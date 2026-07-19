"""
citizen_service.py
-------------------
Single source of truth for "does a Beneficiary already exist for this ID,
and if so, how does this User connect to it" — used by:
  - the Telegram bot's /register flow (app/bot/handlers.py)
  - the website's citizen registration flow (app/routes/citizen.py)
  - Field Officer in-person registration (app/routes/field_officer.py)

Before this existed, the bot had its own ID-matching logic and the web
register/profile routes had none at all, which is how a citizen registered
in person by a Field Officer could end up with a second, disconnected
Beneficiary record if they signed up on the website instead of the bot.
"""
import random
import string

from app.extensions import db
from app.models.user import User
from app.models.beneficiary import Beneficiary


def generate_username():
    suffix = ''.join(random.choices(string.digits, k=6))
    return f'citizen_{suffix}'


def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


def find_beneficiary_by_id(identification_number):
    return Beneficiary.query.filter_by(identification_number=identification_number).first()


class IdentityConflict(Exception):
    """Raised when this ID is already claimed by a *different*, already-connected account."""
    def __init__(self, beneficiary):
        self.beneficiary = beneficiary
        super().__init__(f'ID already linked to account for {beneficiary.full_name}')


def register_or_link_citizen(identification_number, full_name, extra_user_fields=None,
                              allow_link=True):
    """
    Core of every "citizen signs up" flow, regardless of door.

    - No existing Beneficiary for this ID -> create a new User + Beneficiary,
      linked to each other.
    - Existing Beneficiary with no User yet (e.g. registered in person by a
      Field Officer) -> create a User and attach it to that SAME
      Beneficiary, instead of creating a duplicate record.
    - Existing Beneficiary that already has a User -> if allow_link is
      True, return that existing user/beneficiary pair unchanged (caller
      decides what "link" means for their flow — e.g. attach a Telegram
      chat id). If allow_link is False, raises IdentityConflict so the
      caller can ask the citizen to confirm before touching an existing
      account.

    Returns (user, beneficiary, created: bool) — created is True only when
    a brand-new User was created by this call.
    """
    extra_user_fields = extra_user_fields or {}
    existing = find_beneficiary_by_id(identification_number)

    if existing and existing.user_id:
        if not allow_link:
            raise IdentityConflict(existing)
        return existing.user, existing, False

    if existing and not existing.user_id:
        username = generate_username()
        password = generate_password()
        user = User(
            username=username,
            full_name=existing.full_name or full_name,
            role_level='citizen',
            status='active',
            **extra_user_fields,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        existing.user_id = user.id
        user._generated_password = password  # transient, not persisted — for the caller to show once
        return user, existing, True

    # No existing record at all — brand new citizen.
    username = generate_username()
    password = generate_password()
    user = User(
        username=username,
        full_name=full_name,
        role_level='citizen',
        status='active',
        **extra_user_fields,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    beneficiary = Beneficiary(
        identification_number=identification_number,
        full_name=full_name,
        is_verified=False,
        user_id=user.id,
    )
    db.session.add(beneficiary)
    return user, beneficiary, True


def search_beneficiaries(query, limit=10):
    """Simple ID/name search used by the person picker (see app/routes/api.py)."""
    if not query or len(query.strip()) < 2:
        return []
    like = f'%{query.strip()}%'
    return (Beneficiary.query
            .filter(db.or_(Beneficiary.full_name.ilike(like),
                            Beneficiary.identification_number.ilike(like)))
            .order_by(Beneficiary.full_name)
            .limit(limit).all())
