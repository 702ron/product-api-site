"""Fix credit_transactions id autoincrement

Revision ID: 004_fix_credit_transactions_autoincrement
Revises: 003_add_admin_dashboard_system_tables
Create Date: 2025-07-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix the credit_transactions table to properly use AUTOINCREMENT for the id field.
    Also fix user_id type consistency between users and credit_transactions tables.
    SQLite requires us to recreate the table to add AUTOINCREMENT.
    """
    
    # First, update users table id field from UUID to VARCHAR(36) to match models
    op.execute("""
        CREATE TABLE users_new (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            full_name VARCHAR(255),
            credit_balance INTEGER NOT NULL DEFAULT 10,
            hashed_password VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT credit_balance_non_negative CHECK (credit_balance >= 0)
        )
    """)
    
    # Copy users data
    op.execute("""
        INSERT INTO users_new (
            id, email, full_name, credit_balance, hashed_password,
            is_active, is_verified, created_at, updated_at
        )
        SELECT 
            id, email, full_name, credit_balance, hashed_password,
            is_active, is_verified, created_at, updated_at
        FROM users
    """)
    
    # Drop old users table
    op.drop_table('users')
    
    # Rename new users table
    op.execute("ALTER TABLE users_new RENAME TO users")
    
    # Recreate users indexes
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create new credit_transactions table with proper autoincrement and matching user_id type
    op.execute("""
        CREATE TABLE credit_transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(36) NOT NULL,
            amount INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            operation VARCHAR(100),
            description TEXT,
            stripe_session_id VARCHAR(255),
            stripe_payment_intent_id VARCHAR(255),
            extra_data JSON,
            created_at DATETIME NOT NULL,
            CONSTRAINT valid_transaction_type CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'adjustment')),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    
    # Copy existing data if any exists
    op.execute("""
        INSERT INTO credit_transactions_new (
            user_id, amount, transaction_type, operation, description,
            stripe_session_id, stripe_payment_intent_id, extra_data, created_at
        )
        SELECT 
            user_id, amount, transaction_type, operation, description,
            stripe_session_id, stripe_payment_intent_id, extra_data, created_at
        FROM credit_transactions
    """)
    
    # Drop old table
    op.drop_table('credit_transactions')
    
    # Rename new table
    op.execute("ALTER TABLE credit_transactions_new RENAME TO credit_transactions")
    
    # Recreate indexes
    op.create_index('ix_credit_transactions_created_at', 'credit_transactions', ['created_at'])
    op.create_index('ix_credit_transactions_stripe_payment_intent_id', 'credit_transactions', ['stripe_payment_intent_id'])
    op.create_index('ix_credit_transactions_stripe_session_id', 'credit_transactions', ['stripe_session_id'])


def downgrade() -> None:
    """
    Revert back to the original table structure.
    """
    
    # Revert users table back to UUID
    op.execute("""
        CREATE TABLE users_old (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            full_name VARCHAR(255),
            credit_balance INTEGER NOT NULL DEFAULT 10,
            hashed_password VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT credit_balance_non_negative CHECK (credit_balance >= 0)
        )
    """)
    
    # Copy users data back
    op.execute("""
        INSERT INTO users_old (
            id, email, full_name, credit_balance, hashed_password,
            is_active, is_verified, created_at, updated_at
        )
        SELECT 
            id, email, full_name, credit_balance, hashed_password,
            is_active, is_verified, created_at, updated_at
        FROM users
    """)
    
    # Drop current users table
    op.drop_table('users')
    
    # Rename old users table back
    op.execute("ALTER TABLE users_old RENAME TO users")
    
    # Recreate users indexes
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create original credit_transactions table structure
    op.execute("""
        CREATE TABLE credit_transactions_old (
            id BIGINT NOT NULL,
            user_id UUID NOT NULL,
            amount INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            operation VARCHAR(100),
            description TEXT,
            stripe_session_id VARCHAR(255),
            stripe_payment_intent_id VARCHAR(255),
            extra_data JSON,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT valid_transaction_type CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'adjustment')),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    
    # Copy data back
    op.execute("""
        INSERT INTO credit_transactions_old (
            id, user_id, amount, transaction_type, operation, description,
            stripe_session_id, stripe_payment_intent_id, extra_data, created_at
        )
        SELECT 
            id, user_id, amount, transaction_type, operation, description,
            stripe_session_id, stripe_payment_intent_id, extra_data, created_at
        FROM credit_transactions
    """)
    
    # Drop new table
    op.drop_table('credit_transactions')
    
    # Rename old table back
    op.execute("ALTER TABLE credit_transactions_old RENAME TO credit_transactions")
    
    # Recreate indexes
    op.create_index('ix_credit_transactions_created_at', 'credit_transactions', ['created_at'])
    op.create_index('ix_credit_transactions_stripe_payment_intent_id', 'credit_transactions', ['stripe_payment_intent_id'])
    op.create_index('ix_credit_transactions_stripe_session_id', 'credit_transactions', ['stripe_session_id'])