"""Add admin dashboard system tables

Revision ID: 003
Revises: 002_remove_supabase_add_password
Create Date: 2025-07-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002_remove_supabase_add_password'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_users table
    op.create_table('admin_users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('admin_role', sa.String(length=50), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("admin_role IN ('super_admin', 'admin', 'moderator', 'viewer')", name='valid_admin_role'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create admin_sessions table
    op.create_table('admin_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('admin_user_id', sa.String(length=36), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('login_at', sa.DateTime(), nullable=False),
        sa.Column('logout_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create admin_actions table
    op.create_table('admin_actions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('admin_user_id', sa.String(length=36), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.CheckConstraint('duration_ms IS NULL OR duration_ms >= 0', name='non_negative_duration'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_actions_created_at', 'admin_actions', ['created_at'], unique=False)

    # Create system_config table
    op.create_table('system_config',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False),
        sa.Column('updated_by', sa.String(length=36), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('default_value', sa.JSON(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('requires_restart', sa.Boolean(), nullable=False),
        sa.CheckConstraint("config_type IN ('feature_flag', 'setting', 'threshold', 'api_limit', 'notification')", name='valid_config_type'),
        sa.ForeignKeyConstraint(['updated_by'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('key')
    )

    # Create security_events table
    op.create_table('security_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('admin_user_id', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_by', sa.String(length=36), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('false_positive', sa.Boolean(), nullable=False),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='valid_severity'),
        sa.CheckConstraint('risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)', name='valid_risk_score'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['admin_users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_security_events_created_at', table_name='security_events')
    op.drop_table('security_events')
    op.drop_table('system_config')
    op.drop_index('ix_admin_actions_created_at', table_name='admin_actions')
    op.drop_table('admin_actions')
    op.drop_table('admin_sessions')
    op.drop_table('admin_users')