"""Create reminders table

Revision ID: 003_create_reminders
Revises: 002_create_recurrence_rules
Create Date: 2026-01-06 19:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_reminders'
down_revision: Union[str, None] = '002_create_recurrence_rules'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create reminders table"""
    op.create_table(
        'reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
        sa.Column('reminder_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.VARCHAR(length=20), nullable=True, server_default='pending'),
        sa.Column('delivery_method', sa.VARCHAR(length=50), nullable=True, server_default='webhook'),
        sa.Column('retry_count', sa.INTEGER(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_reminders_task_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'], unique=False)
    op.create_index('ix_reminders_task_id', 'reminders', ['task_id'], unique=False)
    op.create_index('ix_reminders_reminder_time', 'reminders', ['reminder_time'], unique=False)
    op.create_index('ix_reminders_status', 'reminders', ['status'], unique=False)


def downgrade() -> None:
    """Drop reminders table"""
    # Drop indexes
    op.drop_index('ix_reminders_status', table_name='reminders')
    op.drop_index('ix_reminders_reminder_time', table_name='reminders')
    op.drop_index('ix_reminders_task_id', table_name='reminders')
    op.drop_index('ix_reminders_user_id', table_name='reminders')

    # Drop table
    op.drop_table('reminders')
