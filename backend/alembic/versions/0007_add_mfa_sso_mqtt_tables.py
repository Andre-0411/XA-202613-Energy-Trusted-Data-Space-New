"""添加 MFA、SSO、MQTT 数据持久化表

Revision ID: 0007_add_mfa_sso_mqtt_tables
Revises: 0006_add_ops_enhanced
Create Date: 2026-05-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision: str = '0007_add_mfa_sso_mqtt_tables'
down_revision: Union[str, None] = '0006_add_ops_enhanced'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建 MFA、SSO、MQTT 表"""

    # ==================== MFA 相关表 ====================

    # mfa_configs
    op.create_table('mfa_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(128), nullable=False, unique=True),
        sa.Column('secret', sa.String(128), nullable=False),
        sa.Column('method', sa.String(20), nullable=False, server_default='totp'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mfa_config_user_id', 'mfa_configs', ['user_id'])
    op.create_index('idx_mfa_config_enabled', 'mfa_configs', ['enabled'])

    # mfa_backup_codes
    op.create_table('mfa_backup_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('mfa_config_id', UUID(as_uuid=True), sa.ForeignKey('mfa_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code_hash', sa.String(128), nullable=False),
        sa.Column('used', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mfa_backup_config_id', 'mfa_backup_codes', ['mfa_config_id'])
    op.create_index('idx_mfa_backup_code_hash', 'mfa_backup_codes', ['code_hash'])

    # mfa_sessions
    op.create_table('mfa_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('mfa_config_id', UUID(as_uuid=True), sa.ForeignKey('mfa_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(128), nullable=False, unique=True),
        sa.Column('verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mfa_session_session_id', 'mfa_sessions', ['session_id'])
    op.create_index('idx_mfa_session_config_id', 'mfa_sessions', ['mfa_config_id'])
    op.create_index('idx_mfa_session_expires_at', 'mfa_sessions', ['expires_at'])

    # ==================== SSO 相关表 ====================

    # sso_providers
    op.create_table('sso_providers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_id', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('protocol', sa.String(20), nullable=False),
        sa.Column('client_id', sa.String(200), nullable=True),
        sa.Column('client_secret', sa.String(200), nullable=True),
        sa.Column('authorize_url', sa.String(500), nullable=True),
        sa.Column('token_url', sa.String(500), nullable=True),
        sa.Column('userinfo_url', sa.String(500), nullable=True),
        sa.Column('redirect_uri', sa.String(500), nullable=True),
        sa.Column('scopes', JSONB, nullable=True, server_default='["openid", "profile", "email"]'),
        sa.Column('metadata_url', sa.String(500), nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sso_provider_provider_id', 'sso_providers', ['provider_id'])
    op.create_index('idx_sso_provider_enabled', 'sso_providers', ['enabled'])

    # sso_sessions
    op.create_table('sso_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(128), nullable=False, unique=True),
        sa.Column('user_id', sa.String(128), nullable=False),
        sa.Column('provider_id_ref', sa.String(64), nullable=False),
        sa.Column('access_token', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_sso_session_session_id', 'sso_sessions', ['session_id'])
    op.create_index('idx_sso_session_user_id', 'sso_sessions', ['user_id'])
    op.create_index('idx_sso_session_provider', 'sso_sessions', ['provider_id_ref'])
    op.create_index('idx_sso_session_expires_at', 'sso_sessions', ['expires_at'])

    # sso_pending_auths
    op.create_table('sso_pending_auths',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('state', sa.String(128), nullable=False, unique=True),
        sa.Column('provider_id', sa.String(64), nullable=False),
        sa.Column('redirect_uri', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_sso_pending_state', 'sso_pending_auths', ['state'])
    op.create_index('idx_sso_pending_expires_at', 'sso_pending_auths', ['expires_at'])

    # ==================== MQTT 数据相关表 ====================

    # mqtt_devices
    op.create_table('mqtt_devices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_did', sa.String(128), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('enterprise', sa.String(200), nullable=True),
        sa.Column('location', sa.String(500), nullable=True),
        sa.Column('capacity_kw', sa.Float, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='online'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('device_metadata', JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mqtt_device_did', 'mqtt_devices', ['device_did'])
    op.create_index('idx_mqtt_device_status', 'mqtt_devices', ['status'])
    op.create_index('idx_mqtt_device_enterprise', 'mqtt_devices', ['enterprise'])

    # mqtt_data_records
    op.create_table('mqtt_data_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('mqtt_devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_did', sa.String(128), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('values', JSONB, nullable=False),
        sa.Column('timestamp', sa.String(64), nullable=False),
        sa.Column('signature', sa.Text, nullable=False, server_default=''),
        sa.Column('stored_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mqtt_data_device_did', 'mqtt_data_records', ['device_did'])
    op.create_index('idx_mqtt_data_data_type', 'mqtt_data_records', ['data_type'])
    op.create_index('idx_mqtt_data_timestamp', 'mqtt_data_records', ['timestamp'])
    op.create_index('idx_mqtt_data_device_type', 'mqtt_data_records', ['device_did', 'data_type'])
    op.create_index('idx_mqtt_data_stored_at', 'mqtt_data_records', ['stored_at'])

    # mqtt_alarms
    op.create_table('mqtt_alarms',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('mqtt_devices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('device_did', sa.String(128), nullable=False),
        sa.Column('alarm_type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('values', JSONB, nullable=True, server_default='{}'),
        sa.Column('acknowledged', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_mqtt_alarm_device_did', 'mqtt_alarms', ['device_did'])
    op.create_index('idx_mqtt_alarm_type', 'mqtt_alarms', ['alarm_type'])
    op.create_index('idx_mqtt_alarm_severity', 'mqtt_alarms', ['severity'])
    op.create_index('idx_mqtt_alarm_timestamp', 'mqtt_alarms', ['timestamp'])


def downgrade() -> None:
    """降级迁移 - 删除 MFA、SSO、MQTT 表"""

    # MQTT 相关表
    op.drop_table('mqtt_alarms')
    op.drop_table('mqtt_data_records')
    op.drop_table('mqtt_devices')

    # SSO 相关表
    op.drop_table('sso_pending_auths')
    op.drop_table('sso_sessions')
    op.drop_table('sso_providers')

    # MFA 相关表
    op.drop_table('mfa_sessions')
    op.drop_table('mfa_backup_codes')
    op.drop_table('mfa_configs')
