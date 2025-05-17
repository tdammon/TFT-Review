"""Add event_id to comments table

Revision ID: add_event_id_to_comments
Revises: 22da4a8bc75b
Create Date: 2023-05-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_event_id_to_comments'
down_revision = '22da4a8bc75b'
branch_labels = None
depends_on = None


def upgrade():
    # Add event_id column to comments table
    op.add_column('comment', sa.Column('event_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_comment_event_id', 'comment', 'event', ['event_id'], ['id'])


def downgrade():
    # Remove event_id column from comments table
    op.drop_constraint('fk_comment_event_id', 'comment', type_='foreignkey')
    op.drop_column('comment', 'event_id') 