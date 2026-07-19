"""
run_bot_polling.py
--------------------
Run the Telegram bot in long-polling mode — no public HTTPS URL required.
Use this for local development. On Render (or anywhere with a public URL),
use the webhook instead (see app/routes/bot.py + scripts/set_webhook.py).

Usage:
    python run_bot_polling.py

Requires TELEGRAM_BOT_TOKEN to be set (in your .env or environment).
This script and the main Flask app (run.py) can run at the same time —
they share the same database, so notifications triggered by web actions
still get delivered even though this is a separate process.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services import telegram_api
from app.bot.handlers import process_update

app = create_app(os.environ.get('FLASK_ENV', 'development'))


def main():
    if not telegram_api.is_configured():
        print("TELEGRAM_BOT_TOKEN is not set — nothing to poll. "
              "Set it in your .env file and try again.")
        return

    # Polling and webhook modes can't both be active — make sure no
    # webhook is registered before we start pulling updates ourselves.
    telegram_api.delete_webhook()

    print("SAHANANETH Telegram bot — polling mode. Press Ctrl+C to stop.")
    offset = None

    with app.app_context():
        while True:
            try:
                updates = telegram_api.get_updates(offset=offset, timeout=25)
                for update in updates:
                    offset = update['update_id'] + 1
                    try:
                        process_update(update)
                    except Exception as e:
                        print(f"Error handling update {update.get('update_id')}: {e}")
            except KeyboardInterrupt:
                print("\nStopping.")
                break
            except Exception as e:
                print(f"Polling error: {e} — retrying in 3s")
                time.sleep(3)


if __name__ == '__main__':
    main()
