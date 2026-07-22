"""add location to citizen_aid_requests

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c['name'] for c in inspector.get_columns('citizen_aid_requests')}

    if 'latitude' not in existing_columns:
        op.add_column('citizen_aid_requests', sa.Column('latitude', sa.Float(), nullable=True))
    if 'longitude' not in existing_columns:
        op.add_column('citizen_aid_requests', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c['name'] for c in inspector.get_columns('citizen_aid_requests')}

    if 'longitude' in existing_columns:
        op.drop_column('citizen_aid_requests', 'longitude')
    if 'latitude' in existing_columns:
        op.drop_column('citizen_aid_requests', 'latitude')
