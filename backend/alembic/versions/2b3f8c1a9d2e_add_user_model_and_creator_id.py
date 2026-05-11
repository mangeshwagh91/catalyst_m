"""Add User model and creator_id fields for multi-user support

Revision ID: 2b3f8c1a9d2e
Revises: 88b53816f07e
Create Date: 2026-05-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b3f8c1a9d2e'
down_revision: Union[str, None] = '88b53816f07e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='false'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_is_active', 'users', ['is_active'], unique=False)
    
    # Add creator_id to reactions table
    op.add_column('reactions', sa.Column('creator_id', sa.String(length=64), nullable=True))
    op.create_foreign_key('fk_reactions_creator_id', 'reactions', 'users', ['creator_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_reactions_creator_id', 'reactions', ['creator_id'], unique=False)
    
    # Add creator_id to experiments table
    op.add_column('experiments', sa.Column('creator_id', sa.String(length=64), nullable=True))
    op.create_foreign_key('fk_experiments_creator_id', 'experiments', 'users', ['creator_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_experiments_creator_id', 'experiments', ['creator_id'], unique=False)


def downgrade() -> None:
    # Drop foreign keys and columns
    op.drop_index('ix_experiments_creator_id', table_name='experiments')
    op.drop_constraint('fk_experiments_creator_id', 'experiments', type_='foreignkey')
    op.drop_column('experiments', 'creator_id')
    
    op.drop_index('ix_reactions_creator_id', table_name='reactions')
    op.drop_constraint('fk_reactions_creator_id', 'reactions', type_='foreignkey')
    op.drop_column('reactions', 'creator_id')
    
    # Drop users table
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
