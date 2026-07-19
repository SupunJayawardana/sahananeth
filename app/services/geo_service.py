import math
from app.models.warehouse import Warehouse, InventoryStock
from app.models.shelter import Shelter


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate real-world distance between two GPS coordinates.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in km

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + \
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2

    c = 2 * math.asin(math.sqrt(a))
    return round(R * c, 2)


def estimate_travel_time(distance_km):
    """Rough estimate assuming 60km/h average speed for relief vehicles."""
    minutes = (distance_km / 60) * 60
    if minutes < 60:
        return f'{int(minutes)} min'
    hours = minutes / 60
    return f'{hours:.1f} hrs'


def find_matching_warehouses(shelter, requested_sku, quantity_needed):
    """
    Find and rank warehouses by:
    1. Has sufficient stock of requested item
    2. Sorted by distance from shelter (nearest first)
    Returns list of dicts with warehouse info + distance + stock
    """
    if not shelter.latitude or not shelter.longitude:
        # No coordinates — return all warehouses with stock, unranked
        warehouses = Warehouse.query.filter_by(status='active').all()
        results = []
        for w in warehouses:
            stock = InventoryStock.query.filter_by(
                warehouse_id=w.id,
                sku_name=requested_sku
            ).first()
            results.append({
                'warehouse': w,
                'stock': stock,
                'quantity_available': stock.quantity_available if stock else 0,
                'has_sufficient': stock and stock.quantity_available >= quantity_needed,
                'distance_km': None,
                'travel_time': None,
                'recommended': False
            })
        return results

    warehouses = Warehouse.query.filter_by(status='active').all()
    results = []

    for w in warehouses:
        stock = InventoryStock.query.filter_by(
            warehouse_id=w.id,
            sku_name=requested_sku
        ).first()

        qty = stock.quantity_available if stock else 0
        has_sufficient = stock and qty >= quantity_needed

        if w.latitude and w.longitude:
            distance = haversine_distance(
                shelter.latitude, shelter.longitude,
                w.latitude, w.longitude
            )
            travel_time = estimate_travel_time(distance)
        else:
            distance = None
            travel_time = 'Unknown'

        results.append({
            'warehouse': w,
            'stock': stock,
            'quantity_available': qty,
            'has_sufficient': has_sufficient,
            'distance_km': distance,
            'travel_time': travel_time,
            'recommended': False
        })

    # Sort: sufficient stock first, then by distance
    results.sort(key=lambda x: (
        0 if x['has_sufficient'] else 1,
        x['distance_km'] if x['distance_km'] is not None else 99999
    ))

    # Mark top result as recommended
    if results and results[0]['has_sufficient']:
        results[0]['recommended'] = True

    return results


def get_citizen_points(checkin_id=None):
    """
    Citizen location points for the analytics map. Previously there was
    no citizen layer at all — only shelters/warehouses. If checkin_id is
    given, each point is colored by that check-in's response status
    instead of just being a plain dot, so "how many people have
    responded, and where" is visible directly on the map.
    """
    from app.models.user import User
    query = User.query.filter(
        User.role_level == 'citizen',
        User.latitude.isnot(None),
        User.longitude.isnot(None),
    )
    users = query.all()

    status_by_user = {}
    if checkin_id:
        from app.models.checkin import CheckInResponse
        for r in CheckInResponse.query.filter_by(checkin_id=checkin_id).all():
            status_by_user[r.user_id] = 'no_response' if r.status == 'pending' else r.status

    points = []
    for u in users:
        points.append({
            'id': u.id,
            'name': u.full_name or u.username,
            'lat': u.latitude,
            'lng': u.longitude,
            'type': 'citizen',
            'checkin_status': status_by_user.get(u.id, 'no_response' if checkin_id else None),
        })
    return points


def get_all_locations_geojson(checkin_id=None):
    """
    Returns shelters, warehouses, and citizens as GeoJSON-compatible
    dict for Leaflet.js map rendering.
    """
    shelters = Shelter.query.filter_by(status='active').all()
    warehouses = Warehouse.query.filter_by(status='active').all()

    shelter_points = []
    for s in shelters:
        if s.latitude and s.longitude:
            shelter_points.append({
                'id': s.id,
                'name': s.shelter_name,
                'lat': s.latitude,
                'lng': s.longitude,
                'type': 'shelter',
                'capacity': s.maximum_capacity,
                'occupancy': s.current_occupancy_count,
                'occupancy_pct': round(
                    (s.current_occupancy_count / s.maximum_capacity * 100)
                    if s.maximum_capacity > 0 else 0, 1
                )
            })

    warehouse_points = []
    for w in warehouses:
        if w.latitude and w.longitude:
            total_items = sum(i.quantity_available for i in w.inventory)
            low_stock_count = sum(1 for i in w.inventory if i.is_low)
            warehouse_points.append({
                'id': w.id,
                'name': w.warehouse_name,
                'lat': w.latitude,
                'lng': w.longitude,
                'type': 'warehouse',
                'total_items': total_items,
                'low_stock_count': low_stock_count,
                'stock_items': [
                    {
                        'name': i.sku_name,
                        'qty': i.quantity_available,
                        'unit': i.metric_unit,
                        'low': i.is_low
                    }
                    for i in w.inventory
                ]
            })

    return {
        'shelters': shelter_points,
        'warehouses': warehouse_points,
        'citizens': get_citizen_points(checkin_id=checkin_id),
    }