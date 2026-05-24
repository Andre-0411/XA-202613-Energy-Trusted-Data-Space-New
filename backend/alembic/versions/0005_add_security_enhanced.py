"""add security enhanced tables

Revision ID: 0005_add_security_enhanced
Revises: 0004_add_blockchain_settlement
Create Date: 2024-01-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0005_add_security_enhanced'
down_revision: Union[str, None] = '0004_add_blockchain_settlement'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 DID 文档表
    op.create_table(
        'did_documents',
        sa.Column('id', sa.Integer(), primary_key=True, comment='DID 文档 ID'),
        sa.Column('did', sa.String(256), nullable=False, unique=True, comment='分布式标识符'),
        sa.Column('public_key', sa.Text(), nullable=False, comment='公钥'),
        sa.Column('authentication', postgresql.JSONB(), nullable=True, comment='认证方式'),
        sa.Column('service_endpoints', postgresql.JSONB(), nullable=True, comment='服务端点'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态 (active/deactivated)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='DID 文档表'
    )

    # 创建 VC 记录表
    op.create_table(
        'vc_records',
        sa.Column('id', sa.Integer(), primary_key=True, comment='VC 记录 ID'),
        sa.Column('vc_id', sa.String(256), nullable=False, unique=True, comment='可验证凭证 ID'),
        sa.Column('issuer_did', sa.String(256), sa.ForeignKey('did_documents.did'), nullable=False, comment='发行者 DID'),
        sa.Column('subject_did', sa.String(256), nullable=False, comment='主体 DID'),
        sa.Column('credential_type', sa.String(100), nullable=False, comment='凭证类型'),
        sa.Column('claims', postgresql.JSONB(), nullable=False, comment='声明内容'),
        sa.Column('issuance_date', sa.DateTime(), nullable=False, comment='发行日期'),
        sa.Column('expiration_date', sa.DateTime(), nullable=True, comment='过期日期'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态 (active/revoked/expired)'),
        sa.Column('proof', postgresql.JSONB(), nullable=True, comment='证明'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        comment='VC 记录表'
    )

    # 创建密钥存储表
    op.create_table(
        'key_stores',
        sa.Column('id', sa.Integer(), primary_key=True, comment='密钥 ID'),
        sa.Column('key_id', sa.String(64), nullable=False, unique=True, comment='密钥标识'),
        sa.Column('key_type', sa.String(20), nullable=False, comment='密钥类型 (RSA/EC/SM2)'),
        sa.Column('public_key', sa.Text(), nullable=False, comment='公钥'),
        sa.Column('encrypted_private_key', sa.Text(), nullable=False, comment='加密后的私钥'),
        sa.Column('algorithm', sa.String(50), nullable=False, comment='算法'),
        sa.Column('purpose', sa.String(50), nullable=False, comment='用途 (signing/encryption)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='是否激活'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        comment='密钥存储表'
    )

    # 创建安全策略表
    op.create_table(
        'security_policies',
        sa.Column('id', sa.Integer(), primary_key=True, comment='策略 ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='策略名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='策略描述'),
        sa.Column('policy_type', sa.String(50), nullable=False, comment='策略类型 (access_control/data_protection/network)'),
        sa.Column('rules', postgresql.JSONB(), nullable=False, comment='策略规则'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='优先级'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='安全策略表'
    )

    # 创建威胁事件表
    op.create_table(
        'threat_events',
        sa.Column('id', sa.Integer(), primary_key=True, comment='事件 ID'),
        sa.Column('event_type', sa.String(50), nullable=False, comment='事件类型 (intrusion/malware/ddos/brute_force)'),
        sa.Column('severity', sa.String(20), nullable=False, comment='严重程度 (low/medium/high/critical)'),
        sa.Column('source_ip', sa.String(50), nullable=True, comment='源 IP'),
        sa.Column('target_resource', sa.String(200), nullable=True, comment='目标资源'),
        sa.Column('description', sa.Text(), nullable=False, comment='事件描述'),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True, comment='原始数据'),
        sa.Column('status', sa.String(20), nullable=False, server_default='detected', comment='状态 (detected/investigating/resolved)'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='解决时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        comment='威胁事件表'
    )

    # 创建索引
    op.create_index('ix_did_documents_did', 'did_documents', ['did'])
    op.create_index('ix_did_documents_status', 'did_documents', ['status'])
    op.create_index('ix_vc_records_vc_id', 'vc_records', ['vc_id'])
    op.create_index('ix_vc_records_issuer_did', 'vc_records', ['issuer_did'])
    op.create_index('ix_vc_records_subject_did', 'vc_records', ['subject_did'])
    op.create_index('ix_vc_records_status', 'vc_records', ['status'])
    op.create_index('ix_key_stores_key_id', 'key_stores', ['key_id'])
    op.create_index('ix_security_policies_policy_type', 'security_policies', ['policy_type'])
    op.create_index('ix_security_policies_is_enabled', 'security_policies', ['is_enabled'])
    op.create_index('ix_threat_events_event_type', 'threat_events', ['event_type'])
    op.create_index('ix_threat_events_severity', 'threat_events', ['severity'])
    op.create_index('ix_threat_events_status', 'threat_events', ['status'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_threat_events_status', table_name='threat_events')
    op.drop_index('ix_threat_events_severity', table_name='threat_events')
    op.drop_index('ix_threat_events_event_type', table_name='threat_events')
    op.drop_index('ix_security_policies_is_enabled', table_name='security_policies')
    op.drop_index('ix_security_policies_policy_type', table_name='security_policies')
    op.drop_index('ix_key_stores_key_id', table_name='key_stores')
    op.drop_index('ix_vc_records_status', table_name='vc_records')
    op.drop_index('ix_vc_records_subject_did', table_name='vc_records')
    op.drop_index('ix_vc_records_issuer_did', table_name='vc_records')
    op.drop_index('ix_vc_records_vc_id', table_name='vc_records')
    op.drop_index('ix_did_documents_status', table_name='did_documents')
    op.drop_index('ix_did_documents_did', table_name='did_documents')

    # 删除表
    op.drop_table('threat_events')
    op.drop_table('security_policies')
    op.drop_table('key_stores')
    op.drop_table('vc_records')
    op.drop_table('did_documents')
