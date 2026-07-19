"""
notification_service.py
------------------------
Central place that turns "something happened" into a Telegram message.

Two ways this gets used:
  1. Track 1 (automatic): route handlers call notify_user(...) right next
     to their existing log_activity(...) call — e.g. after a shelter is
     approved, after stock runs low, etc.
  2. Track 2 (broadcast): the Announcement screen calls notify_segment(...)
     with a set of filter criteria (roles, country/region/city, shelter).

Every send is recorded as a Notification + one NotificationDelivery per
recipient, so there's always an audit trail and a "N of M delivered" count
— and a failed Telegram send never raises or blocks the calling request.
"""
import json
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification, NotificationDelivery
from app.services import telegram_api

URGENCY_PREFIX = {
    'info': 'ℹ️',
    'warning': '⚠️',
    'critical': '🚨',
}


def _format_message(title, message, urgency='info'):
    prefix = URGENCY_PREFIX.get(urgency, '')
    if title:
        return f"{prefix} <b>{title}</b>\n\n{message}".strip()
    return f"{prefix} {message}".strip()


def _deliver(notification, user, reply_markup=None):
    """Sends to one user and records the outcome. Never raises."""
    if not user.notify_opt_in:
        status, error = 'skipped_not_linked', 'User opted out'
    elif not user.telegram_chat_id:
        status, error = 'skipped_not_linked', 'Telegram not linked'
    else:
        ok, err = telegram_api.send_message(user.telegram_chat_id, notification.message, reply_markup=reply_markup)
        status, error = ('sent', None) if ok else ('failed', err)

    db.session.add(NotificationDelivery(
        notification_id=notification.id,
        user_id=user.id,
        status=status,
        error_message=error,
    ))


def notify_user(user, message, title=None, urgency='info', category='auto_alert', reply_markup=None):
    """Send a single transactional alert to one user (Track 1)."""
    if user is None:
        return None
    notification = Notification(
        category=category,
        urgency=urgency,
        title=title,
        message=_format_message(title, message, urgency),
    )
    db.session.add(notification)
    db.session.flush()  # get notification.id before creating deliveries

    _deliver(notification, user, reply_markup=reply_markup)
    db.session.commit()
    return notification


def notify_users(users, message, title=None, urgency='info', category='auto_alert', reply_markup=None):
    """Send the same transactional alert to several specific users at once."""
    if not users:
        return None
    notification = Notification(
        category=category,
        urgency=urgency,
        title=title,
        message=_format_message(title, message, urgency),
    )
    db.session.add(notification)
    db.session.flush()

    for user in users:
        _deliver(notification, user, reply_markup=reply_markup)
    db.session.commit()
    return notification


def notify_role(role, message, title=None, urgency='info', reply_markup=None):
    """Send to every active user with a given role_level (e.g. all Gov Officers)."""
    users = User.query.filter_by(role_level=role, status='active').all()
    return notify_users(users, message, title=title, urgency=urgency, reply_markup=reply_markup)


def build_segment_query(roles=None, country=None, region=None, city=None,
                         shelter_id=None, status='active'):
    """
    Builds (but doesn't execute) the User query for a set of broadcast
    criteria. Shared by the recipient-count preview and the actual send,
    so the count shown to the sender always matches who actually gets it.
    """
    query = User.query
    if status:
        query = query.filter(User.status == status)
    if roles:
        query = query.filter(User.role_level.in_(roles))
    if country:
        query = query.filter(User.country == country)
    if region:
        query = query.filter(User.region == region)
    if city:
        query = query.filter(User.city == city)

    if shelter_id:
        from app.models.beneficiary import Beneficiary
        beneficiary_user_ids = [
            b.user_id for b in Beneficiary.query.filter_by(allocated_shelter_id=shelter_id).all()
            if b.user_id is not None
        ]
        query = query.filter(User.id.in_(beneficiary_user_ids))

    return query


def notify_segment(message, title=None, urgency='info', roles=None, country=None,
                    region=None, city=None, shelter_id=None, sent_by_id=None,
                    reply_markup=None, users=None):
    """
    Send a manual, criteria-targeted announcement (Track 2 — disaster
    alerts / general announcements). Returns the Notification record,
    which carries delivered/failed/skipped counts.

    reply_markup lets a broadcast carry inline buttons (e.g. check-in
    campaigns' "I'm safe" / "Need help") — previously not supported here.
    Pass an explicit `users` list to skip re-deriving the audience from
    criteria (used by checkin_service, which needs the exact same user
    list for both the Notification deliveries and the CheckInResponse rows).
    """
    if users is None:
        users = build_segment_query(
            roles=roles, country=country, region=region, city=city, shelter_id=shelter_id
        ).all()

    criteria = {
        'roles': roles, 'country': country, 'region': region,
        'city': city, 'shelter_id': shelter_id,
    }

    notification = Notification(
        category='announcement',
        urgency=urgency,
        title=title,
        message=_format_message(title, message, urgency),
        criteria_json=json.dumps(criteria),
        sent_by_id=sent_by_id,
    )
    db.session.add(notification)
    db.session.flush()

    for user in users:
        _deliver(notification, user, reply_markup=reply_markup)
    db.session.commit()
    return notification
