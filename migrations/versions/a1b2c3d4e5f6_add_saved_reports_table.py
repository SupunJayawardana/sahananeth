"""add saved_reports table

Revision ID: a1b2c3d4e5f6
Revises: f3a8c1d2e6b7
Create Date: 2026-07-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f3a8c1d2e6b7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'saved_reports' not in existing_tables:
        op.create_table('saved_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=300), nullable=True),
        sa.Column('source_key', sa.String(length=50), nullable=False),
        sa.Column('filters_json', sa.Text(), nullable=True),
        sa.Column('location_filter_json', sa.Text(), nullable=True),
        sa.Column('group_by', sa.String(length=50), nullable=True),
        sa.Column('sort_by', sa.String(length=50), nullable=True),
        sa.Column('sort_dir', sa.String(length=4), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'saved_reports' in existing_tables:
        op.drop_table('saved_reports')
