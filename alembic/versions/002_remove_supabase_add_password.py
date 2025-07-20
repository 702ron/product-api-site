"""Remove Supabase, add password authentication

Revision ID: 002_remove_supabase_add_password
Revises: 001_initial_migration
Create Date: 2025-07-19 20:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_remove_supabase_add_password'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hashed_password column
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))
    
    # Add is_verified column
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Drop supabase_user_id column and its constraints
    op.drop_index('ix_users_supabase_user_id', table_name='users')
    op.drop_column('users', 'supabase_user_id')


def downgrade() -> None:
    # Add back supabase_user_id column
    op.add_column('users', sa.Column('supabase_user_id', sa.String(255), nullable=True))
    op.create_index('ix_users_supabase_user_id', 'users', ['supabase_user_id'], unique=True)
    
    # Drop new columns
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'hashed_password')