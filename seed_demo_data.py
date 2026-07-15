"""
seed_demo_data.py
------------------
Run this AFTER seed.py (which creates the base admin/staff/warehouse accounts).
This script adds a full spread of realistic demo data so every screen and
workflow in the app has something to show: shelters in every status,
citizens/beneficiaries, shelter registration requests, procurement requests
in every stage, stock transfers, alerts, and activity log entries.

Usage:
    python seed_demo_data.py

Safe to re-run — it checks for its own marker records before inserting.
"""
import os
import random
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db

app = create_app(os.environ.get('FLASK_ENV', 'development'))

with app.app_context():
    from app.models.user import User
    from app.models.shelter import Shelter, ShelterInventory
    from app.models.beneficiary import Beneficiary
    from app.models.shelter_registration import ShelterRegistrationRequest
    from app.models.warehouse import Warehouse, InventoryStock
    from app.models.procurement import ProcurementRequest
    from app.models.stock_transfer import StockTransfer
    from app.models.alert import Alert
    from app.models.activity_log import ActivityLog
    from app.models.product import Product

    admin = User.query.filter_by(username='superadmin').first()
    if not admin:
        print('❌ Run seed.py first — no superadmin found.')
        raise SystemExit(1)

    gov1 = User.query.filter_by(username='gov1').first()
    gov2 = User.query.filter_by(username='gov2').first()
    field1 = User.query.filter_by(username='field1').first()
    field2 = User.query.filter_by(username='field2').first()
    field3 = User.query.filter_by(username='field3').first()
    wm1 = User.query.filter_by(username='wm1').first()
    wm2 = User.query.filter_by(username='wm2').first()
    wm3 = User.query.filter_by(username='wm3').first()

    if not all([gov1, gov2, field1, field2, field3, wm1, wm2, wm3]):
        print('❌ Run seed.py first — base staff users are missing.')
        raise SystemExit(1)

    # ------------------------------------------------------------------
    # 1. Extra staff accounts in every status (for approval-queue testing)
    # ------------------------------------------------------------------
    pending_and_rejected_users = [
        ('gov3_pending', 'Priya Rathnayake', 'gov_officer', 'pending'),
        ('field4_pending', 'Nadeesha Perera', 'field_officer', 'pending'),
        ('field5_rejected', 'Chathura Wijesinghe', 'field_officer', 'rejected'),
        ('wm4_pending', 'Ishara Karunaratne', 'warehouse_manager', 'pending'),
        ('wm5_rejected', 'Buddhika Senanayake', 'warehouse_manager', 'rejected'),
    ]
    for username, full_name, role, status in pending_and_rejected_users:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, full_name=full_name, role_level=role, status=status)
            u.set_password('admin1234')
            db.session.add(u)
            print(f'✅ Created {status} {role}: {username}')
    db.session.commit()

    # ------------------------------------------------------------------
    # 2. Citizen accounts (for the citizen-facing shelter request flow)
    # ------------------------------------------------------------------
    citizens_data = [
        ('citizen4', 'Anushka Weerasinghe'),
        ('citizen5', 'Harshani Gunawardena'),
        ('citizen6', 'Lasantha Abeywickrama'),
    ]
    for username, full_name in citizens_data:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, full_name=full_name, role_level='citizen', status='active')
            u.set_password('admin1234')
            db.session.add(u)
            print(f'✅ Created citizen: {username}')
    db.session.commit()

    citizen_users = User.query.filter_by(role_level='citizen').all()

    # ------------------------------------------------------------------
    # 3. Shelters — a mix of pending / active / inactive, varied occupancy
    # ------------------------------------------------------------------
    if Shelter.query.count() == 0:
        shelters_data = [
            # name, lat, lng, address, capacity, occupancy, status, created_by, approved_by
            ('Colombo Community Hall', 6.9344, 79.8428, 'No. 22, Union Place, Colombo 02',
             120, 118, 'active', field1, gov1),          # near full
            ('Kandy Municipal Shelter', 7.2955, 80.6356, 'No. 8, Peradeniya Road, Kandy',
             80, 35, 'active', field2, gov1),             # comfortable
            ('Galle Fort Relief Center', 6.0300, 80.2170, 'No. 5, Church Street, Galle',
             60, 60, 'active', field3, gov2),              # full
            ('Negombo Coastal Shelter', 7.2081, 79.8371, 'No. 14, Beach Road, Negombo',
             100, 42, 'active', field1, gov2),
            ('Matara Interim Camp', 5.9549, 80.5550, 'No. 3, Station Road, Matara',
             50, 12, 'pending_approval', field2, None),    # awaiting gov approval
            ('Jaffna North Shelter', 9.6615, 80.0255, 'No. 9, Hospital Road, Jaffna',
             70, 0, 'pending_approval', field3, None),     # awaiting gov approval
            ('Ratnapura Old School Shelter', 6.6828, 80.4014, 'No. 2, Main Street, Ratnapura',
             40, 5, 'inactive', field1, gov1),             # rejected/closed
        ]

        created_shelters = []
        for name, lat, lng, address, cap, occ, status, creator, approver in shelters_data:
            s = Shelter(
                shelter_name=name,
                latitude=lat,
                longitude=lng,
                address=address,
                maximum_capacity=cap,
                current_occupancy_count=occ,
                status=status,
                created_by_id=creator.id,
                approved_by_id=approver.id if approver else None,
            )
            db.session.add(s)
            db.session.flush()
            created_shelters.append(s)

            # A little shelter-level inventory (some deliberately low, to trigger alerts)
            for item_name, qty, threshold, unit in [
                ('Rice', random.randint(5, 200), 20, 'kg'),
                ('Drinking Water', random.randint(10, 300), 40, 'liters'),
                ('Blankets', random.randint(2, 60), 15, 'units'),
            ]:
                db.session.add(ShelterInventory(
                    shelter_id=s.id, item_name=item_name,
                    quantity=qty, threshold=threshold, metric_unit=unit
                ))

            print(f'✅ Created shelter: {name} ({status})')

        db.session.commit()
    else:
        created_shelters = Shelter.query.all()
        print('ℹ️  Shelters already exist, reusing them.')

    active_shelters = [s for s in created_shelters if s.status == 'active']

    # ------------------------------------------------------------------
    # 4. Beneficiaries allocated to active shelters
    # ------------------------------------------------------------------
    if Beneficiary.query.count() == 0:
        beneficiary_names = [
            'Kasun Herath', 'Ishani Rodrigo', 'Tharindu Mendis', 'Sachini Peiris',
            'Dinuka Wanigasekara', 'Nilmini Alwis', 'Chamindu Ekanayake', 'Vindya Samarasinghe',
        ]
        for i, name in enumerate(beneficiary_names):
            shelter = active_shelters[i % len(active_shelters)]
            linked_user = citizen_users[i % len(citizen_users)] if i % 3 == 0 else None
            b = Beneficiary(
                identification_number=f'NIC{200000 + i}',
                full_name=name,
                is_verified=(i % 4 != 0),  # most verified, a few not
                allocated_shelter_id=shelter.id,
                user_id=linked_user.id if linked_user else None,
            )
            db.session.add(b)
        db.session.commit()
        print(f'✅ {len(beneficiary_names)} beneficiaries seeded.')
    else:
        print('ℹ️  Beneficiaries already exist.')

    # ------------------------------------------------------------------
    # 5. Shelter registration requests — pending / approved / rejected
    # ------------------------------------------------------------------
    if ShelterRegistrationRequest.query.count() == 0:
        reg_data = [
            ('W.M. Sanduni Perera', '199512345V', citizen_users[0], field1, 'pending'),
            ('K.D. Ruwan Jayasundara', '198834567V', citizen_users[1], None, 'pending'),
            ('A.G. Nimalka Fernando', '199245678V', citizen_users[2], field2, 'approved'),
            ('H.M. Sampath Kumara', '200156789V', None, field3, 'rejected'),
        ]
        for i, (name, nic, citizen, created_by, status) in enumerate(reg_data):
            shelter = active_shelters[i % len(active_shelters)]
            reg = ShelterRegistrationRequest(
                citizen_user_id=citizen.id if citizen else None,
                shelter_id=shelter.id,
                full_name=name,
                identification_number=nic,
                phone_number=f'07{random.randint(10000000, 99999999)}',
                address='Displaced due to flooding',
                status=status,
                created_by_role='citizen' if created_by is None else 'field_officer',
                created_by_id=created_by.id if created_by else citizen.id,
                reviewed_by_id=gov1.id if status != 'pending' else None,
                reviewed_at=datetime.utcnow() - timedelta(days=1) if status != 'pending' else None,
            )
            db.session.add(reg)
        db.session.commit()
        print(f'✅ {len(reg_data)} shelter registration requests seeded.')
    else:
        print('ℹ️  Shelter registration requests already exist.')

    # ------------------------------------------------------------------
    # 6. Procurement requests — full spread of statuses, spread over 7 days
    # ------------------------------------------------------------------
    warehouses = Warehouse.query.filter_by(status='active').all()
    if ProcurementRequest.query.count() == 0 and active_shelters and warehouses:
        sample_items = [
            ('Rice', 'kg'), ('Drinking Water', 'liters'), ('Blankets', 'units'),
            ('First Aid Kits', 'units'), ('Canned Food', 'units'), ('Tents', 'units'),
            ('Baby Food', 'units'), ('Hygiene Kits', 'units'),
        ]
        statuses = ['pending', 'pending', 'approved', 'dispatched', 'fulfilled', 'fulfilled', 'rejected']

        requesters = [field1, field2, field3]
        for i in range(18):
            shelter = active_shelters[i % len(active_shelters)]
            requester = requesters[i % len(requesters)]
            sku, unit = sample_items[i % len(sample_items)]
            status = statuses[i % len(statuses)]
            days_ago = random.randint(0, 6)
            created = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))

            req = ProcurementRequest(
                origin_shelter_id=shelter.id,
                requested_by_id=requester.id,
                requested_sku=sku,
                quantity_needed=random.randint(10, 150),
                metric_unit=unit,
                notes='Urgent need due to recent influx of displaced families.' if i % 5 == 0 else None,
                status_state=status,
                created_at=created,
                updated_at=created + timedelta(hours=random.randint(1, 20)) if status != 'pending' else created,
            )
            if status in ('approved', 'dispatched', 'fulfilled'):
                req.fulfilled_warehouse_id = warehouses[i % len(warehouses)].id
            if status == 'fulfilled':
                req.received_quantity = req.quantity_needed

            db.session.add(req)

        db.session.commit()
        print('✅ 18 procurement requests seeded across pending/approved/dispatched/fulfilled/rejected.')
    else:
        print('ℹ️  Procurement requests already exist (or no active shelters/warehouses to attach to).')

    # ------------------------------------------------------------------
    # 7. Stock transfers between warehouses — pending / dispatched / confirmed
    # ------------------------------------------------------------------
    if StockTransfer.query.count() == 0 and len(warehouses) >= 2:
        managers = [wm1, wm2, wm3]
        transfer_data = [
            (warehouses[0], warehouses[1], 'Rice', 'kg', 100, 'pending'),
            (warehouses[1], warehouses[2], 'Drinking Water', 'liters', 200, 'dispatched'),
            (warehouses[2], warehouses[0], 'Blankets', 'units', 50, 'confirmed'),
        ]
        for i, (frm, to, sku, unit, qty, status) in enumerate(transfer_data):
            t = StockTransfer(
                from_warehouse_id=frm.id,
                to_warehouse_id=to.id,
                sku_name=sku,
                metric_unit=unit,
                quantity=qty,
                status=status,
                notes='Rebalancing stock between regional depots.',
                initiated_by_id=managers[i % len(managers)].id,
                confirmed_by_id=managers[(i + 1) % len(managers)].id if status == 'confirmed' else None,
                created_at=datetime.utcnow() - timedelta(days=i + 1),
                confirmed_at=datetime.utcnow() - timedelta(hours=2) if status == 'confirmed' else None,
            )
            db.session.add(t)
        db.session.commit()
        print('✅ 3 stock transfers seeded (pending/dispatched/confirmed).')
    else:
        print('ℹ️  Stock transfers already exist (or fewer than 2 warehouses).')

    # ------------------------------------------------------------------
    # 8. Alerts — a few of each type, mix of read/unread
    # ------------------------------------------------------------------
    if Alert.query.count() == 0:
        alert_data = [
            ('low_shelter_stock', 'Ratnapura Old School Shelter is low on Rice.', True, False),
            ('low_warehouse_stock', f'{warehouses[0].warehouse_name if warehouses else "Warehouse"} is low on First Aid Kits.', False, True),
            ('shelter_full', 'Galle Fort Relief Center has reached full capacity.', True, False),
            ('new_procurement_request', 'New procurement request submitted from Negombo Coastal Shelter.', False, False),
            ('shelter_full', 'Colombo Community Hall is nearly at full capacity.', True, True),
        ]
        for alert_type, message, has_shelter, has_warehouse in alert_data:
            a = Alert(
                alert_type=alert_type,
                message=message,
                shelter_id=active_shelters[0].id if has_shelter and active_shelters else None,
                warehouse_id=warehouses[0].id if has_warehouse and warehouses else None,
                is_read=random.choice([True, False]),
            )
            db.session.add(a)
        db.session.commit()
        print('✅ 5 alerts seeded.')
    else:
        print('ℹ️  Alerts already exist.')

    # ------------------------------------------------------------------
    # 9. Activity log entries — populate the Analytics feed with history
    # ------------------------------------------------------------------
    if ActivityLog.query.count() == 0:
        activity_data = [
            ('user', 'gov1 approved field officer Sunil Fernando.', gov1, 6),
            ('shelter', 'Shelter "Kandy Municipal Shelter" approved by gov1.', gov1, 5),
            ('warehouse', 'Warehouse "Galle Southern Store" created by superadmin.', admin, 5),
            ('procurement', 'Procurement request #1 (Rice) approved by gov1.', gov1, 4),
            ('procurement', 'Procurement request #3 (Drinking Water) dispatched by wm2.', wm2, 3),
            ('shelter', 'Citizen registration for "A.G. Nimalka Fernando" approved by gov2.', gov2, 2),
            ('user', 'Warehouse Manager Pradeep Rajapaksa approved by gov1.', gov1, 2),
            ('warehouse', 'wm3 confirmed transfer of 50 units of Blankets.', wm3, 1),
            ('procurement', 'New procurement request from "Negombo Coastal Shelter" by field1.', field1, 0),
        ]
        for category, description, user, days_ago in activity_data:
            log = ActivityLog(
                category=category,
                description=description,
                user_id=user.id if user else None,
                created_at=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
            )
            db.session.add(log)
        db.session.commit()
        print('✅ 9 activity log entries seeded.')
    else:
        print('ℹ️  Activity logs already exist.')

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print('\n--- Demo Data Summary ---')
    print(f'Users (all roles):          {User.query.count()}')
    print(f'Shelters:                   {Shelter.query.count()}')
    print(f'Beneficiaries:              {Beneficiary.query.count()}')
    print(f'Shelter registration reqs:  {ShelterRegistrationRequest.query.count()}')
    print(f'Procurement requests:       {ProcurementRequest.query.count()}')
    print(f'Stock transfers:            {StockTransfer.query.count()}')
    print(f'Alerts:                     {Alert.query.count()}')
    print(f'Activity log entries:       {ActivityLog.query.count()}')
    print('\n--- New login credentials added (all password: admin1234) ---')
    print('gov3_pending     → Gov Officer awaiting approval')
    print('field4_pending   → Field Officer awaiting approval')
    print('field5_rejected  → Field Officer (rejected)')
    print('wm4_pending      → Warehouse Manager awaiting approval')
    print('wm5_rejected     → Warehouse Manager (rejected)')
    print('citizen4/5/6     → Citizens')
