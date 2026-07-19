from flask import Blueprint, request, current_app, abort
from app.bot.handlers import process_update

bot_bp = Blueprint('bot', __name__)


@bot_bp.route('/webhook/<secret>', methods=['POST'])
def webhook(secret):
    """
    Telegram POSTs each update here. The <secret> in the URL (plus the
    X-Telegram-Bot-Api-Secret-Token header Telegram also sends, checked
    below) keeps randoms on the internet from feeding fake updates into
    the bot.
    """
    expected = current_app.config.get('TELEGRAM_WEBHOOK_SECRET')
    if not expected or secret != expected:
        abort(404)

    header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if header_secret and header_secret != expected:
        abort(403)

    update = request.get_json(silent=True) or {}
    try:
        process_update(update)
    except Exception:
        # Never let a malformed update or a bug in one handler crash the
        # webhook endpoint — Telegram will just retry otherwise, and a
        # 500 here has no effect on the rest of the app either way.
        current_app.logger.exception("Error processing Telegram update")

    return {'ok': True}
