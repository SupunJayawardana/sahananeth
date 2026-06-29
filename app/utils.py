from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role_level not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def active_required(f):
    """Blocks pending/rejected users from accessing any function."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.status == 'pending':
            flash('Your account is pending approval. Please wait.', 'warning')
            return redirect(url_for('auth.pending'))
        if current_user.status == 'rejected':
            flash('Your account has been rejected. Contact admin.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function