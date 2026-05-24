"""add data quality tables

Revision ID: 0003_add_data_quality
Revises: 0002_add_mfa_fields
Create Date: 2024-01-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0003_add_data_quality'
down_revision: Union[str, None] = '0002_add_mfa_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建数据质量报告表
    op.create_table(
        'data_quality_reports',
        sa.Column('id', sa.Integer(), primary_key=True, comment='报告 ID'),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('datasets.id'), nullable=False, comment='数据集 ID'),
        sa.Column('report_time', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='报告时间'),
        sa.Column('completeness_score', sa.Float(), nullable=False, server_default='0', comment='完整性评分'),
        sa.Column('accuracy_score', sa.Float(), nullable=False, server_default='0', comment='准确性评分'),
        sa.Column('consistency_score', sa.Float(), nullable=False, server_default='0', comment='一致性评分'),
        sa.Column('timeliness_score', sa.Float(), nullable=False, server_default='0', comment='时效性评分'),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0', comment='综合评分'),
        sa.Column('issues', postgresql.JSONB(), nullable=True, comment='质量问题列表'),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True, comment='改进建议'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='数据质量报告表'
    )

    # 创建数据反馈表
    op.create_table(
        'data_feedbacks',
        sa.Column('id', sa.Integer(), primary_key=True, comment='反馈 ID'),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('datasets.id'), nullable=False, comment='数据集 ID'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, comment='用户 ID'),
        sa.Column('feedback_type', sa.String(50), nullable=False, comment='反馈类型 (quality/usage/suggestion)'),
        sa.Column('content', sa.Text(), nullable=False, comment='反馈内容'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='处理状态 (pending/processing/resolved)'),
        sa.Column('admin_reply', sa.Text(), nullable=True, comment='管理员回复'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='数据反馈表'
    )

    # 创建索引
    op.create_index('ix_data_quality_reports_dataset_id', 'data_quality_reports', ['dataset_id'])
    op.create_index('ix_data_quality_reports_report_time', 'data_quality_reports', ['report_time'])
    op.create_index('ix_data_feedbacks_dataset_id', 'data_feedbacks', ['dataset_id'])
    op.create_index('ix_data_feedbacks_user_id', 'data_feedbacks', ['user_id'])
    op.create_index('ix_data_feedbacks_status', 'data_feedbacks', ['status'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_data_feedbacks_status', table_name='data_feedbacks')
    op.drop_index('ix_data_feedbacks_user_id', table_name='data_feedbacks')
    op.drop_index('ix_data_feedbacks_dataset_id', table_name='data_feedbacks')
    op.drop_index('ix_data_quality_reports_report_time', table_name='data_quality_reports')
    op.drop_index('ix_data_quality_reports_dataset_id', table_name='data_quality_reports')

    # 删除表
    op.drop_table('data_feedbacks')
    op.drop_table('data_quality_reports')
