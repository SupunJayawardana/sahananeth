"""
telegram_api.py
----------------
Minimal wrapper around Telegram's Bot HTTP API using `requests`.

Deliberately avoids the python-telegram-bot dependency: Telegram's Bot API
is just plain HTTPS + JSON, so a thin wrapper keeps this project's
dependency list small and makes the whole integration easy to test.

Requires the environment variable TELEGRAM_BOT_TOKEN to be set (get one
from @BotFather on Telegram). If it's not set, every function here is a
safe no-op that logs a warning instead of raising — so the rest of the
app (approvals, dashboards, etc.) never breaks just because the bot isn't
configured yet.
"""
import os
import requests

API_BASE = "https://api.telegram.org/bot{token}"
DEFAULT_TIMEOUT = 8  # seconds — never let a Telegram hiccup hang a web request


def _token():
    return os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()


def is_configured():
    return bool(_token())


def _url(method):
    return f"{API_BASE.format(token=_token())}/{method}"


def send_message(chat_id, text, parse_mode='HTML', reply_markup=None):
    """
    Sends a message to a chat. Returns (success: bool, error: str|None).
    Never raises — callers can always proceed even if this fails.
    """
    if not is_configured():
        return False, "TELEGRAM_BOT_TOKEN is not set"
    if not chat_id:
        return False, "No chat_id"

    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        resp = requests.post(_url('sendMessage'), json=payload, timeout=DEFAULT_TIMEOUT)
        data = resp.json()
        if data.get('ok'):
            return True, None
        return False, data.get('description', 'Unknown Telegram API error')
    except requests.RequestException as e:
        return False, str(e)


def build_inline_keyboard(rows):
    """
    rows: list of lists of (label, callback_data) tuples, e.g.
        [[("✅ Approve", "apr_shelter:12"), ("❌ Reject", "rej_shelter:12")]]
    Returns a Telegram-shaped reply_markup dict. callback_data must be <=64 bytes.
    """
    return {
        'inline_keyboard': [
            [{'text': label, 'callback_data': data} for label, data in row]
            for row in rows
        ]
    }


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """Stops the loading spinner on the button the user tapped, optionally
    showing a small toast (or a blocking alert dialog if show_alert=True)."""
    if not is_configured():
        return False
    payload = {'callback_query_id': callback_query_id}
    if text:
        payload['text'] = text
        payload['show_alert'] = show_alert
    try:
        resp = requests.post(_url('answerCallbackQuery'), json=payload, timeout=DEFAULT_TIMEOUT)
        return resp.json().get('ok', False)
    except requests.RequestException:
        return False


def edit_message_text(chat_id, message_id, text, parse_mode='HTML', reply_markup=None):
    """Replaces a message's text (and optionally its buttons) in place —
    used after an inline button is actioned, so the outcome is shown and
    the buttons can't be clicked twice."""
    if not is_configured():
        return False, "TELEGRAM_BOT_TOKEN is not set"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    try:
        resp = requests.post(_url('editMessageText'), json=payload, timeout=DEFAULT_TIMEOUT)
        data = resp.json()
        if data.get('ok'):
            return True, None
        return False, data.get('description', 'Unknown Telegram API error')
    except requests.RequestException as e:
        return False, str(e)


def send_location_request(chat_id, text):
    """
    Sends a message with Telegram's native "Share Location" prompt — a real
    reply keyboard (not an inline one), so the citizen's own client shows
    the standard location-sharing UI and their device's actual current
    GPS position comes back as a message.location update. This is what
    makes "ask the citizen where they are" possible at all — a staff
    member's own device location is never a stand-in for the citizen's.
    """
    reply_markup = {
        'keyboard': [[{'text': '📍 Share my current location', 'request_location': True}]],
        'resize_keyboard': True,
        'one_time_keyboard': True,
    }
    return send_message(chat_id, text, reply_markup=reply_markup)


def get_updates(offset=None, timeout=25):
    """Long-polling fetch of new updates. Used only by the local polling script."""
    if not is_configured():
        return []
    params = {'timeout': timeout}
    if offset is not None:
        params['offset'] = offset
    try:
        resp = requests.get(_url('getUpdates'), params=params, timeout=timeout + 10)
        data = resp.json()
        return data.get('result', []) if data.get('ok') else []
    except requests.RequestException:
        return []


def set_webhook(url, secret_token=None):
    if not is_configured():
        return False, "TELEGRAM_BOT_TOKEN is not set"
    payload = {'url': url}
    if secret_token:
        payload['secret_token'] = secret_token
    try:
        resp = requests.post(_url('setWebhook'), json=payload, timeout=DEFAULT_TIMEOUT)
        data = resp.json()
        return data.get('ok', False), data.get('description')
    except requests.RequestException as e:
        return False, str(e)


def delete_webhook():
    if not is_configured():
        return False
    try:
        resp = requests.post(_url('deleteWebhook'), timeout=DEFAULT_TIMEOUT)
        return resp.json().get('ok', False)
    except requests.RequestException:
        return False
