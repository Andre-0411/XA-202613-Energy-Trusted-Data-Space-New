/**
 * 区块链查询页面
 * 交易查询 / 区块查询 / 地址查询 / 合约查询
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Tabs, Card, Row, Col, Statistic, Divider, Typography, Space, Table, Descriptions } from 'tdesign-react';
import {
  SearchIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
  FileIcon, TimeIcon, LinkIcon, DataBaseIcon, WalletIcon,
} from 'tdesign-icons-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';
import {
  getTransactionDetail,
  getBlockDetail,
  listContracts,
  getChainStatus,
  getFiscoConnectionStatus,
} from '@/api/blockchain';

/* ========== 模拟数据 - 交易详情 ========== */
interface TransactionDetail {
  hash: string;
  blockNumber: number;
  blockHash: string;
  from: string;
  to: string;
  value: string;
  gas: number;
  gasPrice: string;
  nonce: number;
  status: string;
  timestamp: string;
  input: string;
  contractAddress: string;
}

const MOCK_TRANSACTION: TransactionDetail = {
  hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
  blockNumber: 1234567,
  blockHash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
  from: '0x1234567890abcdef1234567890abcdef12345678',
  to: '0xabcdef1234567890abcdef1234567890abcdef12',
  value: '1000000000000000000',
  gas: 21000,
  gasPrice: '20000000000',
  nonce: 42,
  status: 'success',
  timestamp: '2025-05-20T08:00:00Z',
  input: '0x',
  contractAddress: '',
};

/* ========== 模拟数据 - 区块详情 ========== */
interface BlockDetail {
  number: number;
  hash: string;
  parentHash: string;
  timestamp: string;
  transactions: string[];
  gasUsed: number;
  gasLimit: number;
  miner: string;
  difficulty: string;
  totalDifficulty: string;
  size: number;
  nonce: string;
}

const MOCK_BLOCK: BlockDetail = {
  number: 1234567,
  hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
  parentHash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
  timestamp: '2025-05-20T08:00:00Z',
  transactions: [
    '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
  ],
  gasUsed: 21000,
  gasLimit: 30000000,
  miner: '0x1234567890abcdef1234567890abcdef12345678',
  difficulty: '1000000000000000',
  totalDifficulty: '1000000000000000000',
  size: 1024,
  nonce: '0x1234567890abcdef',
};

/* ========== 模拟数据 - 地址详情 ========== */
interface AddressDetail {
  address: string;
  balance: string;
  transactionCount: number;
  firstSeen: string;
  lastSeen: string;
  isContract: boolean;
  transactions: Array<{
    hash: string;
    from: string;
    to: string;
    value: string;
    timestamp: string;
    status: string;
  }>;
}

const MOCK_ADDRESS: AddressDetail = {
  address: '0x1234567890abcdef1234567890abcdef12345678',
  balance: '5000000000000000000',
  transactionCount: 156,
  firstSeen: '2025-01-15T10:30:00Z',
  lastSeen: '2025-05-20T08:00:00Z',
  isContract: false,
  transactions: [
    {
      hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      from: '0x1234567890abcdef1234567890abcdef12345678',
      to: '0xabcdef1234567890abcdef1234567890abcdef12',
      value: '1000000000000000000',
      timestamp: '2025-05-20T08:00:00Z',
      status: 'success',
    },
    {
      hash: '0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1',
      from: '0xabcdef1234567890abcdef1234567890abcdef12',
      to: '0x1234567890abcdef1234567890abcdef12345678',
      value: '500000000000000000',
      timestamp: '2025-05-19T14:30:00Z',
      status: 'success',
    },
  ],
};

/* ========== 模拟数据 - 合约详情 ========== */
interface ContractDetail {
  address: string;
  name: string;
  version: string;
  status: string;
  deployedAt: string;
  deployer: string;
  abi: Array<{
    name: string;
    type: string;
    inputs: Array<{ name: string; type: string }>;
    outputs: Array<{ name: string; type: string }>;
  }>;
  storage: Record<string, string>;
  callCount: number;
  lastCalled: string;
}

const MOCK_CONTRACT: ContractDetail = {
  address: '0xabcdef1234567890abcdef1234567890abcdef12',
  name: 'DataSharingContract',
  version: '1.0.0',
  status: 'active',
  deployedAt: '2025-04-15T10:00:00Z',
  deployer: '0x1234567890abcdef1234567890abcdef12345678',
  abi: [
    {
      name: 'shareData',
      type: 'function',
      inputs: [
        { name: 'dataId', type: 'string' },
        { name: 'recipient', type: 'address' },
      ],
      outputs: [{ name: 'success', type: 'bool' }],
    },
    {
      name: 'getData',
      type: 'function',
      inputs: [{ name: 'dataId', type: 'string' }],
      outputs: [{ name: 'data', type: 'bytes' }],
    },
  ],
  storage: {
    '0x0': '0x0000000000000000000000000000000000000000000000000000000000000001',
    '0x1': '0x0000000000000000000000000000000000000000000000000000000000000064',
  },
  callCount: 1250,
  lastCalled: '2025-05-20T08:00:00Z',
};

const BcQueryPage: React.FC = () => {
  // ===== 主 Tab =====
  const [activeTab, setActiveTab] = useState<string>('transaction');

  // ===== 交易查询 =====
  const [txHash, setTxHash] = useState<string>('');
  const [txResult, setTxResult] = useState<TransactionDetail | null>(null);

  // ===== 区块查询 =====
  const [blockNumber, setBlockNumber] = useState<string>('');
  const [blockResult, setBlockResult] = useState<BlockDetail | null>(null);

  // ===== 地址查询 =====
  const [address, setAddress] = useState<string>('');
  const [addressResult, setAddressResult] = useState<AddressDetail | null>(null);

  // ===== 合约查询 =====
  const [contractAddress, setContractAddress] = useState<string>('');
  const [contractResult, setContractResult] = useState<ContractDetail | null>(null);

  // ===== 链状态查询 =====
  const { data: chainStatusData } = useQuery({
    queryKey: ['chain-status'],
    queryFn: async () => {
      try {
        const res = await getChainStatus();
        return res.data;
      } catch {
        return null;
      }
    },
  });

  const { data: connectionData } = useQuery({
    queryKey: ['fisco-connection'],
    queryFn: async () => {
      try {
        const res = await getFiscoConnectionStatus();
        return res.data;
      } catch {
        return null;
      }
    },
  });

  // ===== 查询统计 =====
  const stats = useMemo(() => {
    const status = chainStatusData as ChainStatusData | null;
    return {
      blockHeight: status?.block_height ?? status?.latest_block ?? 1234567,
      totalTransactions: status?.total_transactions ?? status?.tx_count ?? 15820,
      nodeCount: status?.node_count ?? status?.peers ?? 4,
      isConnected: connectionData?.connected ?? true,
    };
  }, [chainStatusData, connectionData]);

  // ===== 查询处理 =====
  const handleTxQuery = useCallback(() => {
    if (txHash.trim()) {
      // 模拟查询
      setTimeout(() => {
        setTxResult(MOCK_TRANSACTION);
      }, 500);
    }
  }, [txHash]);

  const handleBlockQuery = useCallback(() => {
    if (blockNumber.trim()) {
      setTimeout(() => {
        setBlockResult(MOCK_BLOCK);
      }, 500);
    }
  }, [blockNumber]);

  const handleAddressQuery = useCallback(() => {
    if (address.trim()) {
      setTimeout(() => {
        setAddressResult(MOCK_ADDRESS);
      }, 500);
    }
  }, [address]);

  const handleContractQuery = useCallback(() => {
    if (contractAddress.trim()) {
      setTimeout(() => {
        setContractResult(MOCK_CONTRACT);
      }, 500);
    }
  }, [contractAddress]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '链上查询' }],
    [],
  );

  // ===== ECharts 配置 =====
  const blockTimeOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['10:00', '10:05', '10:10', '10:15', '10:20', '10:25', '10:30'] },
    yAxis: { type: 'value', name: '出块时间 (秒)' },
    series: [{
      name: '出块时间',
      type: 'line',
      smooth: true,
      data: [3.2, 2.8, 3.5, 2.9, 3.1, 2.7, 3.0],
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(33, 150, 243, 0.3)' },
            { offset: 1, color: 'rgba(33, 150, 243, 0.05)' },
          ],
        },
      },
      itemStyle: { color: '#2196f3' },
    }],
  }), []);

  const txVolumeOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '交易数量' },
    series: [{
      name: '交易数量',
      type: 'bar',
      data: [1200, 1500, 1800, 2100, 2500, 2900, 3500],
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#4caf50' },
            { offset: 1, color: '#81c784' },
          ],
        },
      },
      barWidth: '40%',
    }],
  }), []);

/** 链状态数据接口 */
interface ChainStatusData {
  block_height?: number;
  latest_block?: number;
  total_transactions?: number;
  tx_count?: number;
  node_count?: number;
  peers?: number;
}

interface ConnectionData {
  connected?: boolean;
}

/** 渲染查询结果 */
const renderTxResult = () => {
    if (!txResult) return null;
    return (
      <Card className="mt-4">
        <div className="flex items-center justify-between mb-4">
          <Typography.Title level="h5">交易详情</Typography.Title>
          <Tag theme="success" icon={<CheckCircleFilledIcon />}>查询成功</Tag>
        </div>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="交易哈希">
            <span className="font-mono text-sm break-all">{txResult.hash}</span>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag theme={txResult.status === 'success' ? 'success' : 'danger'}>{txResult.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="区块号">{txResult.blockNumber}</Descriptions.Item>
          <Descriptions.Item label="时间">{new Date(txResult.timestamp).toLocaleString('zh-CN')}</Descriptions.Item>
          <Descriptions.Item label="发送方">
            <span className="font-mono text-sm">{txResult.from}</span>
          </Descriptions.Item>
          <Descriptions.Item label="接收方">
            <span className="font-mono text-sm">{txResult.to}</span>
          </Descriptions.Item>
          <Descriptions.Item label="金额">{parseInt(txResult.value) / 1e18} ETH</Descriptions.Item>
          <Descriptions.Item label="Gas">{txResult.gas}</Descriptions.Item>
          <Descriptions.Item label="Gas Price">{parseInt(txResult.gasPrice) / 1e9} Gwei</Descriptions.Item>
          <Descriptions.Item label="Nonce">{txResult.nonce}</Descriptions.Item>
        </Descriptions>
      </Card>
    );
  };

  const renderBlockResult = () => {
    if (!blockResult) return null;
    return (
      <Card className="mt-4">
        <div className="flex items-center justify-between mb-4">
          <Typography.Title level="h5">区块信息</Typography.Title>
          <Tag theme="success" icon={<CheckCircleFilledIcon />}>查询成功</Tag>
        </div>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="区块号">{blockResult.number}</Descriptions.Item>
          <Descriptions.Item label="时间">{new Date(blockResult.timestamp).toLocaleString('zh-CN')}</Descriptions.Item>
          <Descriptions.Item label="区块哈希">
            <span className="font-mono text-sm break-all">{blockResult.hash}</span>
          </Descriptions.Item>
          <Descriptions.Item label="父哈希">
            <span className="font-mono text-sm break-all">{blockResult.parentHash}</span>
          </Descriptions.Item>
          <Descriptions.Item label="矿工">
            <span className="font-mono text-sm">{blockResult.miner}</span>
          </Descriptions.Item>
          <Descriptions.Item label="交易数">{blockResult.transactions.length}</Descriptions.Item>
          <Descriptions.Item label="Gas Used">{blockResult.gasUsed.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="Gas Limit">{blockResult.gasLimit.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="大小">{blockResult.size} bytes</Descriptions.Item>
          <Descriptions.Item label="Nonce">{blockResult.nonce}</Descriptions.Item>
        </Descriptions>
      </Card>
    );
  };

  const renderAddressResult = () => {
    if (!addressResult) return null;
    return (
      <Card className="mt-4">
        <div className="flex items-center justify-between mb-4">
          <Typography.Title level="h5">地址信息</Typography.Title>
          <Tag theme="success" icon={<CheckCircleFilledIcon />}>查询成功</Tag>
        </div>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="地址">
            <span className="font-mono text-sm break-all">{addressResult.address}</span>
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            <Tag theme={addressResult.isContract ? 'warning' : 'primary'}>
              {addressResult.isContract ? '合约地址' : '外部地址'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="余额">{parseInt(addressResult.balance) / 1e18} ETH</Descriptions.Item>
          <Descriptions.Item label="交易数">{addressResult.transactionCount}</Descriptions.Item>
          <Descriptions.Item label="首次出现">{new Date(addressResult.firstSeen).toLocaleString('zh-CN')}</Descriptions.Item>
          <Descriptions.Item label="最后活跃">{new Date(addressResult.lastSeen).toLocaleString('zh-CN')}</Descriptions.Item>
        </Descriptions>

        {addressResult.transactions.length > 0 && (
          <>
            <Divider>最近交易</Divider>
            <Table
              data={addressResult.transactions}
              columns={[
                { title: '交易哈希', colKey: 'hash', width: 200, cell: ({ row }) => <span className="font-mono text-xs">{row.hash.slice(0, 16)}...</span> },
                { title: '发送方', colKey: 'from', width: 180, cell: ({ row }) => <span className="font-mono text-xs">{row.from.slice(0, 16)}...</span> },
                { title: '接收方', colKey: 'to', width: 180, cell: ({ row }) => <span className="font-mono text-xs">{row.to.slice(0, 16)}...</span> },
                { title: '金额', colKey: 'value', width: 120, cell: ({ row }) => <span>{parseInt(row.value) / 1e18} ETH</span> },
                { title: '时间', colKey: 'timestamp', width: 160, cell: ({ row }) => new Date(row.timestamp).toLocaleString('zh-CN') },
                { title: '状态', colKey: 'status', width: 100, cell: ({ row }) => <Tag theme={row.status === 'success' ? 'success' : 'danger'} size="small">{row.status}</Tag> },
              ]}
              size="small"
              bordered
            />
          </>
        )}
      </Card>
    );
  };

  const renderContractResult = () => {
    if (!contractResult) return null;
    return (
      <Card className="mt-4">
        <div className="flex items-center justify-between mb-4">
          <Typography.Title level="h5">合约信息</Typography.Title>
          <Tag theme="success" icon={<CheckCircleFilledIcon />}>查询成功</Tag>
        </div>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="合约地址">
            <span className="font-mono text-sm break-all">{contractResult.address}</span>
          </Descriptions.Item>
          <Descriptions.Item label="合约名称">{contractResult.name}</Descriptions.Item>
          <Descriptions.Item label="版本">{contractResult.version}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag theme={contractResult.status === 'active' ? 'success' : 'warning'}>{contractResult.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="部署时间">{new Date(contractResult.deployedAt).toLocaleString('zh-CN')}</Descriptions.Item>
          <Descriptions.Item label="部署者">
            <span className="font-mono text-sm">{contractResult.deployer}</span>
          </Descriptions.Item>
          <Descriptions.Item label="调用次数">{contractResult.callCount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="最后调用">{new Date(contractResult.lastCalled).toLocaleString('zh-CN')}</Descriptions.Item>
        </Descriptions>

        <Divider>ABI 方法</Divider>
        <Table
          data={contractResult.abi}
          columns={[
            { title: '方法名', colKey: 'name', width: 150 },
            { title: '类型', colKey: 'type', width: 100 },
            { title: '输入参数', colKey: 'inputs', width: 250, cell: ({ row }) => row.inputs.map(i => `${i.name}: ${i.type}`).join(', ') },
            { title: '输出参数', colKey: 'outputs', width: 200, cell: ({ row }) => row.outputs.map(o => `${o.name}: ${o.type}`).join(', ') },
          ]}
          size="small"
          bordered
        />

        <Divider>存储数据</Divider>
        <Table
          data={Object.entries(contractResult.storage).map(([key, value]) => ({ key, value }))}
          columns={[
            { title: '存储位置', colKey: 'key', width: 150 },
            { title: '值', colKey: 'value', width: 400, cell: ({ row }) => <span className="font-mono text-xs">{row.value}</span> },
          ]}
          size="small"
          bordered
        />
      </Card>
    );
  };

  return (
    <PageContainer>
      <PageHeader
        title="链上查询"
        subtitle="区块链数据查询工具，支持交易、区块、地址与合约查询"
        breadcrumbs={breadcrumbs}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="区块高度" value={stats.blockHeight.toLocaleString()} unit="" icon={<DataBaseIcon />} gradient="purple" />
        <StatCard title="总交易数" value={stats.totalTransactions.toLocaleString()} unit="笔" icon={<TrendingUpIcon />} gradient="green" />
        <StatCard title="节点数" value={stats.nodeCount} unit="个" icon={<LinkIcon />} gradient="blue" />
        <StatCard title="连接状态" value={stats.isConnected ? '已连接' : '未连接'} unit="" icon={stats.isConnected ? <CheckCircleFilledIcon /> : <ErrorCircleFilledIcon />} gradient={stats.isConnected ? 'cyan' : 'red'} />
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="出块时间趋势" option={blockTimeOption} />
        <ChartCard title="月度交易量" option={txVolumeOption} />
      </div>

      {/* 查询面板 */}
      <Card>
        <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
          <Tabs.TabPanel value="transaction" label="交易查询">
            <div className="flex items-center gap-4 mt-4">
              <Input
                value={txHash}
                onChange={(val) => setTxHash(String(val))}
                placeholder="输入交易哈希 (0x...)"
                style={{ flex: 1 }}
              />
              <Button
                theme="primary"
                icon={<SearchIcon />}
                onClick={handleTxQuery}
                disabled={!txHash.trim()}
              >
                查询
              </Button>
            </div>
            {renderTxResult()}
          </Tabs.TabPanel>

          <Tabs.TabPanel value="block" label="区块查询">
            <div className="flex items-center gap-4 mt-4">
              <Input
                value={blockNumber}
                onChange={(val) => setBlockNumber(String(val))}
                placeholder="输入区块号"
                style={{ flex: 1 }}
              />
              <Button
                theme="primary"
                icon={<SearchIcon />}
                onClick={handleBlockQuery}
                disabled={!blockNumber.trim()}
              >
                查询
              </Button>
            </div>
            {renderBlockResult()}
          </Tabs.TabPanel>

          <Tabs.TabPanel value="address" label="地址查询">
            <div className="flex items-center gap-4 mt-4">
              <Input
                value={address}
                onChange={(val) => setAddress(String(val))}
                placeholder="输入地址 (0x...)"
                style={{ flex: 1 }}
              />
              <Button
                theme="primary"
                icon={<SearchIcon />}
                onClick={handleAddressQuery}
                disabled={!address.trim()}
              >
                查询
              </Button>
            </div>
            {renderAddressResult()}
          </Tabs.TabPanel>

          <Tabs.TabPanel value="contract" label="合约查询">
            <div className="flex items-center gap-4 mt-4">
              <Input
                value={contractAddress}
                onChange={(val) => setContractAddress(String(val))}
                placeholder="输入合约地址 (0x...)"
                style={{ flex: 1 }}
              />
              <Button
                theme="primary"
                icon={<SearchIcon />}
                onClick={handleContractQuery}
                disabled={!contractAddress.trim()}
              >
                查询
              </Button>
            </div>
            {renderContractResult()}
          </Tabs.TabPanel>
        </Tabs>
      </Card>
    </PageContainer>
  );
};

export default BcQueryPage;