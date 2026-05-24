"""add mfa fields to user table

Revision ID: 0002_add_mfa_fields
Revises: 0001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_mfa_fields'
down_revision: Union[str, None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 MFA 相关字段
    op.add_column('users', sa.Column('mfa_secret', sa.String(32), nullable=True, comment='MFA 密钥'))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false', comment='是否启用 MFA'))
    op.add_column('users', sa.Column('login_fail_count', sa.Integer(), nullable=False, server_default='0', comment='登录失败次数'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True, comment='账户锁定截止时间'))

    # 创建索引
    op.create_index('ix_users_mfa_enabled', 'users', ['mfa_enabled'])
    op.create_index('ix_users_locked_until', 'users', ['locked_until'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_users_locked_until', table_name='users')
    op.drop_index('ix_users_mfa_enabled', table_name='users')

    # 删除字段
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'login_fail_count')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
