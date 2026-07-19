"""
geo_services.py
----------------
Deprecated — this used to be a byte-for-byte duplicate of geo_service.py
(same haversine/warehouse-matching code copy-pasted into two files that
had already started to matter for correctness). Kept as a thin re-export
so existing imports (approval_service.py, gov_officer.py, super_admin.py)
don't break; new code should import from geo_service instead.
"""
from app.services.geo_service import (
    haversine_distance,
    estimate_travel_time,
    find_matching_warehouses,
    get_all_locations_geojson,
)

__all__ = [
    'haversine_distance',
    'estimate_travel_time',
    'find_matching_warehouses',
    'get_all_locations_geojson',
]
