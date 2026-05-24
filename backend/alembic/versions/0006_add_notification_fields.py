"""add notification priority/category/target_users/sender fields

Revision ID: 0006_add_notification_fields
Revises: 0005_add_security_enhanced
Create Date: 2026-05-21 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0006_add_notification_fields'
down_revision: Union[str, None] = '0005_add_security_enhanced'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add priority column
    op.add_column('portal_notifications', sa.Column(
        'priority', sa.String(20), nullable=False, server_default='normal',
        comment='优先级: low/normal/high/urgent',
    ))
    op.create_index('idx_portal_notif_priority', 'portal_notifications', ['priority'])

    # Add category column
    op.add_column('portal_notifications', sa.Column(
        'category', sa.String(50), nullable=False, server_default='system',
        comment='分类: system/task/security/billing',
    ))
    op.create_index('idx_portal_notif_category', 'portal_notifications', ['category'])

    # Add target_users column (JSONB array of user IDs, null = all users)
    op.add_column('portal_notifications', sa.Column(
        'target_users', postgresql.JSONB(), nullable=True,
        comment='目标用户ID列表，null表示全员',
    ))

    # Add sender column
    op.add_column('portal_notifications', sa.Column(
        'sender', sa.String(100), nullable=False, server_default='system',
        comment='发送者',
    ))


def downgrade() -> None:
    op.drop_column('portal_notifications', 'sender')
    op.drop_column('portal_notifications', 'target_users')
    op.drop_index('idx_portal_notif_category', 'portal_notifications')
    op.drop_column('portal_notifications', 'category')
    op.drop_index('idx_portal_notif_priority', 'portal_notifications')
    op.drop_column('portal_notifications', 'priority')
