"""Add shared_with JSON columns to Reaction and Experiment tables

Revision ID: 3a4b5c6d7e8f
Revises: 2b3f8c1a9d2e
Create Date: 2026-05-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a4b5c6d7e8f'
down_revision: Union[str, None] = '2b3f8c1a9d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reactions', sa.Column('shared_with', sa.JSON(), nullable=True))
    op.add_column('experiments', sa.Column('shared_with', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('experiments', 'shared_with')
    op.drop_column('reactions', 'shared_with')
