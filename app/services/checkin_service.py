"""
checkin_service.py
-------------------
"Are you safe?" campaigns. Builds on notify_segment (same targeting shape
as announcements) but, unlike a plain announcement, creates a
CheckInResponse row per recipient up front so "who hasn't answered yet"
is always a direct query — not something inferred from Telegram delivery
logs.

Also used for staff roll-call (target roles=field_officer/warehouse_manager
instead of citizen) — same mechanism, same response tracking.
"""
from datetime import datetime
from app.extensions import db
from app.models.checkin import CheckIn, CheckInResponse
from app.services.notification_service import build_segment_query, notify_segment
from app.services import telegram_api


def launch_checkin(title, message, roles=None, country=None, region=None,
                    city=None, shelter_id=None, sent_by_id=None):
    """Send a check-in broadcast and create pending response rows for every recipient."""
    users = build_segment_query(
        roles=roles, country=country, region=region, city=city, shelter_id=shelter_id
    ).all()

    checkin = CheckIn(
        title=title,
        message=message,
        sent_by_id=sent_by_id,
    )
    db.session.add(checkin)
    db.session.flush()

    for user in users:
        db.session.add(CheckInResponse(checkin_id=checkin.id, user_id=user.id))
    db.session.flush()

    keyboard = telegram_api.build_inline_keyboard([[
        ('✅ I\'m safe', f'chk_safe:{checkin.id}'),
        ('🆘 Need help', f'chk_help:{checkin.id}'),
    ]])

    notification = notify_segment(
        message, title=title, urgency='critical', sent_by_id=sent_by_id,
        reply_markup=keyboard, users=users,
    )
    checkin.notification_id = notification.id
    db.session.commit()
    return checkin


def mark_safe(checkin_id, actor):
    return record_response(checkin_id, actor, 'safe')


def mark_need_help(checkin_id, actor):
    return record_response(checkin_id, actor, 'need_help')


def record_response(checkin_id, user, status, latitude=None, longitude=None):
    """
    status is 'safe' or 'need_help'. Returns (ok, result_text). If the
    citizen isn't in the original recipient list (e.g. tapped an old
    button after being removed), creates a response row anyway rather
    than silently dropping their answer — better to over-count than to
    lose someone who says they need help.
    """
    checkin = CheckIn.query.get(checkin_id)
    if not checkin:
        return False, 'This check-in is no longer active.'

    response = CheckInResponse.query.filter_by(checkin_id=checkin_id, user_id=user.id).first()
    if not response:
        response = CheckInResponse(checkin_id=checkin_id, user_id=user.id)
        db.session.add(response)

    already_need_help = response.status == 'need_help'
    response.status = status
    response.responded_at = datetime.utcnow()
    if latitude is not None and longitude is not None:
        response.latitude = latitude
        response.longitude = longitude
    db.session.flush()

    if status == 'need_help' and not already_need_help:
        # Plug straight into the existing aid-request triage pipeline
        # instead of being a fourth, parallel request type. Only on the
        # transition INTO need_help — otherwise a repeat/stale tap would
        # create a duplicate aid request every time.
        from app.models.citizen_aid_request import CitizenAidRequest
        from app.services.notification_service import notify_role
        aid = CitizenAidRequest(
            citizen_user_id=user.id,
            description=f'Marked "need help" in response to check-in: "{checkin.title}".',
            country=user.country, region=user.region, city=user.city,
        )
        db.session.add(aid)
        db.session.commit()
        triage_kb = telegram_api.build_inline_keyboard([[
            ('🔄 In progress', f'aid_prog:{aid.id}'),
            ('✅ Resolved', f'aid_done:{aid.id}'),
        ]])
        notify_role('field_officer', f'{user.full_name or user.username} marked "need help" on '
                                      f'check-in "{checkin.title}".',
                    title='Check-in: needs help', urgency='critical', reply_markup=triage_kb)
        notify_role('gov_officer', f'{user.full_name or user.username} marked "need help" on '
                                    f'check-in "{checkin.title}".',
                    title='Check-in: needs help', urgency='critical', reply_markup=triage_kb)
        return True, "🆘 Got it — you've been marked as needing help, and a responder has been notified."

    db.session.commit()
    if status == 'need_help':
        return True, "You're already marked as needing help — a responder has been notified."
    return True, "✅ Marked as safe. Thank you for checking in."
