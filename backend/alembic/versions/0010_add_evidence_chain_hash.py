"""增强存证记录表：添加链式哈希和操作者字段

增强区块链存证功能:
- evidence_records 表添加 prev_hash, chain_hash, operator_did, operator_signature 字段
- 添加 chain_hash 索引

Revision ID: 0010_add_evidence_chain_hash
Revises: 0009_add_quota_gdpr_tables
Create Date: 2026-06-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "0010_add_evidence_chain_hash"
down_revision: Union[str, None] = "0009_add_quota_gdpr_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加链式哈希字段
    op.add_column("evidence_records", sa.Column("prev_hash", sa.String(128), nullable=True))
    op.add_column("evidence_records", sa.Column("chain_hash", sa.String(128), nullable=True))

    # 添加操作者字段
    op.add_column("evidence_records", sa.Column("operator_did", sa.String(128), nullable=True))
    op.add_column("evidence_records", sa.Column("operator_signature", sa.Text(), nullable=True))

    # 添加索引
    op.create_index("idx_evidence_chain_hash", "evidence_records", ["chain_hash"])


def downgrade() -> None:
    op.drop_index("idx_evidence_chain_hash", table_name="evidence_records")
    op.drop_column("evidence_records", "operator_signature")
    op.drop_column("evidence_records", "operator_did")
    op.drop_column("evidence_records", "chain_hash")
    op.drop_column("evidence_records", "prev_hash")
