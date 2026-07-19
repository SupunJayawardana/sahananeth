"""telegram bot integration and password reset

Revision ID: c9624b1d9d0b
Revises: dcb8807498d5
Create Date: 2026-07-16 04:27:20.333672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9624b1d9d0b'
down_revision = 'dcb8807498d5'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'telegram_conversation_states' not in existing_tables:
        op.create_table('telegram_conversation_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.String(length=64), nullable=False),
        sa.Column('flow_name', sa.String(length=50), nullable=False),
        sa.Column('step', sa.String(length=50), nullable=False),
        sa.Column('data_json', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
        )
    if 'notifications' not in existing_tables:
        op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('auto_alert', 'announcement', name='notification_category_enum'), nullable=False),
        sa.Column('urgency', sa.Enum('info', 'warning', 'critical', name='notification_urgency_enum'), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('message', sa.String(length=1000), nullable=False),
        sa.Column('criteria_json', sa.Text(), nullable=True),
        sa.Column('sent_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sent_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if 'password_reset_tokens' not in existing_tables:
        op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=12), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if 'telegram_link_tokens' not in existing_tables:
        op.create_table('telegram_link_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
        )
    if 'citizen_aid_requests' not in existing_tables:
        op.create_table('citizen_aid_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('citizen_user_id', sa.Integer(), nullable=False),
        sa.Column('shelter_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'resolved', name='aid_request_status_enum'), nullable=False),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['shelter_id'], ['shelters.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if 'notification_deliveries' not in existing_tables:
        op.create_table('notification_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('sent', 'failed', 'skipped_not_linked', name='delivery_status_enum'), nullable=False),
        sa.Column('error_message', sa.String(length=255), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    shelter_cols = {c['name'] for c in inspector.get_columns('shelters')}
    with op.batch_alter_table('shelters', schema=None) as batch_op:
        if 'country' not in shelter_cols:
            batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        if 'region' not in shelter_cols:
            batch_op.add_column(sa.Column('region', sa.String(length=100), nullable=True))
        if 'city' not in shelter_cols:
            batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))

    user_cols = {c['name'] for c in inspector.get_columns('users')}
    user_constraints = {c['name'] for c in inspector.get_unique_constraints('users')}
    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'telegram_chat_id' not in user_cols:
            batch_op.add_column(sa.Column('telegram_chat_id', sa.String(length=64), nullable=True))
        if 'telegram_linked_at' not in user_cols:
            batch_op.add_column(sa.Column('telegram_linked_at', sa.DateTime(), nullable=True))
        if 'notify_opt_in' not in user_cols:
            batch_op.add_column(sa.Column('notify_opt_in', sa.Boolean(), nullable=False, server_default=sa.true()))
        if 'country' not in user_cols:
            batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        if 'region' not in user_cols:
            batch_op.add_column(sa.Column('region', sa.String(length=100), nullable=True))
        if 'city' not in user_cols:
            batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
        if not any('telegram_chat_id' in str(name) for name in user_constraints) and 'telegram_chat_id' not in user_cols:
            pass  # constraint already added implicitly when column is new
    # Unique constraint on telegram_chat_id — only add if the column is new
    # (SQLite/Postgres both accept a duplicate-named constraint being skipped safely here
    # because add_column above already guards on column existence)
    if 'telegram_chat_id' not in user_cols:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_users_telegram_chat_id', ['telegram_chat_id'])


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_telegram_chat_id', type_='unique')
        batch_op.drop_column('city')
        batch_op.drop_column('region')
        batch_op.drop_column('country')
        batch_op.drop_column('notify_opt_in')
        batch_op.drop_column('telegram_linked_at')
        batch_op.drop_column('telegram_chat_id')

    with op.batch_alter_table('shelters', schema=None) as batch_op:
        batch_op.drop_column('city')
        batch_op.drop_column('region')
        batch_op.drop_column('country')

    op.drop_table('notification_deliveries')
    op.drop_table('citizen_aid_requests')
    op.drop_table('telegram_link_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_table('notifications')
    op.drop_table('telegram_conversation_states')
    # ### end Alembic commands ###
