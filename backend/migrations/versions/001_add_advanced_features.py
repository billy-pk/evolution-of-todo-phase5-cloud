"""Add advanced features to tasks table

Revision ID: 001_add_advanced_features
Revises:
Create Date: 2026-01-06 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_advanced_features'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add advanced features columns to tasks table"""
    # Add new columns to tasks table
    op.add_column('tasks', sa.Column('priority', sa.VARCHAR(length=20), nullable=True, server_default='normal'))
    op.add_column('tasks', sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('tasks', sa.Column('due_date', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column('recurrence_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Create indexes for performance
    op.create_index('ix_tasks_priority', 'tasks', ['priority'], unique=False)
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'], unique=False)
    op.create_index('ix_tasks_tags', 'tasks', ['tags'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    """Remove advanced features columns from tasks table"""
    # Drop indexes
    op.drop_index('ix_tasks_tags', table_name='tasks')
    op.drop_index('ix_tasks_due_date', table_name='tasks')
    op.drop_index('ix_tasks_priority', table_name='tasks')

    # Drop columns
    op.drop_column('tasks', 'recurrence_id')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'priority')
