"""add_uuid_columns

Revision ID: add_uuid_columns
Revises: 971291895341
Create Date: 2023-06-10 12:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_uuid_columns'
down_revision: Union[str, None] = '971291895341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add UUID columns to all tables
    
    # User table
    op.add_column('user', sa.Column('uuid', UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE \"user\" SET uuid = gen_random_uuid()")
    op.alter_column('user', 'uuid', nullable=False)
    op.create_index(op.f('ix_user_uuid'), 'user', ['uuid'], unique=True)
    
    # Video table
    op.add_column('video', sa.Column('uuid', UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE video SET uuid = gen_random_uuid()")
    op.alter_column('video', 'uuid', nullable=False)
    op.create_index(op.f('ix_video_uuid'), 'video', ['uuid'], unique=True)
    
    # Comment table
    op.add_column('comment', sa.Column('uuid', UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE comment SET uuid = gen_random_uuid()")
    op.alter_column('comment', 'uuid', nullable=False)
    op.create_index(op.f('ix_comment_uuid'), 'comment', ['uuid'], unique=True)
    
    # Event table
    op.add_column('event', sa.Column('uuid', UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE event SET uuid = gen_random_uuid()")
    op.alter_column('event', 'uuid', nullable=False)
    op.create_index(op.f('ix_event_uuid'), 'event', ['uuid'], unique=True)


def downgrade() -> None:
    # Drop UUID columns from all tables
    op.drop_index(op.f('ix_user_uuid'), table_name='user')
    op.drop_column('user', 'uuid')
    
    op.drop_index(op.f('ix_video_uuid'), table_name='video')
    op.drop_column('video', 'uuid')
    
    op.drop_index(op.f('ix_comment_uuid'), table_name='comment')
    op.drop_column('comment', 'uuid')
    
    op.drop_index(op.f('ix_event_uuid'), table_name='event')
    op.drop_column('event', 'uuid') 