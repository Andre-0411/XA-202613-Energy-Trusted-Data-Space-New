"""添加隐私计算、运营、安全服务持久化表

Batch 2 迁移: 14个内存字典 -> PostgreSQL
- 核心计算: fate_jobs, mpc_sessions, tee_instances, he_keys, he_ciphertexts, fl_models
- 运营服务: monitor_alerts, portal_*, sla_*, cluster_nodes, task_dispatches, data_versions, version_tags, current_versions
- 安全服务: verifiable_credentials, vc_revocation_list, zkp_proofs, knowledge_bases, knowledge_documents, agent_configs
- 沙箱增强: sandbox_sessions, sandbox_resource_usages, sandbox_violations

Revision ID: 0008_add_privacy_compute_ops_security_tables
Revises: 0007_add_mfa_sso_mqtt_tables
Create Date: 2026-05-21 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision: str = '0008_add_privacy_compute_ops_security_tables'
down_revision: Union[str, None] = '0007_add_mfa_sso_mqtt_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建所有 Batch 2 表"""

    # ==================== 核心计算服务 ====================

    # fate_jobs
    op.create_table('fate_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', sa.String(128), nullable=False, unique=True),
        sa.Column('mode', sa.String(50), nullable=False),
        sa.Column('algorithm', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('config', JSONB, nullable=True),
        sa.Column('metrics', JSONB, nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('progress', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_fate_job_status', 'fate_jobs', ['status'])
    op.create_index('idx_fate_job_mode', 'fate_jobs', ['mode'])
    op.create_index('idx_fate_job_algorithm', 'fate_jobs', ['algorithm'])
    op.create_index('idx_fate_job_created_at', 'fate_jobs', ['created_at'])

    # mpc_sessions
    op.create_table('mpc_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(128), nullable=False, unique=True),
        sa.Column('task_id', sa.String(128), nullable=True),
        sa.Column('protocol', sa.String(50), nullable=False),
        sa.Column('participants', JSONB, nullable=False),
        sa.Column('party_endpoints', JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mpc_session_status', 'mpc_sessions', ['status'])
    op.create_index('idx_mpc_session_protocol', 'mpc_sessions', ['protocol'])
    op.create_index('idx_mpc_session_created_at', 'mpc_sessions', ['created_at'])

    # tee_instances
    op.create_table('tee_instances',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('instance_id', sa.String(128), nullable=False, unique=True),
        sa.Column('task_id', sa.String(128), nullable=True),
        sa.Column('runtime', sa.String(50), nullable=False),
        sa.Column('enclave_config', JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('mr_enclave', sa.String(128), nullable=True),
        sa.Column('mr_signer', sa.String(128), nullable=True),
        sa.Column('ra_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_tee_instance_status', 'tee_instances', ['status'])
    op.create_index('idx_tee_instance_runtime', 'tee_instances', ['runtime'])
    op.create_index('idx_tee_instance_created_at', 'tee_instances', ['created_at'])

    # he_keys
    op.create_table('he_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', sa.String(128), nullable=False, unique=True),
        sa.Column('scheme', sa.String(50), nullable=False),
        sa.Column('poly_modulus_degree', sa.Integer, nullable=False),
        sa.Column('coeff_modulus_bits', sa.Integer, nullable=False),
        sa.Column('public_key_hash', sa.String(128), nullable=False),
        sa.Column('secret_key_hash', sa.String(128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_he_key_scheme', 'he_keys', ['scheme'])
    op.create_index('idx_he_key_created_at', 'he_keys', ['created_at'])

    # he_ciphertexts
    op.create_table('he_ciphertexts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ciphertext_id', sa.String(128), nullable=False, unique=True),
        sa.Column('key_id', sa.String(128), nullable=False),
        sa.Column('scheme', sa.String(50), nullable=False),
        sa.Column('asset_id', sa.String(128), nullable=True),
        sa.Column('size_params', JSONB, nullable=True),
        sa.Column('source_operation', sa.String(100), nullable=True),
        sa.Column('source_ciphertexts', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_he_ciphertext_key_id', 'he_ciphertexts', ['key_id'])
    op.create_index('idx_he_ciphertext_scheme', 'he_ciphertexts', ['scheme'])
    op.create_index('idx_he_ciphertext_asset_id', 'he_ciphertexts', ['asset_id'])
    op.create_index('idx_he_ciphertext_created_at', 'he_ciphertexts', ['created_at'])

    # fl_models
    op.create_table('fl_models',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', sa.String(128), nullable=False, unique=True),
        sa.Column('task_id', sa.String(128), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('algorithm', sa.String(100), nullable=False),
        sa.Column('participants', JSONB, nullable=False),
        sa.Column('model_params', JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('metrics', JSONB, nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_fl_model_task_id', 'fl_models', ['task_id'])
    op.create_index('idx_fl_model_status', 'fl_models', ['status'])
    op.create_index('idx_fl_model_algorithm', 'fl_models', ['algorithm'])
    op.create_index('idx_fl_model_created_at', 'fl_models', ['created_at'])

    # ==================== 运营服务 ====================

    # monitor_alerts
    op.create_table('monitor_alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='firing'),
        sa.Column('acknowledged_by', sa.String(128), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('alert_metadata', JSONB, nullable=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_monitor_alert_type', 'monitor_alerts', ['type'])
    op.create_index('idx_monitor_alert_severity', 'monitor_alerts', ['severity'])
    op.create_index('idx_monitor_alert_status', 'monitor_alerts', ['status'])
    op.create_index('idx_monitor_alert_fired_at', 'monitor_alerts', ['fired_at'])
    op.create_index('idx_monitor_alert_source', 'monitor_alerts', ['source'])

    # portal_quick_links
    op.create_table('portal_quick_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_portal_quicklink_user_id', 'portal_quick_links', ['user_id'])
    op.create_index('idx_portal_quicklink_sort_order', 'portal_quick_links', ['sort_order'])

    # portal_notifications
    op.create_table('portal_notifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False, server_default='info'),
        sa.Column('read', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_portal_notif_user_id', 'portal_notifications', ['user_id'])
    op.create_index('idx_portal_notif_read', 'portal_notifications', ['read'])
    op.create_index('idx_portal_notif_type', 'portal_notifications', ['notification_type'])
    op.create_index('idx_portal_notif_created_at', 'portal_notifications', ['created_at'])

    # portal_layouts
    op.create_table('portal_layouts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('layout_config', JSONB, nullable=False),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_portal_layout_user_id', 'portal_layouts', ['user_id'])
    op.create_index('idx_portal_layout_default', 'portal_layouts', ['is_default'])

    # portal_activity_logs
    op.create_table('portal_activity_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_portal_activity_user_id', 'portal_activity_logs', ['user_id'])
    op.create_index('idx_portal_activity_action', 'portal_activity_logs', ['action'])
    op.create_index('idx_portal_activity_created_at', 'portal_activity_logs', ['created_at'])

    # sla_configs
    op.create_table('sla_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('service_name', sa.String(200), nullable=False),
        sa.Column('availability_target', sa.Float, nullable=False, server_default='99.9'),
        sa.Column('response_time_target', sa.Integer, nullable=False, server_default='500'),
        sa.Column('error_rate_target', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sla_config_service_name', 'sla_configs', ['service_name'])
    op.create_index('idx_sla_config_enabled', 'sla_configs', ['enabled'])

    # sla_reports
    op.create_table('sla_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('service_name', sa.String(200), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('availability', sa.Float, nullable=True),
        sa.Column('avg_response_time', sa.Float, nullable=True),
        sa.Column('error_rate', sa.Float, nullable=True),
        sa.Column('total_requests', sa.Integer, nullable=True),
        sa.Column('failed_requests', sa.Integer, nullable=True),
        sa.Column('met_sla', sa.Boolean, nullable=True),
        sa.Column('report_data', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sla_report_service_name', 'sla_reports', ['service_name'])
    op.create_index('idx_sla_report_period_start', 'sla_reports', ['period_start'])
    op.create_index('idx_sla_report_period_end', 'sla_reports', ['period_end'])

    # sla_alert_configs
    op.create_table('sla_alert_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('service_name', sa.String(200), nullable=False),
        sa.Column('metric', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Float, nullable=False),
        sa.Column('operator', sa.String(10), nullable=False),
        sa.Column('notification_channels', JSONB, nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sla_alert_service_name', 'sla_alert_configs', ['service_name'])
    op.create_index('idx_sla_alert_enabled', 'sla_alert_configs', ['enabled'])

    # sla_metric_history
    op.create_table('sla_metric_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('service_name', sa.String(200), nullable=False),
        sa.Column('metric', sa.String(50), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_metric_history_service_name', 'sla_metric_history', ['service_name'])
    op.create_index('idx_metric_history_metric', 'sla_metric_history', ['metric'])
    op.create_index('idx_metric_history_timestamp', 'sla_metric_history', ['timestamp'])

    # cluster_nodes
    op.create_table('cluster_nodes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('node_id', sa.String(128), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('organization_id', sa.String(128), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('capabilities', JSONB, nullable=True),
        sa.Column('active_tasks', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('node_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_cluster_node_name', 'cluster_nodes', ['name'])
    op.create_index('idx_cluster_node_type', 'cluster_nodes', ['node_type'])
    op.create_index('idx_cluster_node_status', 'cluster_nodes', ['status'])
    op.create_index('idx_cluster_node_region', 'cluster_nodes', ['region'])
    op.create_index('idx_cluster_node_organization_id', 'cluster_nodes', ['organization_id'])

    # task_dispatches
    op.create_table('task_dispatches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('dispatch_id', sa.String(128), nullable=False, unique=True),
        sa.Column('task_id', sa.String(128), nullable=False),
        sa.Column('node_id', sa.String(128), nullable=False),
        sa.Column('node_endpoint', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_task_dispatch_task_id', 'task_dispatches', ['task_id'])
    op.create_index('idx_task_dispatch_node_id', 'task_dispatches', ['node_id'])
    op.create_index('idx_task_dispatch_status', 'task_dispatches', ['status'])
    op.create_index('idx_task_dispatch_dispatched_at', 'task_dispatches', ['dispatched_at'])

    # data_versions
    op.create_table('data_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('asset_id', sa.String(128), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('data_hash', sa.String(128), nullable=True),
        sa.Column('size_bytes', sa.Integer, nullable=True),
        sa.Column('record_count', sa.Integer, nullable=True),
        sa.Column('schema_info', JSONB, nullable=True),
        sa.Column('diff_from_parent', JSONB, nullable=True),
        sa.Column('version_metadata', JSONB, nullable=True),
        sa.Column('parent_version_id', sa.String(128), nullable=True),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_data_version_asset_id', 'data_versions', ['asset_id'])
    op.create_index('idx_data_version_version_number', 'data_versions', ['version_number'])
    op.create_index('idx_data_version_parent_id', 'data_versions', ['parent_version_id'])
    op.create_index('idx_data_version_created_at', 'data_versions', ['created_at'])
    op.create_unique_constraint('uq_data_version_asset_version', 'data_versions', ['asset_id', 'version_number'])

    # version_tags
    op.create_table('version_tags',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tag_name', sa.String(100), nullable=False),
        sa.Column('asset_id', sa.String(128), nullable=False),
        sa.Column('version_id', sa.String(128), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_version_tag_name', 'version_tags', ['tag_name'])
    op.create_index('idx_version_tag_asset_id', 'version_tags', ['asset_id'])
    op.create_index('idx_version_tag_version_id', 'version_tags', ['version_id'])
    op.create_unique_constraint('uq_version_tag_asset_tag', 'version_tags', ['asset_id', 'tag_name'])

    # current_versions
    op.create_table('current_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', sa.String(128), nullable=False),
        sa.Column('version_id', sa.String(128), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('updated_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_current_version_asset_id', 'current_versions', ['asset_id'])
    op.create_unique_constraint('uq_current_version_asset', 'current_versions', ['asset_id'])

    # ==================== 安全服务 ====================

    # verifiable_credentials
    op.create_table('verifiable_credentials',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document', JSONB, nullable=False),
        sa.Column('issuer_did', sa.String(200), nullable=False),
        sa.Column('subject_did', sa.String(200), nullable=False),
        sa.Column('revoked', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_vc_issuer_did', 'verifiable_credentials', ['issuer_did'])
    op.create_index('idx_vc_subject_did', 'verifiable_credentials', ['subject_did'])
    op.create_index('idx_vc_revoked', 'verifiable_credentials', ['revoked'])
    op.create_index('idx_vc_issued_at', 'verifiable_credentials', ['issued_at'])

    # vc_revocation_list
    op.create_table('vc_revocation_list',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('vc_id', sa.String(128), nullable=False, unique=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('revoked_by', sa.String(200), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_revocation_vc_id', 'vc_revocation_list', ['vc_id'])
    op.create_index('idx_revocation_revoked_at', 'vc_revocation_list', ['revoked_at'])

    # zkp_proofs
    op.create_table('zkp_proofs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('proof_type', sa.String(50), nullable=False),
        sa.Column('prover_did', sa.String(200), nullable=False),
        sa.Column('circuit_id', sa.String(128), nullable=False),
        sa.Column('public_inputs', JSONB, nullable=True),
        sa.Column('proof_data', JSONB, nullable=False),
        sa.Column('messages_count', sa.Integer, nullable=True),
        sa.Column('range_min', sa.Integer, nullable=True),
        sa.Column('range_max', sa.Integer, nullable=True),
        sa.Column('verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_zkp_proof_type', 'zkp_proofs', ['proof_type'])
    op.create_index('idx_zkp_proof_prover_did', 'zkp_proofs', ['prover_did'])
    op.create_index('idx_zkp_proof_circuit_id', 'zkp_proofs', ['circuit_id'])
    op.create_index('idx_zkp_proof_verified', 'zkp_proofs', ['verified'])
    op.create_index('idx_zkp_proof_created_at', 'zkp_proofs', ['created_at'])

    # knowledge_bases
    op.create_table('knowledge_bases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('organization_id', sa.String(128), nullable=False),
        sa.Column('embedding_model', sa.String(100), nullable=False, server_default='text-embedding-ada-002'),
        sa.Column('chunk_size', sa.Integer, nullable=False, server_default='1000'),
        sa.Column('chunk_overlap', sa.Integer, nullable=False, server_default='200'),
        sa.Column('document_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_kb_name', 'knowledge_bases', ['name'])
    op.create_index('idx_kb_organization_id', 'knowledge_bases', ['organization_id'])

    # knowledge_documents
    op.create_table('knowledge_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('knowledge_base_id', sa.String(128), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('chunk_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='processing'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('doc_metadata', JSONB, nullable=True),
        sa.Column('uploaded_by', sa.String(128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_kdoc_kb_id', 'knowledge_documents', ['knowledge_base_id'])
    op.create_index('idx_kdoc_status', 'knowledge_documents', ['status'])
    op.create_index('idx_kdoc_filename', 'knowledge_documents', ['filename'])

    # agent_configs
    op.create_table('agent_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('organization_id', sa.String(128), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False, server_default='gpt-3.5-turbo'),
        sa.Column('model_provider', sa.String(50), nullable=False, server_default='openai'),
        sa.Column('temperature', sa.Float, nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer, nullable=False, server_default='2000'),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('knowledge_base_ids', JSONB, nullable=True),
        sa.Column('tools', JSONB, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_agent_name', 'agent_configs', ['name'])
    op.create_index('idx_agent_type', 'agent_configs', ['agent_type'])
    op.create_index('idx_agent_organization_id', 'agent_configs', ['organization_id'])
    op.create_index('idx_agent_enabled', 'agent_configs', ['enabled'])

    # ==================== 沙箱增强表 ====================

    # sandbox_sessions
    op.create_table('sandbox_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('compute_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(128), nullable=False, unique=True),
        sa.Column('container_id', sa.String(128), nullable=True),
        sa.Column('pid', sa.Integer, nullable=True),
        sa.Column('mode', sa.String(20), nullable=False, server_default='subprocess'),
        sa.Column('status', sa.String(30), nullable=False, server_default='created'),
        sa.Column('algorithm_hash', sa.String(128), nullable=True),
        sa.Column('input_asset_ids', JSONB, nullable=True),
        sa.Column('memory_limit', sa.String(20), nullable=True),
        sa.Column('cpu_limit', sa.String(20), nullable=True),
        sa.Column('disk_limit_mb', sa.Integer, nullable=True),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, server_default='300'),
        sa.Column('exit_code', sa.Integer, nullable=True),
        sa.Column('stdout_summary', sa.Text, nullable=True),
        sa.Column('stderr_summary', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('work_dir', sa.String(500), nullable=True),
        sa.Column('destroyed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sandbox_session_task_id', 'sandbox_sessions', ['task_id'])
    op.create_index('idx_sandbox_session_status', 'sandbox_sessions', ['status'])
    op.create_index('idx_sandbox_session_created_at', 'sandbox_sessions', ['created_at'])

    # sandbox_resource_usages
    op.create_table('sandbox_resource_usages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sandbox_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('peak_memory_mb', sa.Float, nullable=True),
        sa.Column('avg_cpu_percent', sa.Float, nullable=True),
        sa.Column('disk_used_mb', sa.Float, nullable=True),
        sa.Column('network_rx_bytes', sa.Integer, nullable=True),
        sa.Column('network_tx_bytes', sa.Integer, nullable=True),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sandbox_resource_session_id', 'sandbox_resource_usages', ['session_id'])
    op.create_index('idx_sandbox_resource_recorded_at', 'sandbox_resource_usages', ['recorded_at'])

    # sandbox_violations
    op.create_table('sandbox_violations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sandbox_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('source_line', sa.Text, nullable=True),
        sa.Column('action_taken', sa.String(50), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sandbox_violation_session_id', 'sandbox_violations', ['session_id'])
    op.create_index('idx_sandbox_violation_type', 'sandbox_violations', ['violation_type'])
    op.create_index('idx_sandbox_violation_created_at', 'sandbox_violations', ['created_at'])


def downgrade() -> None:
    """降级迁移 - 删除所有 Batch 2 表"""

    # 沙箱增强
    op.drop_table('sandbox_violations')
    op.drop_table('sandbox_resource_usages')
    op.drop_table('sandbox_sessions')

    # 安全服务
    op.drop_table('agent_configs')
    op.drop_table('knowledge_documents')
    op.drop_table('knowledge_bases')
    op.drop_table('zkp_proofs')
    op.drop_table('vc_revocation_list')
    op.drop_table('verifiable_credentials')

    # 运营服务
    op.drop_table('current_versions')
    op.drop_table('version_tags')
    op.drop_table('data_versions')
    op.drop_table('task_dispatches')
    op.drop_table('cluster_nodes')
    op.drop_table('sla_metric_history')
    op.drop_table('sla_alert_configs')
    op.drop_table('sla_reports')
    op.drop_table('sla_configs')
    op.drop_table('portal_activity_logs')
    op.drop_table('portal_layouts')
    op.drop_table('portal_notifications')
    op.drop_table('portal_quick_links')
    op.drop_table('monitor_alerts')

    # 核心计算
    op.drop_table('fl_models')
    op.drop_table('he_ciphertexts')
    op.drop_table('he_keys')
    op.drop_table('tee_instances')
    op.drop_table('mpc_sessions')
    op.drop_table('fate_jobs')
