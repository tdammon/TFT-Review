"""make_uuid_primary_keys

Revision ID: make_uuid_primary_keys
Revises: update_foreign_keys_to_uuid
Create Date: 2023-06-10 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'make_uuid_primary_keys'
down_revision: Union[str, None] = 'update_foreign_keys_to_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old integer primary keys and make UUIDs the new primary keys
    
    # First drop all foreign key constraints that use the old integer IDs
    op.drop_constraint('video_user_id_fkey', 'video', type_='foreignkey')
    op.drop_constraint('comment_user_id_fkey', 'comment', type_='foreignkey')
    op.drop_constraint('comment_video_id_fkey', 'comment', type_='foreignkey')
    op.drop_constraint('comment_parent_id_fkey', 'comment', type_='foreignkey')
    op.drop_constraint('comment_event_id_fkey', 'comment', type_='foreignkey')
    op.drop_constraint('event_user_id_fkey', 'event', type_='foreignkey')
    op.drop_constraint('event_video_id_fkey', 'event', type_='foreignkey')
    
    # Drop old primary key constraints and indexes
    op.drop_constraint('user_pkey', 'user', type_='primary')
    op.drop_constraint('video_pkey', 'video', type_='primary')
    op.drop_constraint('comment_pkey', 'comment', type_='primary')
    op.drop_constraint('event_pkey', 'event', type_='primary')
    
    op.drop_index('ix_user_id', table_name='user')
    op.drop_index('ix_video_id', table_name='video')
    op.drop_index('ix_comment_id', table_name='comment')
    op.drop_index('ix_event_id', table_name='event')
    
    # Make UUID columns the new primary keys
    op.create_primary_key('user_pkey', 'user', ['uuid'])
    op.create_primary_key('video_pkey', 'video', ['uuid'])
    op.create_primary_key('comment_pkey', 'comment', ['uuid'])
    op.create_primary_key('event_pkey', 'event', ['uuid'])
    
    # Drop old integer ID columns
    op.drop_column('user', 'id')
    op.drop_column('video', 'id')
    op.drop_column('comment', 'id')
    op.drop_column('event', 'id')
    
    # Drop old integer foreign key columns
    op.drop_column('video', 'user_id')
    op.drop_column('comment', 'user_id')
    op.drop_column('comment', 'video_id')
    op.drop_column('comment', 'parent_id')
    op.drop_column('comment', 'event_id')
    op.drop_column('event', 'user_id')
    op.drop_column('event', 'video_id')
    
    # Rename UUID columns to 'id'
    op.alter_column('user', 'uuid', new_column_name='id')
    op.alter_column('video', 'uuid', new_column_name='id')
    op.alter_column('comment', 'uuid', new_column_name='id')
    op.alter_column('event', 'uuid', new_column_name='id')
    
    # Rename UUID foreign key columns to standard names
    op.alter_column('video', 'user_uuid', new_column_name='user_id')
    op.alter_column('comment', 'user_uuid', new_column_name='user_id')
    op.alter_column('comment', 'video_uuid', new_column_name='video_id')
    op.alter_column('comment', 'parent_uuid', new_column_name='parent_id')
    op.alter_column('comment', 'event_uuid', new_column_name='event_id')
    op.alter_column('event', 'user_uuid', new_column_name='user_id')
    op.alter_column('event', 'video_uuid', new_column_name='video_id')
    
    # Create indexes for the new primary key columns
    op.create_index(op.f('ix_user_id'), 'user', ['id'], unique=True)
    op.create_index(op.f('ix_video_id'), 'video', ['id'], unique=True)
    op.create_index(op.f('ix_comment_id'), 'comment', ['id'], unique=True)
    op.create_index(op.f('ix_event_id'), 'event', ['id'], unique=True)


def downgrade() -> None:
    # This is a complex operation that would require recreating integer IDs and remapping all relationships
    # It's safer to restore from a backup if you need to downgrade
    op.execute("-- Cannot safely downgrade this migration")
    pass 