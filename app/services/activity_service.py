from app.extensions import db
from app.models.activity_log import ActivityLog


def log_activity(category, description, user_id=None):
    """Creates a new activity log entry. Call this after any notable
    create/approve/reject/update action so it shows up on the
    Super Admin Analytics feed."""
    entry = ActivityLog(
        category=category,
        description=description,
        user_id=user_id
    )
    db.session.add(entry)
    db.session.commit()


def get_recent_activity(limit=25):
    return ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
