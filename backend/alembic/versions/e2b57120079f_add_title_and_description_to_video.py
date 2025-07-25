"""add_title_and_description_to_video

Revision ID: e2b57120079f
Revises: 3fbbd68e6677
Create Date: 2025-05-08 10:19:07.023985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b57120079f'
down_revision: Union[str, None] = '3fbbd68e6677'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'username',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.add_column('video', sa.Column('title', sa.String(length=100), nullable=False))
    op.add_column('video', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('video', sa.Column('file_path', sa.String(), nullable=True))
    op.alter_column('video', 'video_url',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('video', 'video_url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('video', 'file_path')
    op.drop_column('video', 'description')
    op.drop_column('video', 'title')
    op.alter_column('user', 'username',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###
