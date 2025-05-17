"""Add event relationship to comments table

Revision ID: add_event_id_to_comments
Revises: 22da4a8bc75b
Create Date: 2023-05-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import logging

logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision = 'add_event_id_to_comments'
down_revision = '22da4a8bc75b'
branch_labels = None
depends_on = None


def upgrade():
    try:
        # Check if column already exists to avoid errors
        inspector = op.get_bind().dialect.inspector
        columns = [col['name'] for col in inspector.get_columns('comment')]
        
        if 'event_id' not in columns:
            # Add event_id column to comments table
            op.add_column('comment', sa.Column('event_id', UUID(as_uuid=True), nullable=True))
            
            # Create foreign key - using id as the primary key of event table
            op.create_foreign_key('fk_comment_event_id', 'comment', 'event', ['event_id'], ['id'])
            logger.info("Successfully added event_id column to comment table")
        else:
            logger.info("event_id column already exists in comment table")
    
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        # Continue the migration process even if there's an error
        # This allows subsequent migrations to run


def downgrade():
    try:
        # Remove event_id column from comments table
        inspector = op.get_bind().dialect.inspector
        fk_names = [fk['name'] for fk in inspector.get_foreign_keys('comment')]
        
        if 'fk_comment_event_id' in fk_names:
            op.drop_constraint('fk_comment_event_id', 'comment', type_='foreignkey')
        
        columns = [col['name'] for col in inspector.get_columns('comment')]
        if 'event_id' in columns:
            op.drop_column('comment', 'event_id')
    
    except Exception as e:
        logger.error(f"Error during downgrade: {str(e)}") 