"""Create recurrence_rules table

Revision ID: 002_create_recurrence_rules
Revises: 001_add_advanced_features
Create Date: 2026-01-06 19:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_create_recurrence_rules'
down_revision: Union[str, None] = '001_add_advanced_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recurrence_rules table"""
    op.create_table(
        'recurrence_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
        sa.Column('pattern', sa.VARCHAR(length=50), nullable=False),
        sa.Column('interval', sa.INTEGER(), nullable=True, server_default='1'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_recurrence_rules_task_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_recurrence_rules_user_id', 'recurrence_rules', ['user_id'], unique=False)
    op.create_index('ix_recurrence_rules_task_id', 'recurrence_rules', ['task_id'], unique=False)
    op.create_index('ix_recurrence_rules_pattern', 'recurrence_rules', ['pattern'], unique=False)

    # Add foreign key constraint from tasks to recurrence_rules
    op.create_foreign_key(
        'fk_tasks_recurrence_id',
        'tasks',
        'recurrence_rules',
        ['recurrence_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop recurrence_rules table"""
    # Drop foreign key from tasks
    op.drop_constraint('fk_tasks_recurrence_id', 'tasks', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_recurrence_rules_pattern', table_name='recurrence_rules')
    op.drop_index('ix_recurrence_rules_task_id', table_name='recurrence_rules')
    op.drop_index('ix_recurrence_rules_user_id', table_name='recurrence_rules')

    # Drop table
    op.drop_table('recurrence_rules')
