"""update_foreign_keys_to_uuid

Revision ID: update_foreign_keys_to_uuid
Revises: add_uuid_columns
Create Date: 2023-06-10 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'update_foreign_keys_to_uuid'
down_revision: Union[str, None] = 'add_uuid_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add UUID foreign key columns
    
    # Video table - user_id to user_uuid
    op.add_column('video', sa.Column('user_uuid', UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE video v
        SET user_uuid = u.uuid
        FROM "user" u
        WHERE v.user_id = u.id
    """)
    
    # Comment table - user_id to user_uuid, video_id to video_uuid, parent_id to parent_uuid
    op.add_column('comment', sa.Column('user_uuid', UUID(as_uuid=True), nullable=True))
    op.add_column('comment', sa.Column('video_uuid', UUID(as_uuid=True), nullable=True))
    op.add_column('comment', sa.Column('parent_uuid', UUID(as_uuid=True), nullable=True))
    op.add_column('comment', sa.Column('event_uuid', UUID(as_uuid=True), nullable=True))
    
    op.execute("""
        UPDATE comment c
        SET user_uuid = u.uuid
        FROM "user" u
        WHERE c.user_id = u.id
    """)
    
    op.execute("""
        UPDATE comment c
        SET video_uuid = v.uuid
        FROM video v
        WHERE c.video_id = v.id
    """)
    
    op.execute("""
        UPDATE comment c
        SET parent_uuid = p.uuid
        FROM comment p
        WHERE c.parent_id = p.id
    """)
    
    op.execute("""
        UPDATE comment c
        SET event_uuid = e.uuid
        FROM event e
        WHERE c.event_id = e.id
    """)
    
    # Event table - user_id to user_uuid, video_id to video_uuid
    op.add_column('event', sa.Column('user_uuid', UUID(as_uuid=True), nullable=True))
    op.add_column('event', sa.Column('video_uuid', UUID(as_uuid=True), nullable=True))
    
    op.execute("""
        UPDATE event e
        SET user_uuid = u.uuid
        FROM "user" u
        WHERE e.user_id = u.id
    """)
    
    op.execute("""
        UPDATE event e
        SET video_uuid = v.uuid
        FROM video v
        WHERE e.video_id = v.id
    """)
    
    # Make the new foreign key columns non-nullable where appropriate
    op.alter_column('video', 'user_uuid', nullable=False)
    op.alter_column('comment', 'user_uuid', nullable=False)
    op.alter_column('comment', 'video_uuid', nullable=False)
    op.alter_column('event', 'user_uuid', nullable=False)
    op.alter_column('event', 'video_uuid', nullable=False)
    
    # Add foreign key constraints
    op.create_foreign_key('fk_video_user_uuid', 'video', 'user', ['user_uuid'], ['uuid'])
    op.create_foreign_key('fk_comment_user_uuid', 'comment', 'user', ['user_uuid'], ['uuid'])
    op.create_foreign_key('fk_comment_video_uuid', 'comment', 'video', ['video_uuid'], ['uuid'])
    op.create_foreign_key('fk_comment_parent_uuid', 'comment', 'comment', ['parent_uuid'], ['uuid'])
    op.create_foreign_key('fk_comment_event_uuid', 'comment', 'event', ['event_uuid'], ['uuid'])
    op.create_foreign_key('fk_event_user_uuid', 'event', 'user', ['user_uuid'], ['uuid'])
    op.create_foreign_key('fk_event_video_uuid', 'event', 'video', ['video_uuid'], ['uuid'])


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('fk_video_user_uuid', 'video', type_='foreignkey')
    op.drop_constraint('fk_comment_user_uuid', 'comment', type_='foreignkey')
    op.drop_constraint('fk_comment_video_uuid', 'comment', type_='foreignkey')
    op.drop_constraint('fk_comment_parent_uuid', 'comment', type_='foreignkey')
    op.drop_constraint('fk_comment_event_uuid', 'comment', type_='foreignkey')
    op.drop_constraint('fk_event_user_uuid', 'event', type_='foreignkey')
    op.drop_constraint('fk_event_video_uuid', 'event', type_='foreignkey')
    
    # Drop UUID foreign key columns
    op.drop_column('video', 'user_uuid')
    op.drop_column('comment', 'user_uuid')
    op.drop_column('comment', 'video_uuid')
    op.drop_column('comment', 'parent_uuid')
    op.drop_column('comment', 'event_uuid')
    op.drop_column('event', 'user_uuid')
    op.drop_column('event', 'video_uuid') 