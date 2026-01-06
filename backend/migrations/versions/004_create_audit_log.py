"""Create audit_log table

Revision ID: 004_create_audit_log
Revises: 003_create_reminders
Create Date: 2026-01-06 19:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_create_audit_log'
down_revision: Union[str, None] = '003_create_reminders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_log table"""
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'], unique=False)
    op.create_index('ix_audit_log_task_id', 'audit_log', ['task_id'], unique=False)
    op.create_index('ix_audit_log_event_type', 'audit_log', ['event_type'], unique=False)
    op.create_index('ix_audit_log_timestamp', 'audit_log', [sa.text('timestamp DESC')], unique=False)


def downgrade() -> None:
    """Drop audit_log table"""
    # Drop indexes
    op.drop_index('ix_audit_log_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_event_type', table_name='audit_log')
    op.drop_index('ix_audit_log_task_id', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')

    # Drop table
    op.drop_table('audit_log')
