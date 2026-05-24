"""add operations enhanced tables

Revision ID: 0006_add_ops_enhanced
Revises: 0006_add_notification_fields
Create Date: 2024-01-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0006_add_ops_enhanced'
down_revision: Union[str, None] = '0006_add_notification_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建部门表（支持层级结构）
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), primary_key=True, comment='部门 ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='部门名称'),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, comment='所属组织 ID'),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True, comment='上级部门 ID'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1', comment='层级'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='排序'),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, comment='部门负责人 ID'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态 (active/inactive)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='部门表'
    )

    # 创建计费记录表
    op.create_table(
        'billing_records',
        sa.Column('id', sa.Integer(), primary_key=True, comment='计费 ID'),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, comment='组织 ID'),
        sa.Column('billing_type', sa.String(50), nullable=False, comment='计费类型 (data_usage/compute/storage/api_call)'),
        sa.Column('resource_id', sa.String(100), nullable=True, comment='资源 ID'),
        sa.Column('quantity', sa.Float(), nullable=False, comment='用量'),
        sa.Column('unit_price', sa.Float(), nullable=False, comment='单价'),
        sa.Column('amount', sa.Float(), nullable=False, comment='金额'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='CNY', comment='货币类型'),
        sa.Column('billing_period', sa.String(20), nullable=False, comment='计费周期 (2024-01)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='状态 (pending/paid/overdue)'),
        sa.Column('paid_at', sa.DateTime(), nullable=True, comment='支付时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        comment='计费记录表'
    )

    # 创建合规报告表
    op.create_table(
        'compliance_reports',
        sa.Column('id', sa.Integer(), primary_key=True, comment='报告 ID'),
        sa.Column('title', sa.String(200), nullable=False, comment='报告标题'),
        sa.Column('report_type', sa.String(50), nullable=False, comment='报告类型 (gdpr/data_security/energy_regulation)'),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, comment='组织 ID'),
        sa.Column('report_period', sa.String(20), nullable=False, comment='报告周期'),
        sa.Column('findings', postgresql.JSONB(), nullable=True, comment='发现的问题'),
        sa.Column('score', sa.Float(), nullable=True, comment='合规评分'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='状态 (draft/submitted/approved/rejected)'),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, comment='审批人 ID'),
        sa.Column('approved_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='合规报告表'
    )

    # 创建告警规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), primary_key=True, comment='规则 ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='规则描述'),
        sa.Column('metric', sa.String(100), nullable=False, comment='监控指标'),
        sa.Column('condition', postgresql.JSONB(), nullable=False, comment='触发条件'),
        sa.Column('threshold', sa.Float(), nullable=False, comment='阈值'),
        sa.Column('duration', sa.Integer(), nullable=False, comment='持续时间(秒)'),
        sa.Column('severity', sa.String(20), nullable=False, comment='严重程度 (low/medium/high/critical)'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True, comment='通知渠道'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='告警规则表'
    )

    # 创建索引
    op.create_index('ix_departments_org_id', 'departments', ['org_id'])
    op.create_index('ix_departments_parent_id', 'departments', ['parent_id'])
    op.create_index('ix_billing_records_org_id', 'billing_records', ['org_id'])
    op.create_index('ix_billing_records_billing_type', 'billing_records', ['billing_type'])
    op.create_index('ix_billing_records_status', 'billing_records', ['status'])
    op.create_index('ix_compliance_reports_org_id', 'compliance_reports', ['org_id'])
    op.create_index('ix_compliance_reports_status', 'compliance_reports', ['status'])
    op.create_index('ix_alert_rules_metric', 'alert_rules', ['metric'])
    op.create_index('ix_alert_rules_is_enabled', 'alert_rules', ['is_enabled'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_alert_rules_is_enabled', table_name='alert_rules')
    op.drop_index('ix_alert_rules_metric', table_name='alert_rules')
    op.drop_index('ix_compliance_reports_status', table_name='compliance_reports')
    op.drop_index('ix_compliance_reports_org_id', table_name='compliance_reports')
    op.drop_index('ix_billing_records_status', table_name='billing_records')
    op.drop_index('ix_billing_records_billing_type', table_name='billing_records')
    op.drop_index('ix_billing_records_org_id', table_name='billing_records')
    op.drop_index('ix_departments_parent_id', table_name='departments')
    op.drop_index('ix_departments_org_id', table_name='departments')

    # 删除表
    op.drop_table('alert_rules')
    op.drop_table('compliance_reports')
    op.drop_table('billing_records')
    op.drop_table('departments')
