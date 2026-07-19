"""
handlers.py
------------
All Telegram bot conversation logic lives here as one function:
process_update(update). Both the webhook route (app/routes/bot.py) and the
local polling script (run_bot_polling.py) call this same function, so the
behaviour is identical no matter which mode the bot is running in.

Must always be called from inside a Flask app context (the webhook route
gets one automatically; the polling script pushes one explicitly).
"""
import random
import string
from datetime import datetime

from app.extensions import db
from app.models.user import User
from app.models.beneficiary import Beneficiary
from app.models.telegram_link_token import TelegramLinkToken
from app.models.telegram_conversation_state import TelegramConversationState
from app.models.citizen_aid_request import CitizenAidRequest
from app.models.shelter import Shelter
from app.models.procurement import ProcurementRequest
from app.models.shelter_registration import ShelterRegistrationRequest
from app.services import telegram_api
from app.services.activity_service import log_activity
from app.services import approval_service


def _reply(chat_id, text):
    telegram_api.send_message(chat_id, text)


def _get_state(chat_id):
    return TelegramConversationState.query.filter_by(chat_id=str(chat_id)).first()


def _clear_state(chat_id):
    state = _get_state(chat_id)
    if state:
        db.session.delete(state)
        db.session.commit()


def _set_state(chat_id, flow_name, step, data=None):
    state = _get_state(chat_id)
    if not state:
        state = TelegramConversationState(chat_id=str(chat_id), flow_name=flow_name, step=step)
        db.session.add(state)
    state.flow_name = flow_name
    state.step = step
    if data is not None:
        state.set_data(data)
    db.session.commit()
    return state


def _linked_user(chat_id):
    return User.query.filter_by(telegram_chat_id=str(chat_id)).first()


def _generate_username():
    suffix = ''.join(random.choices(string.digits, k=6))
    return f'tg_citizen_{suffix}'


def _generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


# ---------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------

def handle_start(chat_id, args):
    existing = _linked_user(chat_id)
    if args:
        token = TelegramLinkToken.query.filter_by(token=args).first()
        if not token or not token.is_valid:
            _reply(chat_id, "⚠️ That link is invalid or has expired. Go back to the website and "
                             "click \"Connect Telegram\" again to get a fresh link.")
            return

        user = token.user
        # If this chat is already linked to a different account, unlink it first.
        if user.telegram_chat_id and user.telegram_chat_id != str(chat_id):
            pass  # overwrite — the new link token takes precedence

        user.telegram_chat_id = str(chat_id)
        user.telegram_linked_at = datetime.utcnow()
        token.used_at = datetime.utcnow()
        db.session.commit()

        _reply(chat_id, f"✅ Connected! Hi {user.full_name or user.username}, you'll now get "
                        f"SAHANANETH alerts here.\n\nSend /help to see what I can do.")
        return

    if existing:
        _reply(chat_id, f"👋 Welcome back, {existing.full_name or existing.username}.\n"
                        f"Send /help to see available commands.")
    else:
        _reply(chat_id,
               "👋 Welcome to SAHANANETH — Disaster Relief Management System.\n\n"
               "If you already have a staff account, connect it from your dashboard's "
               "\"Connect Telegram\" button on the website.\n\n"
               "If you're a citizen and need help, send /register to create an account "
               "in under a minute, right here in the chat.")


def handle_help(chat_id):
    user = _linked_user(chat_id)
    lines = ["<b>Available commands</b>"]
    if not user:
        lines.append("/register — create a citizen account and get connected")
    else:
        lines.append("/status — check the status of your requests")
        if user.role_level == 'citizen':
            lines.append("/requestaid — quickly request help/supplies")
    lines.append("/stop — pause notifications")
    lines.append("/resume — resume notifications")
    lines.append("/help — show this message")
    _reply(chat_id, "\n".join(lines))


def handle_stop(chat_id):
    user = _linked_user(chat_id)
    if not user:
        _reply(chat_id, "You're not connected to an account yet.")
        return
    user.notify_opt_in = False
    db.session.commit()
    _reply(chat_id, "🔕 Notifications paused. Send /resume any time to turn them back on.")


def handle_resume(chat_id):
    user = _linked_user(chat_id)
    if not user:
        _reply(chat_id, "You're not connected to an account yet.")
        return
    user.notify_opt_in = True
    db.session.commit()
    _reply(chat_id, "🔔 Notifications resumed.")


def handle_status(chat_id):
    user = _linked_user(chat_id)
    if not user:
        _reply(chat_id, "You're not connected to an account yet. Send /register to get started.")
        return

    if user.role_level == 'citizen':
        lines = ["<b>Your status</b>"]
        aid = (CitizenAidRequest.query.filter_by(citizen_user_id=user.id)
               .order_by(CitizenAidRequest.created_at.desc()).first())
        if aid:
            lines.append(f"Latest aid request: <b>{aid.status}</b> — {aid.description[:80]}")
        reg = (ShelterRegistrationRequest.query.filter_by(citizen_user_id=user.id)
               .order_by(ShelterRegistrationRequest.created_at.desc()).first())
        if reg:
            lines.append(f"Shelter registration ({reg.shelter.shelter_name if reg.shelter else '—'}): <b>{reg.status}</b>")
        if not aid and not reg:
            lines.append("No requests on file yet. Send /requestaid if you need help.")
        _reply(chat_id, "\n".join(lines))
        return

    if user.role_level == 'field_officer':
        open_count = ProcurementRequest.query.filter(
            ProcurementRequest.requested_by_id == user.id,
            ProcurementRequest.status_state.in_(['pending', 'approved', 'dispatched'])
        ).count()
        _reply(chat_id, f"You have <b>{open_count}</b> open procurement request(s) in progress.")
        return

    if user.status == 'pending':
        _reply(chat_id, "Your account is still pending approval.")
    else:
        _reply(chat_id, f"You're logged in as <b>{user.role_level.replace('_', ' ').title()}</b> "
                        f"and your account is <b>{user.status}</b>.")


# ---------------------------------------------------------------------
# /register flow (citizen self-registration)
# ---------------------------------------------------------------------

REGISTER_STEPS = ['full_name', 'id_number', 'phone', 'country', 'region', 'city', 'confirm']
REGISTER_PROMPTS = {
    'full_name': "Let's get you registered. What's your full name?",
    'id_number': "What's your national ID / passport number?",
    'phone': "What's a phone number we can reach you on?",
    'country': "Which country are you in?",
    'region': "Which state / province / region?",
    'city': "Which city or town?",
    'confirm': None,  # built dynamically
}


def _confirm_text(data):
    return (
        "Please confirm your details:\n\n"
        f"Name: {data.get('full_name')}\n"
        f"ID: {data.get('id_number')}\n"
        f"Phone: {data.get('phone')}\n"
        f"Location: {data.get('city')}, {data.get('region')}, {data.get('country')}\n\n"
        "Reply <b>yes</b> to confirm, or <b>no</b> to start over."
    )


def start_register(chat_id):
    if _linked_user(chat_id):
        _reply(chat_id, "You're already connected to an account. Send /status to check it.")
        return
    _set_state(chat_id, 'register', 'full_name', {})
    _reply(chat_id, REGISTER_PROMPTS['full_name'])


def continue_register(chat_id, state, text):
    data = state.get_data()
    step = state.step

    if step == 'link_confirm':
        if text.strip().lower() in ('link', 'l', 'yes', 'y'):
            beneficiary = Beneficiary.query.get(data['match_beneficiary_id'])
            if not beneficiary:
                _clear_state(chat_id)
                _reply(chat_id, "That record isn't available anymore. Send /register to start fresh.")
                return

            if beneficiary.user:
                # Existing account with no Telegram attached yet — just attach this chat to it.
                existing_user = beneficiary.user
                existing_user.telegram_chat_id = str(chat_id)
                existing_user.telegram_linked_at = datetime.utcnow()
                db.session.commit()
                log_activity('user', f'{existing_user.username} linked Telegram via /register (matched existing ID).', user_id=existing_user.id)
                _clear_state(chat_id)
                _reply(chat_id, f"✅ Connected! Welcome back, {beneficiary.full_name}. "
                                f"Send /status to check your requests, or /requestaid for help.")
            else:
                # Beneficiary exists (e.g. registered in person by a Field Officer) but has
                # no login yet — create one now and attach it to the SAME beneficiary record
                # instead of creating a second, duplicate one.
                username = _generate_username()
                password = _generate_password()
                user = User(
                    username=username,
                    full_name=beneficiary.full_name,
                    role_level='citizen',
                    status='active',
                    telegram_chat_id=str(chat_id),
                    telegram_linked_at=datetime.utcnow(),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                beneficiary.user_id = user.id
                log_activity('user', f'Citizen {user.username} linked to existing beneficiary record via Telegram.', user_id=user.id)
                db.session.commit()
                _clear_state(chat_id)
                _reply(chat_id, f"✅ Connected to your existing record, {beneficiary.full_name}. "
                                f"Your account username is <b>{username}</b> (password: <b>{password}</b>) "
                                f"if you ever want to log into the website.\n\nSend /requestaid any time you need help.")
        else:
            _clear_state(chat_id)
            _reply(chat_id, "No problem. If that ID is genuinely yours and this seems wrong, "
                            "please contact a Field Officer to sort it out. Send /register any time to try again.")
        return

    if step == 'confirm':
        if text.strip().lower() in ('yes', 'y'):
            username = _generate_username()
            password = _generate_password()
            user = User(
                username=username,
                full_name=data['full_name'],
                role_level='citizen',
                status='active',
                country=data['country'],
                region=data['region'],
                city=data['city'],
                telegram_chat_id=str(chat_id),
                telegram_linked_at=datetime.utcnow(),
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            db.session.add(Beneficiary(
                identification_number=data['id_number'],
                full_name=data['full_name'],
                is_verified=False,
                user_id=user.id,
            ))
            log_activity('user', f'Citizen {user.username} self-registered via Telegram bot.', user_id=user.id)
            db.session.commit()

            _clear_state(chat_id)
            _reply(chat_id,
                   f"✅ You're registered! Your account username is <b>{username}</b> "
                   f"(password: <b>{password}</b>) if you ever want to log into the website — "
                   f"but you can do everything right here too.\n\n"
                   f"Send /requestaid any time you need help.")
        else:
            _clear_state(chat_id)
            _reply(chat_id, "No problem — send /register whenever you're ready to try again.")
        return

    # Store the answer for the current step, then move to the next one
    field = step
    data[field] = text.strip()

    if field == 'id_number':
        existing = Beneficiary.query.filter_by(identification_number=data['id_number']).first()
        if existing:
            if existing.user and existing.user.telegram_chat_id:
                _clear_state(chat_id)
                _reply(chat_id, "That ID is already linked to a different Telegram account. "
                                "If this is you and you've lost access, please contact a Field Officer for help.")
                return
            data['match_beneficiary_id'] = existing.id
            _set_state(chat_id, 'register', 'link_confirm', data)
            _reply(chat_id, f"We found an existing record under this ID for <b>{existing.full_name}</b>.\n\n"
                            f"Reply <b>link</b> to connect this Telegram account to it, "
                            f"or <b>cancel</b> if that's not you.")
            return

    next_index = REGISTER_STEPS.index(step) + 1
    next_step = REGISTER_STEPS[next_index]
    _set_state(chat_id, 'register', next_step, data)

    if next_step == 'confirm':
        _reply(chat_id, _confirm_text(data))
    else:
        _reply(chat_id, REGISTER_PROMPTS[next_step])


# ---------------------------------------------------------------------
# /requestaid flow
# ---------------------------------------------------------------------

def start_request_aid(chat_id):
    user = _linked_user(chat_id)
    if not user:
        _reply(chat_id, "You'll need an account first — send /register to set one up (takes under a minute).")
        return
    _set_state(chat_id, 'request_aid', 'description', {})
    _reply(chat_id, "What do you need help with? (e.g. \"need drinking water and blankets for 4 people\")")


def continue_request_aid(chat_id, state, text):
    data = state.get_data()
    step = state.step
    user = _linked_user(chat_id)

    if step == 'description':
        data['description'] = text.strip()
        if user.country and user.region and user.city:
            # Reuse profile location, skip straight to confirm
            data['country'], data['region'], data['city'] = user.country, user.region, user.city
            _set_state(chat_id, 'request_aid', 'confirm', data)
            _reply(chat_id, f"Submit this request?\n\n\"{data['description']}\"\n"
                            f"Location: {data['city']}, {data['region']}, {data['country']}\n\n"
                            f"Reply <b>yes</b> to submit, or <b>no</b> to cancel.")
        else:
            _set_state(chat_id, 'request_aid', 'city', data)
            _reply(chat_id, "Which city/town are you in right now?")
        return

    if step == 'city':
        data['city'] = text.strip()
        _set_state(chat_id, 'request_aid', 'region', data)
        _reply(chat_id, "Which state / province / region?")
        return

    if step == 'region':
        data['region'] = text.strip()
        _set_state(chat_id, 'request_aid', 'country', data)
        _reply(chat_id, "Which country?")
        return

    if step == 'country':
        data['country'] = text.strip()
        _set_state(chat_id, 'request_aid', 'confirm', data)
        _reply(chat_id, f"Submit this request?\n\n\"{data['description']}\"\n"
                        f"Location: {data['city']}, {data['region']}, {data['country']}\n\n"
                        f"Reply <b>yes</b> to submit, or <b>no</b> to cancel.")
        return

    if step == 'confirm':
        if text.strip().lower() in ('yes', 'y'):
            aid = CitizenAidRequest(
                citizen_user_id=user.id,
                description=data['description'],
                country=data.get('country'),
                region=data.get('region'),
                city=data.get('city'),
            )
            db.session.add(aid)
            log_activity('shelter', f'Citizen {user.username} requested aid via Telegram bot.', user_id=user.id)
            db.session.commit()

            from app.services.notification_service import notify_role
            triage_kb = telegram_api.build_inline_keyboard([[
                ('🔄 In progress', f'aid_prog:{aid.id}'),
                ('✅ Resolved', f'aid_done:{aid.id}'),
            ]])
            notify_role('field_officer', f'New aid request from {user.full_name or user.username} '
                                          f'in {aid.city or "unknown location"}: "{aid.description}"',
                        title='New citizen aid request', urgency='warning', reply_markup=triage_kb)
            notify_role('gov_officer', f'New aid request from {user.full_name or user.username} '
                                        f'in {aid.city or "unknown location"}: "{aid.description}"',
                        title='New citizen aid request', urgency='warning', reply_markup=triage_kb)

            _clear_state(chat_id)
            _reply(chat_id, "✅ Your request has been submitted. A responder will be in touch. "
                            "Send /status any time to check on it.")
        else:
            _clear_state(chat_id)
            _reply(chat_id, "Cancelled. Send /requestaid whenever you need to.")
        return


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

COMMAND_HANDLERS = {
    '/start': lambda chat_id, args: handle_start(chat_id, args),
    '/help': lambda chat_id, args: handle_help(chat_id),
    '/status': lambda chat_id, args: handle_status(chat_id),
    '/stop': lambda chat_id, args: handle_stop(chat_id),
    '/resume': lambda chat_id, args: handle_resume(chat_id),
    '/register': lambda chat_id, args: start_register(chat_id),
    '/requestaid': lambda chat_id, args: start_request_aid(chat_id),
}

CONTINUATION_HANDLERS = {
    'register': continue_register,
    'request_aid': continue_request_aid,
}


# ─── Inline button (callback_query) handling — Phase 3 ─────────────────────

# callback_data is formatted "<action>:<id>" — see build_*_keyboard callers
# in the route files for where these are generated.
CALLBACK_ACTIONS = {
    'apr_user': approval_service.approve_staff_user,
    'rej_user': approval_service.reject_staff_user,
    'apr_shelter': approval_service.approve_shelter,
    'rej_shelter': approval_service.reject_shelter,
    'apr_wh': approval_service.approve_warehouse,
    'rej_wh': approval_service.reject_warehouse,
    'apr_proc': approval_service.approve_procurement_auto,
    'rej_proc': approval_service.reject_procurement,
    'apr_reg': approval_service.approve_registration,
    'rej_reg': approval_service.reject_registration,
    'aid_prog': approval_service.mark_aid_in_progress,
    'aid_done': approval_service.mark_aid_resolved,
}


def handle_callback_query(callback_query):
    query_id = callback_query['id']
    from_chat_id = callback_query['from']['id']
    message = callback_query.get('message') or {}
    chat_id = message.get('chat', {}).get('id')
    message_id = message.get('message_id')
    original_text = message.get('text', '')
    data = callback_query.get('data', '')

    actor = _linked_user(from_chat_id)
    if not actor:
        telegram_api.answer_callback_query(query_id, text='Link your account first with /start.', show_alert=True)
        return

    action, _, id_str = data.partition(':')
    handler = CALLBACK_ACTIONS.get(action)
    if not handler or not id_str.isdigit():
        telegram_api.answer_callback_query(query_id, text='Unknown action.', show_alert=True)
        return

    ok, result_text = handler(int(id_str), actor)

    # Always remove the buttons and show the outcome, whether this actor
    # succeeded, was denied, or someone else already handled it first —
    # so a stale button can never be tapped twice.
    if chat_id is not None and message_id is not None:
        telegram_api.edit_message_text(chat_id, message_id, f'{original_text}\n\n— {result_text}', reply_markup=None)

    telegram_api.answer_callback_query(query_id, text=result_text if not ok else 'Done ✅')


def process_update(update):
    """
    Main entry point. Called with one Telegram Update object (as a dict).
    Must run inside a Flask app context.
    """
    callback_query = update.get('callback_query')
    if callback_query:
        handle_callback_query(callback_query)
        return

    message = update.get('message')
    if not message or 'text' not in message:
        return  # ignore non-text updates (photos, stickers, edits, etc.)

    chat_id = message['chat']['id']
    text = message['text'].strip()

    if text.startswith('/'):
        parts = text.split(maxsplit=1)
        command = parts[0].split('@')[0]  # strip "@BotName" if present
        args = parts[1].strip() if len(parts) > 1 else ''

        # A command always interrupts/cancels any in-progress guided flow
        _clear_state(chat_id)

        handler = COMMAND_HANDLERS.get(command)
        if handler:
            handler(chat_id, args)
        else:
            _reply(chat_id, "Unknown command. Send /help to see what I can do.")
        return

    # Not a command — continue an in-progress guided flow, if any
    state = _get_state(chat_id)
    if state and state.flow_name in CONTINUATION_HANDLERS:
        CONTINUATION_HANDLERS[state.flow_name](chat_id, state, text)
    else:
        _reply(chat_id, "I didn't understand that. Send /help to see available commands.")
