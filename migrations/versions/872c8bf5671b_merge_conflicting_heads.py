"""merge conflicting heads

Revision ID: 872c8bf5671b
Revises: a03957d9c2ba, a1b2c3d4e5f6
Create Date: 2026-07-20 14:54:14.176390

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '872c8bf5671b'
down_revision = ('a03957d9c2ba', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
