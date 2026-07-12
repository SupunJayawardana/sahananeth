from app import create_app
from app.extensions import db

app = create_app('development')

with app.app_context():
    from app.models.user import User
    from app.models.warehouse import Warehouse, InventoryStock
    from app.models.warehouse_assignment import WarehouseAssignment
    from app.models.product import Product

    # --- Super Admin ---
    if not User.query.filter_by(username='superadmin').first():
        admin = User(username='superadmin', full_name='System Administrator',
                     role_level='super_admin', status='active')
        admin.set_password('admin1234')
        db.session.add(admin)
        db.session.commit()
        print('✅ Super admin created.')
    else:
        print('ℹ️  Super admin already exists.')

    admin = User.query.filter_by(username='superadmin').first()

    # --- Sample Staff Users ---
    sample_users = [
        # Gov Officers
        ('gov1', 'Kamal Perera', 'gov_officer', 'active'),
        ('gov2', 'Nimal Silva', 'gov_officer', 'active'),
        # Field Officers
        ('field1', 'Sunil Fernando', 'field_officer', 'active'),
        ('field2', 'Amara Jayasinghe', 'field_officer', 'active'),
        ('field3', 'Ravi Bandara', 'field_officer', 'active'),
        # Warehouse Managers
        ('wm1', 'Chamara Gunasekara', 'warehouse_manager', 'active'),
        ('wm2', 'Dilini Wickrama', 'warehouse_manager', 'active'),
        ('wm3', 'Pradeep Rajapaksa', 'warehouse_manager', 'active'),
        # Citizens
        ('citizen1', 'Saman Kumara', 'citizen', 'active'),
        ('citizen2', 'Mala Dissanayake', 'citizen', 'active'),
        ('citizen3', 'Rohan Wijeratne', 'citizen', 'active'),
    ]

    for username, full_name, role, status in sample_users:
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                full_name=full_name,
                role_level=role,
                status=status
            )
            user.set_password('admin1234')
            db.session.add(user)
            print(f'✅ Created {role}: {username}')
        else:
            print(f'ℹ️  {username} already exists.')

    db.session.commit()

    # --- Sample Warehouses ---
    if not Warehouse.query.first():
        print('Seeding warehouses...')
        warehouses_data = [
            {
                'name': 'Colombo Central Warehouse',
                'lat': 6.9271, 'lng': 79.8612,
                'address': 'No. 1, Colombo Road, Colombo 01',
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
                'address': 'No. 45, Kandy Road, Kandy',
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
                'address': 'No. 12, Galle Fort Road, Galle',
                'stock': [
                    ('Rice', 250, 'kg'),
                    ('Drinking Water', 600, 'liters'),
                    ('Blankets', 150, 'units'),
                    ('Baby Food', 100, 'units'),
                ]
            },
        ]

        wm1 = User.query.filter_by(username='wm1').first()
        wm2 = User.query.filter_by(username='wm2').first()
        wm3 = User.query.filter_by(username='wm3').first()

        for i, w in enumerate(warehouses_data):
            warehouse = Warehouse(
                warehouse_name=w['name'],
                latitude=w['lat'],
                longitude=w['lng'],
                address=w['address'],
                status='active',
                created_by_id=admin.id,
                approved_by_id=admin.id
            )
            db.session.add(warehouse)
            db.session.flush()

            for sku, qty, unit in w['stock']:
                item = InventoryStock(
                    warehouse_id=warehouse.id,
                    sku_name=sku,
                    quantity_available=qty,
                    metric_unit=unit,
                    threshold=20
                )
                db.session.add(item)

            # Assign one warehouse manager per warehouse
            manager = [wm1, wm2, wm3][i]
            if manager:
                assignment = WarehouseAssignment(
                    user_id=manager.id,
                    warehouse_id=warehouse.id,
                    assigned_by_id=admin.id
                )
                db.session.add(assignment)
                print(f'✅ Assigned {manager.username} to {w["name"]}')

        db.session.commit()
        print('✅ Warehouses seeded.')
    else:
        print('ℹ️  Warehouses already exist.')

    # --- Starter Product Catalog ---
    if not Product.query.first():
        print('Seeding product catalog...')
        products = [
            ('Rice', 'Food', 'kg', 'Staple food item'),
            ('Bread', 'Food', 'units', 'Packaged bread loaves'),
            ('Canned Food', 'Food', 'units', 'Assorted canned goods'),
            ('Baby Food', 'Food', 'units', 'Infant formula and food packs'),
            ('Biscuits', 'Food', 'packs', 'Energy biscuit packs'),
            ('Drinking Water', 'Water', 'liters', 'Bottled or purified water'),
            ('Water Purification Tablets', 'Water', 'units', 'Tablet-based purification'),
            ('First Aid Kits', 'Medicine', 'units', 'Basic first aid kit'),
            ('Medicine Packs', 'Medicine', 'units', 'General medicine assortment'),
            ('ORS Packets', 'Medicine', 'packs', 'Oral rehydration salts'),
            ('Tents', 'Shelter', 'units', 'Family-size relief tents'),
            ('Blankets', 'Shelter', 'units', 'Thermal blankets'),
            ('Tarpaulins', 'Shelter', 'units', 'Waterproof tarpaulin sheets'),
            ('Hygiene Kits', 'Hygiene', 'units', 'Soap, toothbrush, sanitizer'),
            ('Sanitary Pads', 'Hygiene', 'packs', 'Feminine hygiene packs'),
            ('Clothing Bundles', 'Clothing', 'units', 'Mixed adult clothing'),
            ('Children Clothing', 'Clothing', 'units', 'Mixed children clothing'),
        ]

        for name, category, unit, desc in products:
            product = Product(
                name=name,
                category=category,
                default_unit=unit,
                description=desc,
                is_active=True,
                created_by_id=admin.id
            )
            db.session.add(product)

        db.session.commit()
        print(f'✅ {len(products)} products seeded.')
    else:
        print('ℹ️  Products already exist.')

    # --- Summary ---
    print('\n--- Verification ---')
    print(f'Users:       {User.query.count()}')
    print(f'Warehouses:  {Warehouse.query.count()}')
    print(f'Stock items: {InventoryStock.query.count()}')
    print(f'Products:    {Product.query.count()}')
    print(f'Assignments: {WarehouseAssignment.query.count()}')
    print('\n--- Sample Login Credentials (all password: admin1234) ---')
    print('superadmin  → Super Admin')
    print('gov1        → Government Officer')
    print('wm1         → Warehouse Manager (Colombo)')
    print('wm2         → Warehouse Manager (Kandy)')
    print('wm3         → Warehouse Manager (Galle)')
    print('field1      → Field Officer')
    print('citizen1    → Citizen')