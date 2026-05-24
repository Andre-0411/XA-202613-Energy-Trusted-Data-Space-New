"""add organizations and blockchain settlement tables

Revision ID: 0004_add_blockchain_settlement
Revises: 0003_add_data_quality
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004_add_blockchain_settlement'
down_revision: Union[str, None] = '0003_add_data_quality'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建组织表（结算记录依赖此表）
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True, comment='组织 ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='组织名称'),
        sa.Column('code', sa.String(50), nullable=False, unique=True, comment='组织编码'),
        sa.Column('type', sa.String(50), nullable=False, comment='组织类型 (energy_company/grid/utility/retail)'),
        sa.Column('contact_person', sa.String(100), nullable=True, comment='联系人'),
        sa.Column('contact_phone', sa.String(20), nullable=True, comment='联系电话'),
        sa.Column('contact_email', sa.String(100), nullable=True, comment='联系邮箱'),
        sa.Column('address', sa.Text(), nullable=True, comment='地址'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态 (active/inactive/suspended)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='组织表'
    )

    # 创建结算记录表
    op.create_table(
        'settlement_records',
        sa.Column('id', sa.Integer(), primary_key=True, comment='结算 ID'),
        sa.Column('transaction_id', sa.String(64), nullable=False, unique=True, comment='交易 ID'),
        sa.Column('from_org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, comment='付款方 ID'),
        sa.Column('to_org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False, comment='收款方 ID'),
        sa.Column('amount', sa.Float(), nullable=False, comment='结算金额'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='CNY', comment='货币类型'),
        sa.Column('settlement_type', sa.String(50), nullable=False, comment='结算类型 (data_usage/compute/storage)'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='状态 (pending/confirmed/failed)'),
        sa.Column('blockchain_tx_hash', sa.String(128), nullable=True, comment='区块链交易哈希'),
        sa.Column('description', sa.Text(), nullable=True, comment='结算描述'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()'), comment='更新时间'),
        comment='结算记录表'
    )

    # 创建区块链交易表
    op.create_table(
        'blockchain_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, comment='交易 ID'),
        sa.Column('tx_hash', sa.String(128), nullable=False, unique=True, comment='交易哈希'),
        sa.Column('block_number', sa.Integer(), nullable=True, comment='区块号'),
        sa.Column('chain_type', sa.String(20), nullable=False, comment='链类型 (fisco/ethereum)'),
        sa.Column('contract_address', sa.String(128), nullable=True, comment='合约地址'),
        sa.Column('method', sa.String(100), nullable=True, comment='调用方法'),
        sa.Column('from_address', sa.String(128), nullable=True, comment='发起地址'),
        sa.Column('gas_used', sa.Integer(), nullable=True, comment='Gas 消耗'),
        sa.Column('gas_price', sa.Float(), nullable=True, comment='Gas 价格'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='状态 (pending/success/failed)'),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True, comment='原始数据'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='创建时间'),
        comment='区块链交易表'
    )

    # 创建索引
    op.create_index('ix_organizations_code', 'organizations', ['code'])
    op.create_index('ix_organizations_status', 'organizations', ['status'])
    op.create_index('ix_settlement_records_transaction_id', 'settlement_records', ['transaction_id'])
    op.create_index('ix_settlement_records_from_org_id', 'settlement_records', ['from_org_id'])
    op.create_index('ix_settlement_records_to_org_id', 'settlement_records', ['to_org_id'])
    op.create_index('ix_settlement_records_status', 'settlement_records', ['status'])
    op.create_index('ix_blockchain_transactions_tx_hash', 'blockchain_transactions', ['tx_hash'])
    op.create_index('ix_blockchain_transactions_block_number', 'blockchain_transactions', ['block_number'])
    op.create_index('ix_blockchain_transactions_status', 'blockchain_transactions', ['status'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_blockchain_transactions_status', table_name='blockchain_transactions')
    op.drop_index('ix_blockchain_transactions_block_number', table_name='blockchain_transactions')
    op.drop_index('ix_blockchain_transactions_tx_hash', table_name='blockchain_transactions')
    op.drop_index('ix_settlement_records_status', table_name='settlement_records')
    op.drop_index('ix_settlement_records_to_org_id', table_name='settlement_records')
    op.drop_index('ix_settlement_records_from_org_id', table_name='settlement_records')
    op.drop_index('ix_settlement_records_transaction_id', table_name='settlement_records')
    op.drop_index('ix_organizations_status', table_name='organizations')
    op.drop_index('ix_organizations_code', table_name='organizations')

    # 删除表
    op.drop_table('blockchain_transactions')
    op.drop_table('settlement_records')
    op.drop_table('organizations')
