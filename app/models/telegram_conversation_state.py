from app.extensions import db
from datetime import datetime
import json

class TelegramConversationState(db.Model):
    """
    One row per active Telegram chat that's mid-way through a guided flow
    (e.g. /register or /requestaid). Storing this in the database rather
    than in memory means it survives app restarts and works identically
    whether the bot is running in polling mode or webhook mode.
    """
    __tablename__ = 'telegram_conversation_states'

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(64), unique=True, nullable=False)
    flow_name = db.Column(db.String(50), nullable=False)   # e.g. 'register', 'request_aid'
    step = db.Column(db.String(50), nullable=False)
    data_json = db.Column(db.Text, nullable=True)           # collected answers so far
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_data(self):
        return json.loads(self.data_json) if self.data_json else {}

    def set_data(self, d):
        self.data_json = json.dumps(d)

    def __repr__(self):
        return f'<TelegramConversationState {self.chat_id} {self.flow_name}:{self.step}>'
