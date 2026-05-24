"""添加配额管理和 GDPR 合规表

Batch 6 运营管理增强:
- quotas: 配额管理表
- quota_usage_logs: 配额使用记录表
- data_subject_requests: 数据主体请求表（GDPR/数安法）

Revision ID: 0009_add_quota_gdpr_tables
Revises: 0008_add_privacy_compute_ops_security_tables
Create Date: 2026-06-15 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision: str = "0009_add_quota_gdpr_tables"
down_revision: Union[str, None] = "0008_add_privacy_compute_ops_security_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 配额管理表 ----
    op.create_table(
        "quotas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("limit_value", sa.Float(), nullable=False, comment="配额上限"),
        sa.Column("used_value", sa.Float(), nullable=False, server_default="0", comment="已使用量"),
        sa.Column("unit", sa.String(20), nullable=False, server_default="", comment="计量单位"),
        sa.Column("period", sa.String(20), nullable=False, server_default="monthly", comment="配额周期"),
        sa.Column("alert_threshold", sa.Float(), nullable=False, server_default="80", comment="告警阈值百分比"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态"),
        sa.Column("metadata", JSONB, nullable=True, comment="扩展配置"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        comment="配额管理表",
    )

    op.create_index("idx_quota_org_id", "quotas", ["organization_id"])
    op.create_index("idx_quota_resource_type", "quotas", ["resource_type"])
    op.create_index("idx_quota_status", "quotas", ["status"])

    # ---- 配额使用记录表 ----
    op.create_table(
        "quota_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quota_id", UUID(as_uuid=True), sa.ForeignKey("quotas.id"), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False, comment="变更量"),
        sa.Column("before_value", sa.Float(), nullable=False, comment="变更前值"),
        sa.Column("after_value", sa.Float(), nullable=False, comment="变更后值"),
        sa.Column("reason", sa.Text(), nullable=True, comment="变更原因"),
        sa.Column("operator_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        comment="配额使用记录表",
    )

    op.create_index("idx_quota_log_quota_id", "quota_usage_logs", ["quota_id"])

    # ---- 数据主体请求表（GDPR / 数安法） ----
    op.create_table(
        "data_subject_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_type", sa.String(30), nullable=False, comment="请求类型"),
        sa.Column("subject_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, comment="数据主体用户ID"),
        sa.Column("subject_email", sa.String(200), nullable=True, comment="数据主体邮箱"),
        sa.Column("subject_name", sa.String(100), nullable=True, comment="数据主体姓名"),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True, comment="关联组织ID"),
        sa.Column("description", sa.Text(), nullable=True, comment="请求描述"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="状态"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="normal", comment="优先级"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, comment="处理人ID"),
        sa.Column("response_data", JSONB, nullable=True, comment="响应数据"),
        sa.Column("rejection_reason", sa.Text(), nullable=True, comment="拒绝原因"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True, comment="截止日期"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        comment="数据主体请求表",
    )

    op.create_index("idx_dsr_type", "data_subject_requests", ["request_type"])
    op.create_index("idx_dsr_status", "data_subject_requests", ["status"])
    op.create_index("idx_dsr_subject_user", "data_subject_requests", ["subject_user_id"])
    op.create_index("idx_dsr_org_id", "data_subject_requests", ["organization_id"])


def downgrade() -> None:
    op.drop_index("idx_dsr_org_id", table_name="data_subject_requests")
    op.drop_index("idx_dsr_subject_user", table_name="data_subject_requests")
    op.drop_index("idx_dsr_status", table_name="data_subject_requests")
    op.drop_index("idx_dsr_type", table_name="data_subject_requests")
    op.drop_table("data_subject_requests")

    op.drop_index("idx_quota_log_quota_id", table_name="quota_usage_logs")
    op.drop_table("quota_usage_logs")

    op.drop_index("idx_quota_status", table_name="quotas")
    op.drop_index("idx_quota_resource_type", table_name="quotas")
    op.drop_index("idx_quota_org_id", table_name="quotas")
    op.drop_table("quotas")
