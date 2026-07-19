from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.services import telegram_api
from app.services.notification_service import notify_role
from app.services.telegram_api import build_inline_keyboard

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Staff login — for Gov Officer, Field Officer, Super Admin."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))

        # Block citizens from staff login
        if user.role_level == 'citizen':
            flash('Please use the Citizen login portal.', 'warning')
            return redirect(url_for('auth.login'))

        session.permanent = remember
        login_user(user, remember=remember)
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Staff registration — Gov Officer and Field Officer only."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        role = request.form.get('role')

        # Only allow staff roles here
        if role not in ('gov_officer', 'field_officer', 'warehouse_manager'):
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            full_name=full_name,
            role_level=role,
            status='pending'        # Always pending until approved
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        approval_kb = build_inline_keyboard([[
            ('✅ Approve', f'apr_user:{new_user.id}'),
            ('❌ Reject', f'rej_user:{new_user.id}'),
        ]])
        notify_role('gov_officer', f'New {role.replace("_", " ").title()} registration awaiting approval: {new_user.username}.',
                    title='New staff registration', urgency='info', reply_markup=approval_kb)
        notify_role('super_admin', f'New {role.replace("_", " ").title()} registration awaiting approval: {new_user.username}.',
                    title='New staff registration', urgency='info', reply_markup=approval_kb)

        flash('Registration submitted. Please wait for approval before logging in.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/pending')
@login_required
def pending():
    """Shown to staff who are logged in but not yet approved."""
    return render_template('auth/pending.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role_level == 'super_admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role_level == 'gov_officer':
        if current_user.status == 'pending':
            return redirect(url_for('auth.pending'))
        return redirect(url_for('gov.dashboard'))
    elif current_user.role_level == 'field_officer':
        if current_user.status == 'pending':
            return redirect(url_for('auth.pending'))
        return redirect(url_for('field.dashboard'))
    elif current_user.role_level == 'warehouse_manager':
        if current_user.status == 'pending':
            return redirect(url_for('auth.pending'))
        return redirect(url_for('warehouse.dashboard'))
    else:
        return redirect(url_for('citizen.dashboard'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Password reset works via the linked Telegram account: a 6-digit code is
    sent to the user's chat, they enter it (plus a new password) on the next
    screen. If they haven't linked Telegram yet, there's no email/SMS on
    this system to fall back to — they're told to contact an administrator,
    who can trigger an admin-assisted reset from Manage Users instead.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username).first()

        # Same message whether or not the username exists, so this can't be
        # used to enumerate valid usernames.
        generic_msg = ("If that account exists and has Telegram connected, "
                       "a reset code has been sent.")

        if user and user.telegram_chat_id:
            reset_token = PasswordResetToken.generate(user.id)
            db.session.add(reset_token)
            db.session.commit()
            telegram_api.send_message(
                user.telegram_chat_id,
                f"🔑 Your SAHANANETH password reset code is: <b>{reset_token.code}</b>\n"
                f"It expires in 15 minutes. If you didn't request this, ignore this message."
            )
            flash(generic_msg, 'info')
            return redirect(url_for('auth.reset_password', username=username))

        flash(generic_msg, 'info')
        return redirect(url_for('auth.forgot_password'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    username = request.values.get('username', '')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        code = request.form.get('code', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Invalid reset request.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        token = (PasswordResetToken.query
                 .filter_by(user_id=user.id, code=code, used_at=None)
                 .order_by(PasswordResetToken.created_at.desc())
                 .first())

        if not token or not token.is_valid:
            flash('That code is invalid or has expired. Request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        if not new_password or new_password != confirm_password:
            flash("Passwords don't match.", 'danger')
            return redirect(url_for('auth.reset_password', username=username))

        user.set_password(new_password)
        token.used_at = db.func.now()
        db.session.commit()

        flash('Password reset. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', username=username)


@auth_bp.route('/telegram/connect')
@login_required
def telegram_connect():
    """Generates a one-time link token and shows the user a t.me deep link / QR."""
    from app.models.telegram_link_token import TelegramLinkToken
    from flask import current_app

    link_token = TelegramLinkToken.generate(current_user.id)
    db.session.add(link_token)
    db.session.commit()

    bot_username = current_app.config.get('TELEGRAM_BOT_USERNAME')
    deep_link = f"https://t.me/{bot_username}?start={link_token.token}" if bot_username else None

    return render_template('auth/telegram_connect.html', deep_link=deep_link,
                           bot_configured=bool(bot_username))


@auth_bp.route('/telegram/disconnect')
@login_required
def telegram_disconnect():
    current_user.telegram_chat_id = None
    current_user.telegram_linked_at = None
    db.session.commit()
    flash('Telegram account disconnected.', 'info')
    return redirect(request.referrer or url_for('auth.dashboard'))