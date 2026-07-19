"""
scripts/set_webhook.py
------------------------
Run this ONCE after deploying to Render (or any host with a public HTTPS
URL) to tell Telegram where to send updates. Don't run this for local
development — use run_bot_polling.py instead, and note that setting a
webhook automatically disables polling for the same bot token.

Usage:
    python scripts/set_webhook.py https://your-app.onrender.com
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import telegram_api

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_webhook.py https://your-app.onrender.com")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    secret = os.environ.get('TELEGRAM_WEBHOOK_SECRET', 'dev-webhook-secret-change-later')
    webhook_url = f"{base_url}/telegram/webhook/{secret}"

    ok, error = telegram_api.set_webhook(webhook_url, secret_token=secret)
    if ok:
        print(f"Webhook set: {webhook_url}")
    else:
        print(f"Failed to set webhook: {error}")
        sys.exit(1)
