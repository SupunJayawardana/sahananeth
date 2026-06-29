from app import create_app
from app.extensions import db

app = create_app('development')

with app.app_context():
    from app.models.user import User
    from app.models.warehouse import Warehouse, InventoryStock

    # --- Super Admin ---
    if not User.query.filter_by(username='superadmin').first():
        admin = User(
            username='superadmin',
            full_name='System Administrator',
            role_level='super_admin',
            status='active'
        )
        admin.set_password('admin1234')
        db.session.add(admin)
        db.session.commit()
        print('✅ Super admin created.')
    else:
        print('ℹ️  Super admin already exists.')

    # --- Sample Warehouses ---
    if not Warehouse.query.first():
        print('Seeding warehouses...')
        warehouses_data = [
            {
                'name': 'Colombo Central Warehouse',
                'lat': 6.9271, 'lng': 79.8612,
                'stock': [
                    ('Rice', 500, 'kg'),
                    ('Drinking Water', 1000, 'liters'),
                    ('First Aid Kits', 50, 'units'),
                    ('Blankets', 200, 'units'),
                ]
            },
            {
                'name': 'Kandy Relief Depot',
                'lat': 7.2906, 'lng': 80.6337,
                'stock': [
                    ('Rice', 300, 'kg'),
                    ('Canned Food', 400, 'units'),
                    ('Medicine Packs', 80, 'units'),
                    ('Tents', 30, 'units'),
                ]
            },
            {
                'name': 'Galle Southern Store',
                'lat': 6.0535, 'lng': 80.2210,
                'stock': [
                    ('Rice', 250, 'kg'),
                    ('Drinking Water', 600, 'liters'),
                    ('Blankets', 150, 'units'),
                    ('Baby Food', 100, 'units'),
                ]
            },
        ]

        for w in warehouses_data:
            warehouse = Warehouse(
                warehouse_name=w['name'],
                latitude=w['lat'],
                longitude=w['lng']
            )
            db.session.add(warehouse)
            db.session.flush()

            for sku, qty, unit in w['stock']:
                item = InventoryStock(
                    warehouse_id=warehouse.id,
                    sku_name=sku,
                    quantity_available=qty,
                    metric_unit=unit
                )
                db.session.add(item)

        db.session.commit()
        print('✅ Warehouses and stock seeded.')
    else:
        print('ℹ️  Warehouses already exist.')

    # --- Verify ---
    print('\n--- Verification ---')
    print(f'Users: {User.query.count()}')
    print(f'Warehouses: {Warehouse.query.count()}')
    print(f'Stock items: {InventoryStock.query.count()}')