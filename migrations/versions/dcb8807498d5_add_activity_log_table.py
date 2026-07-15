"""add activity log table

Revision ID: dcb8807498d5
Revises: df049df3c5b4
Create Date: 2026-07-15 02:03:10.313693

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcb8807498d5'
down_revision = 'df049df3c5b4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'activity_logs' not in existing_tables:
        op.create_table('activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('auth', 'user', 'shelter', 'warehouse', 'procurement', 'alert', name='activity_category_enum'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    # shelter_registration_requests was never captured in the original
    # baseline migration even though the model has existed for a while.
    # On most real deployments it already exists because run.py calls
    # db.create_all() on startup, which silently creates any missing
    # model table. On a genuinely fresh database (e.g. CI, a new
    # developer clone) that never ran create_all(), it would still be
    # missing — so we create it here too, guarded by an existence check
    # so this migration is safe to run either way.
    if 'shelter_registration_requests' not in existing_tables:
        op.create_table('shelter_registration_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('citizen_user_id', sa.Integer(), nullable=True),
        sa.Column('shelter_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('identification_number', sa.String(length=50), nullable=False),
        sa.Column('phone_number', sa.String(length=30), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='registration_status_enum'), nullable=False),
        sa.Column('created_by_role', sa.String(length=50), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['shelter_id'], ['shelters.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'shelter_registration_requests' in existing_tables:
        op.drop_table('shelter_registration_requests')
    if 'activity_logs' in existing_tables:
        op.drop_table('activity_logs')
