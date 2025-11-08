"""Add size_bytes and composite index for messages

Revision ID: 003
Revises: 001
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add size_bytes column and composite index for efficient querying"""
    
    # Add size_bytes column to messages table
    op.add_column('messages', 
        sa.Column('size_bytes', sa.Integer(), nullable=True)
    )
    
    # Create composite index for efficient unseen message queries
    op.create_index(
        'idx_messages_unseen', 
        'messages', 
        ['link_token', 'seen', 'created_at']
    )


def downgrade():
    """Remove size_bytes column and composite index"""
    
    # Drop composite index
    op.drop_index('idx_messages_unseen', table_name='messages')
    
    # Drop size_bytes column
    op.drop_column('messages', 'size_bytes')
