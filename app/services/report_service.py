"""
report_service.py
------------------
Backs the self-service Report Builder (Super Admin / Gov Officer).

Rather than hard-coding a fixed set of reports, this defines a small
*registry* of reportable data sources (SOURCES below) — each one names
its model, its filterable fields, and how to render a row. A saved report
is just: which source, which filters, optional location-radius filter,
optional group-by. The builder UI is driven entirely off this registry,
so adding a new report type later means adding one entry here — no new
route, no new template.

Deliberately does everything in Python rather than building dynamic SQL:
this system's tables are small (a relief-coordination system, not a data
warehouse), and a fixed set of hand-written SQLAlchemy filter expressions
per operator would be a much larger, more bug-prone surface than "fetch
the (cheaply pre-filtered) rows, then filter/group/sort them in Python" —
consistent with how geo_service already ranks warehouses in Python rather
than in the query.
"""
import json
from datetime import datetime, timedelta

from app.services.geo_service import haversine_distance


# ---------------------------------------------------------------------
# Field types -> which comparison operators make sense for them
# ---------------------------------------------------------------------
OPERATORS_BY_TYPE = {
    'string':  [('contains', 'contains'), ('not_contains', "doesn't contain"),
                ('equals', 'is exactly'), ('is_empty', 'is empty'), ('is_not_empty', 'is not empty')],
    'choice':  [('equals', 'is'), ('not_equals', 'is not')],
    'number':  [('equals', '='), ('greater_than', '>'), ('less_than', '<')],
    'boolean': [('is_true', 'yes'), ('is_false', 'no')],
    'date':    [('within_last_days', 'within the last (days)'), ('older_than_days', 'older than (days)'),
                ('before', 'before (YYYY-MM-DD)'), ('after', 'after (YYYY-MM-DD)')],
}


def _build_sources():
    from app.models.user import User
    from app.models.beneficiary import Beneficiary
    from app.models.shelter import Shelter
    from app.models.citizen_aid_request import CitizenAidRequest
    from app.models.shelter_registration import ShelterRegistrationRequest
    from app.models.procurement import ProcurementRequest
    from app.models.checkin import CheckInResponse

    def days_since(dt):
        if not dt:
            return None
        return (datetime.utcnow() - dt).days

    return {
        'citizens': {
            'label': 'Citizens',
            'query': lambda: User.query.filter_by(role_level='citizen'),
            'fields': {
                'full_name':    {'label': 'Name', 'type': 'string', 'get': lambda r: r.full_name or r.username},
                'country':      {'label': 'Country', 'type': 'string', 'get': lambda r: r.country},
                'region':       {'label': 'Region / Province', 'type': 'string', 'get': lambda r: r.region},
                'city':         {'label': 'City', 'type': 'string', 'get': lambda r: r.city},
                'has_location': {'label': 'Has shared location', 'type': 'boolean', 'get': lambda r: r.latitude is not None},
                'created_at':   {'label': 'Registered', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': lambda r: (r.latitude, r.longitude),
            'columns': [
                ('Name', lambda r: r.full_name or r.username),
                ('Country', lambda r: r.country or '—'),
                ('Region', lambda r: r.region or '—'),
                ('City', lambda r: r.city or '—'),
                ('Has location', lambda r: 'Yes' if r.latitude is not None else 'No'),
                ('Registered', lambda r: r.created_at.strftime('%Y-%m-%d') if r.created_at else '—'),
            ],
        },
        'beneficiaries': {
            'label': 'Beneficiaries',
            'query': lambda: Beneficiary.query,
            'fields': {
                'full_name':              {'label': 'Name', 'type': 'string', 'get': lambda r: r.full_name},
                'identification_number':  {'label': 'ID Number', 'type': 'string', 'get': lambda r: r.identification_number},
                'is_verified':            {'label': 'Verified', 'type': 'boolean', 'get': lambda r: bool(r.is_verified)},
                'shelter_name':           {'label': 'Shelter', 'type': 'string', 'get': lambda r: r.shelter.shelter_name if r.shelter else None},
                'created_at':             {'label': 'Registered', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': lambda r: ((r.shelter.latitude, r.shelter.longitude) if r.shelter else (None, None)),
            'columns': [
                ('Name', lambda r: r.full_name),
                ('ID Number', lambda r: r.identification_number),
                ('Verified', lambda r: 'Yes' if r.is_verified else 'No'),
                ('Shelter', lambda r: r.shelter.shelter_name if r.shelter else '—'),
                ('Registered', lambda r: r.created_at.strftime('%Y-%m-%d') if r.created_at else '—'),
            ],
        },
        'shelters': {
            'label': 'Shelters',
            'query': lambda: Shelter.query,
            'fields': {
                'shelter_name':   {'label': 'Name', 'type': 'string', 'get': lambda r: r.shelter_name},
                'status':         {'label': 'Status', 'type': 'choice',
                                    'choices': ['pending_approval', 'active', 'inactive'], 'get': lambda r: r.status},
                'country':        {'label': 'Country', 'type': 'string', 'get': lambda r: r.country},
                'region':         {'label': 'Region / Province', 'type': 'string', 'get': lambda r: r.region},
                'city':           {'label': 'City', 'type': 'string', 'get': lambda r: r.city},
                'occupancy_pct':  {'label': 'Occupancy %', 'type': 'number',
                                    'get': lambda r: round(100 * r.current_occupancy_count / r.maximum_capacity) if r.maximum_capacity else 0},
                'created_at':     {'label': 'Created', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': lambda r: (r.latitude, r.longitude),
            'columns': [
                ('Name', lambda r: r.shelter_name),
                ('Status', lambda r: r.status.replace('_', ' ').title()),
                ('Occupancy', lambda r: f'{r.current_occupancy_count}/{r.maximum_capacity}'),
                ('Location', lambda r: f'{r.city or "—"}, {r.region or "—"}, {r.country or "—"}'),
            ],
        },
        'aid_requests': {
            'label': 'Citizen Aid Requests',
            'query': lambda: CitizenAidRequest.query,
            'fields': {
                'status':      {'label': 'Status', 'type': 'choice',
                                 'choices': ['pending', 'in_progress', 'resolved'], 'get': lambda r: r.status},
                'country':     {'label': 'Country', 'type': 'string', 'get': lambda r: r.country},
                'region':      {'label': 'Region / Province', 'type': 'string', 'get': lambda r: r.region},
                'city':        {'label': 'City', 'type': 'string', 'get': lambda r: r.city},
                'description': {'label': 'Description', 'type': 'string', 'get': lambda r: r.description},
                'days_open':   {'label': 'Days open', 'type': 'number',
                                 'get': lambda r: days_since(r.created_at) if r.status != 'resolved' else None},
                'created_at':  {'label': 'Submitted', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': lambda r: (r.latitude, r.longitude) if r.latitude is not None else (
                (r.citizen.latitude, r.citizen.longitude) if r.citizen else (None, None)),
            'columns': [
                ('Citizen', lambda r: (r.citizen.full_name or r.citizen.username) if r.citizen else '—'),
                ('Description', lambda r: r.description),
                ('Status', lambda r: r.status.replace('_', ' ').title()),
                ('Location', lambda r: f'{r.city or "—"}, {r.region or "—"}, {r.country or "—"}'),
                ('Days open', lambda r: days_since(r.created_at) if r.status != 'resolved' else '—'),
                ('Submitted', lambda r: r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '—'),
            ],
        },
        'shelter_registrations': {
            'label': 'Shelter Registration Requests',
            'query': lambda: ShelterRegistrationRequest.query,
            'fields': {
                'status':     {'label': 'Status', 'type': 'choice',
                                'choices': ['pending', 'approved', 'rejected'], 'get': lambda r: r.status},
                'full_name':  {'label': 'Name', 'type': 'string', 'get': lambda r: r.full_name},
                'created_at': {'label': 'Submitted', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': None,
            'columns': [
                ('Name', lambda r: r.full_name),
                ('Shelter requested', lambda r: r.shelter.shelter_name if r.shelter else '—'),
                ('Status', lambda r: r.status.title()),
                ('Submitted', lambda r: r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '—'),
            ],
        },
        'procurement_requests': {
            'label': 'Procurement Requests',
            'query': lambda: ProcurementRequest.query,
            'fields': {
                'status_state':    {'label': 'Status', 'type': 'choice',
                                     'choices': ['pending', 'approved', 'dispatched', 'fulfilled', 'rejected'],
                                     'get': lambda r: r.status_state},
                'requested_sku':   {'label': 'Item', 'type': 'string', 'get': lambda r: r.requested_sku},
                'quantity_needed': {'label': 'Quantity', 'type': 'number', 'get': lambda r: r.quantity_needed},
                'created_at':      {'label': 'Requested', 'type': 'date', 'get': lambda r: r.created_at},
            },
            'location': lambda r: ((r.shelter.latitude, r.shelter.longitude) if r.shelter else (None, None)),
            'columns': [
                ('Shelter', lambda r: r.shelter.shelter_name if r.shelter else '—'),
                ('Item', lambda r: f'{r.quantity_needed} {r.metric_unit} {r.requested_sku}'),
                ('Status', lambda r: r.status_state.title()),
                ('Requested', lambda r: r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '—'),
            ],
        },
        'checkin_responses': {
            'label': 'Check-In Responses',
            'query': lambda: CheckInResponse.query,
            'fields': {
                'status':       {'label': 'Status', 'type': 'choice',
                                  'choices': ['pending', 'safe', 'need_help'], 'get': lambda r: r.status},
                'responded_at': {'label': 'Responded', 'type': 'date', 'get': lambda r: r.responded_at},
            },
            'location': lambda r: (r.latitude, r.longitude) if r.latitude is not None else (
                (r.user.latitude, r.user.longitude) if r.user else (None, None)),
            'columns': [
                ('Check-in', lambda r: r.checkin.title if r.checkin else '—'),
                ('Person', lambda r: (r.user.full_name or r.user.username) if r.user else '—'),
                ('Status', lambda r: r.status.replace('_', ' ').title()),
                ('Responded', lambda r: r.responded_at.strftime('%Y-%m-%d %H:%M') if r.responded_at else 'Not yet'),
            ],
        },
    }


def get_sources():
    return _build_sources()


def get_source(source_key):
    sources = get_sources()
    if source_key not in sources:
        raise ValueError(f'Unknown report source: {source_key}')
    return sources[source_key]


# ---------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------
def _matches(value, field_type, operator, raw_value):
    if operator == 'is_empty':
        return value in (None, '')
    if operator == 'is_not_empty':
        return value not in (None, '')

    if field_type == 'string':
        v = (value or '').lower()
        target = (raw_value or '').lower()
        if operator == 'contains':
            return target in v
        if operator == 'not_contains':
            return target not in v
        if operator == 'equals':
            return v == target

    elif field_type == 'choice':
        if operator == 'equals':
            return value == raw_value
        if operator == 'not_equals':
            return value != raw_value

    elif field_type == 'number':
        if value is None:
            return False
        try:
            target = float(raw_value)
        except (TypeError, ValueError):
            return False
        if operator == 'equals':
            return float(value) == target
        if operator == 'greater_than':
            return float(value) > target
        if operator == 'less_than':
            return float(value) < target

    elif field_type == 'boolean':
        if operator == 'is_true':
            return bool(value) is True
        if operator == 'is_false':
            return bool(value) is False

    elif field_type == 'date':
        if value is None:
            return False
        if operator == 'within_last_days':
            try:
                days = int(raw_value)
            except (TypeError, ValueError):
                return False
            return value >= datetime.utcnow() - timedelta(days=days)
        if operator == 'older_than_days':
            try:
                days = int(raw_value)
            except (TypeError, ValueError):
                return False
            return value < datetime.utcnow() - timedelta(days=days)
        if operator == 'before':
            try:
                target = datetime.strptime(raw_value, '%Y-%m-%d')
            except (TypeError, ValueError):
                return False
            return value < target
        if operator == 'after':
            try:
                target = datetime.strptime(raw_value, '%Y-%m-%d')
            except (TypeError, ValueError):
                return False
            return value > target

    return True


def run_report(source_key, filters=None, location_filter=None, group_by=None,
                sort_by=None, sort_dir='asc'):
    """
    filters: list of {field, operator, value}
    location_filter: {lat, lng, radius_km} or None
    Returns: {'rows': [...], 'columns': [(label, get_fn), ...], 'grouped': [(value, count), ...] or None,
              'source_label': str}
    """
    source = get_source(source_key)
    rows = list(source['query']().all())

    for f in (filters or []):
        field_key = f.get('field')
        spec = source['fields'].get(field_key)
        if not spec:
            continue
        operator = f.get('operator')
        raw_value = f.get('value')
        rows = [r for r in rows if _matches(spec['get'](r), spec['type'], operator, raw_value)]

    distances = {}
    if location_filter and source.get('location'):
        try:
            center_lat = float(location_filter['lat'])
            center_lng = float(location_filter['lng'])
            radius = float(location_filter['radius_km'])
        except (TypeError, ValueError, KeyError):
            center_lat = center_lng = radius = None
        if center_lat is not None:
            kept = []
            for r in rows:
                lat, lng = source['location'](r)
                if lat is None or lng is None:
                    continue
                d = haversine_distance(center_lat, center_lng, lat, lng)
                if d <= radius:
                    distances[id(r)] = d
                    kept.append(r)
            rows = kept

    grouped = None
    if group_by and group_by in source['fields']:
        spec = source['fields'][group_by]
        counts = {}
        for r in rows:
            v = spec['get'](r)
            key = v if v not in (None, '') else '(blank)'
            counts[key] = counts.get(key, 0) + 1
        grouped = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    else:
        if sort_by and sort_by in source['fields']:
            spec = source['fields'][sort_by]
            rows.sort(key=lambda r: (spec['get'](r) is None, spec['get'](r)),
                     reverse=(sort_dir == 'desc'))
        elif distances:
            rows.sort(key=lambda r: distances.get(id(r), 0))

    columns = list(source['columns'])
    if distances:
        columns = columns + [('Distance (km)', lambda r: round(distances.get(id(r), 0), 1))]

    return {
        'rows': rows,
        'columns': columns,
        'grouped': grouped,
        'source_label': source['label'],
        'count': len(rows),
    }
