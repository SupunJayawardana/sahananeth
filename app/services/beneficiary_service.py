"""
beneficiary_service.py
-----------------------
Backs the citizen verification / beneficiary directory screens (Gov
Officer and Super Admin). This is the first place in the codebase either
role can browse or search Beneficiary records directly — previously the
only way one became visible to staff was as a side effect of approving a
specific ShelterRegistrationRequest.
"""
from app.extensions import db
from app.models.beneficiary import Beneficiary


def search_and_filter(q='', verified='', shelter_id=None, limit=200):
    """
    verified: '' (all), 'yes' (is_verified=True), 'no' (is_verified=False)
    """
    query = Beneficiary.query
    if q:
        like = f'%{q.strip()}%'
        query = query.filter(db.or_(
            Beneficiary.full_name.ilike(like),
            Beneficiary.identification_number.ilike(like),
        ))
    if verified == 'yes':
        query = query.filter(Beneficiary.is_verified.is_(True))
    elif verified == 'no':
        query = query.filter(Beneficiary.is_verified.is_(False))
    if shelter_id:
        query = query.filter(Beneficiary.allocated_shelter_id == shelter_id)

    return query.order_by(Beneficiary.full_name).limit(limit).all()
