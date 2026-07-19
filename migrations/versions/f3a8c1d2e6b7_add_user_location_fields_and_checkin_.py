"""add user location fields and checkin tables

Revision ID: f3a8c1d2e6b7
Revises: c9624b1d9d0b
Create Date: 2026-07-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a8c1d2e6b7'
down_revision = 'c9624b1d9d0b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # --- User: GPS coordinates, captured via browser geolocation (web) or
    #     a shared Telegram location message (bot). Distinct from the
    #     existing free-text country/region/city — this is what actually
    #     powers distance/proximity calculations and the analytics map's
    #     new citizen layer. ---
    user_cols = {c['name'] for c in inspector.get_columns('users')}
    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'latitude' not in user_cols:
            batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        if 'longitude' not in user_cols:
            batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))
        if 'location_updated_at' not in user_cols:
            batch_op.add_column(sa.Column('location_updated_at', sa.DateTime(), nullable=True))

    # --- Safety check-in campaigns ---
    if 'checkins' not in existing_tables:
        op.create_table('checkins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('criteria_json', sa.Text(), nullable=True),
        sa.Column('sent_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('notification_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['sent_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'checkin_responses' not in existing_tables:
        op.create_table('checkin_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'safe', 'need_help', name='checkin_response_status_enum'), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['checkin_id'], ['checkins.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    op.drop_table('checkin_responses')
    op.drop_table('checkins')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('location_updated_at')
        batch_op.drop_column('longitude')
        batch_op.drop_column('latitude')
