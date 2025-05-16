"""merge_multiple_heads

Revision ID: 717c9c1c6795
Revises: adc297d50e95, make_uuid_primary_keys
Create Date: 2025-05-15 11:24:44.680273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '717c9c1c6795'
down_revision: Union[str, None] = ('adc297d50e95', 'make_uuid_primary_keys')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
