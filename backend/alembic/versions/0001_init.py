"""初始迁移 - 完整表定义

Revision ID: 0001_init
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET


# revision identifiers
revision: str = '0001_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建所有表"""

    # organizations
    op.create_table('organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('level', sa.SmallInteger, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('did', sa.String(128), nullable=True),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_org_parent_id', 'organizations', ['parent_id'])
    op.create_index('idx_org_code', 'organizations', ['code'])
    op.create_index('idx_org_status', 'organizations', ['status'])

    # departments
    op.create_table('departments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_dept_org_id', 'departments', ['organization_id'])
    op.create_index('idx_dept_parent_id', 'departments', ['parent_id'])

    # users
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('email', sa.String(200), unique=True, nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('did', sa.String(128), unique=True, nullable=True),
        sa.Column('sm2_public_key', sa.Text, nullable=True),
        sa.Column('mfa_secret', sa.String(64), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('role', sa.String(30), nullable=False, server_default='user'),
        sa.Column('department_id', UUID(as_uuid=True), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_fail_count', sa.SmallInteger, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_user_username', 'users', ['username'])
    op.create_index('idx_user_did', 'users', ['did'])
    op.create_index('idx_user_org_id', 'users', ['organization_id'])
    op.create_index('idx_user_dept_id', 'users', ['department_id'])
    op.create_index('idx_user_status', 'users', ['status'])

    # data_sources
    op.create_table('data_sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('protocol_type', sa.String(20), nullable=False),
        sa.Column('connection_config', JSONB, nullable=False),
        sa.Column('device_did', sa.String(128), nullable=True),
        sa.Column('mqtt_topic', sa.String(256), nullable=True),
        sa.Column('collection_interval_ms', sa.Integer, server_default='5000'),
        sa.Column('is_critical', sa.Boolean, server_default='false'),
        sa.Column('edge_preprocess', JSONB, server_default='{}'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_source_protocol', 'data_sources', ['protocol_type'])
    op.create_index('idx_source_org_id', 'data_sources', ['organization_id'])
    op.create_index('idx_source_device_did', 'data_sources', ['device_did'])
    op.create_index('idx_source_status', 'data_sources', ['status'])

    # data_assets
    op.create_table('data_assets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('source_id', UUID(as_uuid=True), sa.ForeignKey('data_sources.id'), nullable=True),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('classification_level', sa.SmallInteger, nullable=False, server_default='4'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('schema_def', JSONB, nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('storage_format', sa.String(20), server_default='parquet'),
        sa.Column('size_bytes', sa.BigInteger, server_default='0'),
        sa.Column('record_count', sa.BigInteger, server_default='0'),
        sa.Column('nft_token_id', sa.String(128), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_asset_category', 'data_assets', ['category'])
    op.create_index('idx_asset_level', 'data_assets', ['classification_level'])
    op.create_index('idx_asset_status', 'data_assets', ['status'])
    op.create_index('idx_asset_owner_id', 'data_assets', ['owner_id'])
    op.create_index('idx_asset_org_id', 'data_assets', ['organization_id'])
    op.create_index('idx_asset_nft_token', 'data_assets', ['nft_token_id'])

    # metadata
    op.create_table('metadata',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', UUID(as_uuid=True), sa.ForeignKey('data_assets.id'), nullable=False, unique=True),
        sa.Column('standard', sa.String(50), server_default='GB/T 36073-2018'),
        sa.Column('content', JSONB, nullable=False),
        sa.Column('lineage_graph', JSONB, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('previous_version_id', UUID(as_uuid=True), sa.ForeignKey('metadata.id'), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # tags
    op.create_table('tags',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('dimension', sa.String(20), nullable=False),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('tags.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('name', 'dimension', name='uq_tag_name_dimension'),
    )

    # asset_tags
    op.create_table('asset_tags',
        sa.Column('asset_id', UUID(as_uuid=True), sa.ForeignKey('data_assets.id'), nullable=False, primary_key=True),
        sa.Column('tag_id', UUID(as_uuid=True), sa.ForeignKey('tags.id'), nullable=False, primary_key=True),
    )

    # dag_definitions
    op.create_table('dag_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('nodes', JSONB, nullable=False),
        sa.Column('edges', JSONB, nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # compute_tasks
    op.create_table('compute_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('task_type', sa.String(20), nullable=False),
        sa.Column('scenario', sa.String(30), nullable=True),
        sa.Column('dag_id', UUID(as_uuid=True), sa.ForeignKey('dag_definitions.id'), nullable=True),
        sa.Column('config', JSONB, nullable=False),
        sa.Column('input_asset_ids', ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.SmallInteger, server_default='0'),
        sa.Column('result_ref', sa.String(500), nullable=True),
        sa.Column('result_hash', sa.String(128), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_task_type', 'compute_tasks', ['task_type'])
    op.create_index('idx_task_status', 'compute_tasks', ['status'])
    op.create_index('idx_task_created_by', 'compute_tasks', ['created_by'])

    # task_signatures
    op.create_table('task_signatures',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('compute_tasks.id'), nullable=False),
        sa.Column('signer_did', sa.String(128), nullable=False),
        sa.Column('signature', sa.Text, nullable=False),
        sa.Column('signed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('task_id', 'signer_did', name='uq_task_signer'),
    )

    # nft_assets
    op.create_table('nft_assets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('token_id', sa.String(128), nullable=False, unique=True),
        sa.Column('asset_id', UUID(as_uuid=True), sa.ForeignKey('data_assets.id'), nullable=False),
        sa.Column('owner_did', sa.String(128), nullable=False),
        sa.Column('creator_did', sa.String(128), nullable=False),
        sa.Column('token_uri', sa.String(500), nullable=True),
        sa.Column('evidence_hash', sa.String(128), nullable=False),
        sa.Column('certificate_url', sa.String(500), nullable=True),
        sa.Column('tx_hash', sa.String(128), nullable=False),
        sa.Column('block_number', sa.BigInteger, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # evidence_records
    op.create_table('evidence_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('node_type', sa.String(30), nullable=False),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(30), nullable=False),
        sa.Column('data_hash', sa.String(128), nullable=False),
        sa.Column('schema_version', sa.String(20), server_default='v1.0'),
        sa.Column('evidence_data', JSONB, nullable=False),
        sa.Column('tx_hash', sa.String(128), nullable=False),
        sa.Column('block_number', sa.BigInteger, nullable=True),
        sa.Column('timestamp', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_evidence_node_type', 'evidence_records', ['node_type'])
    op.create_index('idx_evidence_resource', 'evidence_records', ['resource_id', 'resource_type'])
    op.create_index('idx_evidence_tx_hash', 'evidence_records', ['tx_hash'])

    # blockchain_transactions
    op.create_table('blockchain_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tx_hash', sa.String(128), nullable=False, unique=True),
        sa.Column('contract_address', sa.String(128), nullable=False),
        sa.Column('method', sa.String(100), nullable=False),
        sa.Column('params', JSONB, nullable=True),
        sa.Column('from_address', sa.String(128), nullable=True),
        sa.Column('block_number', sa.BigInteger, nullable=True),
        sa.Column('gas_used', sa.BigInteger, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # service_catalog
    op.create_table('service_catalog',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('service_catalog.id'), nullable=True),
        sa.Column('level', sa.SmallInteger, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('pricing_model', sa.String(20), nullable=False),
        sa.Column('pricing_config', JSONB, nullable=False),
        sa.Column('quota_limit', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # subscriptions
    op.create_table('subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('service_id', UUID(as_uuid=True), sa.ForeignKey('service_catalog.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('quota_used', sa.Integer, server_default='0'),
        sa.Column('approval_status', sa.String(20), server_default='pending'),
        sa.Column('approved_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # billing_records
    op.create_table('billing_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', UUID(as_uuid=True), sa.ForeignKey('subscriptions.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('billing_period', sa.String(20), nullable=False),
        sa.Column('usage_detail', JSONB, nullable=True),
        sa.Column('payment_status', sa.String(20), server_default='pending'),
        sa.Column('tx_hash', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # access_logs
    op.create_table('access_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('asset_id', UUID(as_uuid=True), sa.ForeignKey('data_assets.id'), nullable=True),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('compute_task_id', UUID(as_uuid=True), sa.ForeignKey('compute_tasks.id'), nullable=True),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('details', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_access_user_id', 'access_logs', ['user_id'])
    op.create_index('idx_access_asset_id', 'access_logs', ['asset_id'])
    op.create_index('idx_access_created_at', 'access_logs', ['created_at'])

    # audit_logs
    op.create_table('audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(30), nullable=False),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=False),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_audit_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'])

    # security_policies
    op.create_table('security_policies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('policy_type', sa.String(20), nullable=False),
        sa.Column('rules', JSONB, nullable=False),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # policy_assignments
    op.create_table('policy_assignments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_id', UUID(as_uuid=True), sa.ForeignKey('security_policies.id'), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # did_documents
    op.create_table('did_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('did', sa.String(128), nullable=False, unique=True),
        sa.Column('method', sa.String(30), nullable=False, server_default='did:fisco'),
        sa.Column('document', JSONB, nullable=False),
        sa.Column('controller', sa.String(128), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # vc_records
    op.create_table('vc_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('vc_id', sa.String(128), nullable=False, unique=True),
        sa.Column('issuer_did', sa.String(128), nullable=False),
        sa.Column('subject_did', sa.String(128), nullable=False),
        sa.Column('vc_type', sa.String(100), nullable=False),
        sa.Column('claims', JSONB, nullable=False),
        sa.Column('signature', sa.Text, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )

    # key_store
    op.create_table('key_store',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', sa.String(64), nullable=False, unique=True),
        sa.Column('algorithm', sa.String(20), nullable=False),
        sa.Column('encrypted_key', sa.Text, nullable=False),
        sa.Column('hierarchy_level', sa.String(10), nullable=False),
        sa.Column('parent_key_id', sa.String(64), nullable=True),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # key_usage_logs
    op.create_table('key_usage_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', sa.String(64), nullable=False),
        sa.Column('operation', sa.String(30), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_key_usage_key_id', 'key_usage_logs', ['key_id'])

    # threat_events
    op.create_table('threat_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('threat_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('indicators', JSONB, nullable=True),
        sa.Column('affected_resources', ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column('status', sa.String(20), server_default='detected'),
        sa.Column('assigned_to', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )

    # threat_actions
    op.create_table('threat_actions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('threat_id', UUID(as_uuid=True), sa.ForeignKey('threat_events.id'), nullable=False),
        sa.Column('action_type', sa.String(30), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('performed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # compliance_reports
    op.create_table('compliance_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('report_type', sa.String(20), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('findings', JSONB, nullable=False),
        sa.Column('gdpr_checklist', JSONB, nullable=True),
        sa.Column('data_security_checklist', JSONB, nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # data_quality_reports
    op.create_table('data_quality_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', UUID(as_uuid=True), sa.ForeignKey('data_assets.id'), nullable=False),
        sa.Column('completeness', sa.Numeric(5, 4), nullable=True),
        sa.Column('timeliness_ms', sa.Integer, nullable=True),
        sa.Column('accuracy', sa.Numeric(5, 4), nullable=True),
        sa.Column('consistency', sa.Numeric(5, 4), nullable=True),
        sa.Column('overall_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_quality_asset_id', 'data_quality_reports', ['asset_id'])


def downgrade() -> None:
    """降级迁移 - 按依赖顺序删除所有表"""
    op.drop_table('data_quality_reports')
    op.drop_table('compliance_reports')
    op.drop_table('threat_actions')
    op.drop_table('threat_events')
    op.drop_table('key_usage_logs')
    op.drop_table('key_store')
    op.drop_table('vc_records')
    op.drop_table('did_documents')
    op.drop_table('policy_assignments')
    op.drop_table('security_policies')
    op.drop_table('audit_logs')
    op.drop_table('access_logs')
    op.drop_table('billing_records')
    op.drop_table('subscriptions')
    op.drop_table('service_catalog')
    op.drop_table('blockchain_transactions')
    op.drop_table('evidence_records')
    op.drop_table('nft_assets')
    op.drop_table('task_signatures')
    op.drop_table('compute_tasks')
    op.drop_table('dag_definitions')
    op.drop_table('asset_tags')
    op.drop_table('tags')
    op.drop_table('metadata')
    op.drop_table('data_assets')
    op.drop_table('data_sources')
    op.drop_table('users')
    op.drop_table('departments')
    op.drop_table('organizations')
