"""Initial schema for pycrypt

Revision ID: 001
Revises: 
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial tables for simplex link-based E2EE chat"""
    
    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('link_token', sa.String(128), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
    sa.Column('public_key_hash', sa.String(64), nullable=False),
    sa.Column('key_type', sa.String(16), nullable=False, server_default='ed25519'),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('fetch_token_hash', sa.String(128), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('link_token'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for clients table
    op.create_index('idx_link_token', 'clients', ['link_token'])
    op.create_index('idx_public_key_hash', 'clients', ['public_key_hash'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('link_token', sa.String(128), nullable=False),
        sa.Column('encrypted_message', sa.Text(length=4294967295), nullable=False),  # LONGTEXT
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('seen', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for messages table
    op.create_index('idx_link_token', 'messages', ['link_token'])
    op.create_index('idx_created_at', 'messages', ['created_at'])
    op.create_index('idx_seen', 'messages', ['seen'])
    
    # Create challenges table
    op.create_table(
        'challenges',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('link_token', sa.String(128), nullable=False),
    sa.Column('challenge_nonce', sa.String(255), nullable=False),
    sa.Column('client_ip', sa.String(45), nullable=True),
    sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('used', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for challenges table
    op.create_index('idx_link_token', 'challenges', ['link_token'])
    op.create_index('idx_expires_at', 'challenges', ['expires_at'])
    
    # Create message_requests table for permission-based messaging
    op.create_table(
        'message_requests',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('from_link_token', sa.String(128), nullable=False),
        sa.Column('to_link_token', sa.String(128), nullable=False),
        sa.Column('from_nickname', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('pending', 'accepted', 'rejected', name='request_status'), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for message_requests table
    op.create_index('idx_to_link_token', 'message_requests', ['to_link_token'])
    op.create_index('idx_from_link_token', 'message_requests', ['from_link_token'])
    op.create_index('idx_status', 'message_requests', ['status'])


def downgrade():
    """Remove all tables"""
    op.drop_table('message_requests')
    op.drop_table('challenges')
    op.drop_table('messages')
    op.drop_table('clients')
