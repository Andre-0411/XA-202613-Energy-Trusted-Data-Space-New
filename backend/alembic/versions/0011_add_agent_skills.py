"""add agent skills tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-27 01:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agent_skills table
    op.create_table('agent_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('instructions', sa.Text, nullable=False),
        sa.Column('examples', postgresql.JSONB, nullable=True),
        sa.Column('parameters', postgresql.JSONB, nullable=True),
        sa.Column('trigger_patterns', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('trigger_keywords', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('intent_types', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('use_count', sa.Integer, server_default='0'),
        sa.Column('success_count', sa.Integer, server_default='0'),
        sa.Column('success_rate', sa.Float, server_default='0.0'),
        sa.Column('avg_execution_time', sa.Float, server_default='0.0'),
        sa.Column('source', sa.String(50), server_default='manual'),
        sa.Column('learned_from', sa.Text, nullable=True),
        sa.Column('confidence', sa.Float, server_default='0.5'),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('version', sa.Integer, server_default='1'),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_skill_category', 'agent_skills', ['category'])
    op.create_index('idx_skill_source', 'agent_skills', ['source'])
    op.create_index('idx_skill_active', 'agent_skills', ['is_active'])
    op.create_index('idx_skill_confidence', 'agent_skills', ['confidence'])

    # Create skill_execution_logs table
    op.create_table('skill_execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('input_text', sa.Text, nullable=False),
        sa.Column('output_text', sa.Text, nullable=True),
        sa.Column('execution_time_ms', sa.Integer, server_default='0'),
        sa.Column('success', sa.Boolean, server_default='true'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('match_score', sa.Float, server_default='0.0'),
        sa.Column('match_method', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_exec_skill_id', 'skill_execution_logs', ['skill_id'])
    op.create_index('idx_exec_user_id', 'skill_execution_logs', ['user_id'])
    op.create_index('idx_exec_created', 'skill_execution_logs', ['created_at'])

    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('preference_type', sa.String(50), nullable=False),
        sa.Column('preference_key', sa.String(100), nullable=False),
        sa.Column('preference_value', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float, server_default='0.5'),
        sa.Column('learned_count', sa.Integer, server_default='1'),
        sa.Column('last_used_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_pref_user', 'user_preferences', ['user_id'])
    op.create_index('idx_pref_type', 'user_preferences', ['preference_type'])


def downgrade() -> None:
    op.drop_table('user_preferences')
    op.drop_table('skill_execution_logs')
    op.drop_table('agent_skills')
