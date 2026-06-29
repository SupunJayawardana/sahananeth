from app import create_app
from app.extensions import db

# 1. Create the app instance first
app = create_app('development')

with app.app_context():
    # 2. Import the model safely inside the application context
    from app.models.user import User
    
    # Check if super admin already exists
    existing = User.query.filter_by(username='superadmin').first()
    if existing:
        print('Super admin already exists.')
    else:
        admin = User(
            username='superadmin',
            full_name='System Administrator',
            role_level='super_admin',
            status='active'
        )
        admin.set_password('admin1234')  # Change this!
        db.session.add(admin)
        db.session.commit()
        print('Super admin created successfully.')
        print('Username: superadmin')
        print('Password: admin1234')