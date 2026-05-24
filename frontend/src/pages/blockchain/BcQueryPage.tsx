/**
 * 区块链查询页面
 * 交易查询 / 区块查询 / 合约查询 Tab
 * 数据来源: /api/v1/blockchain/* 真实区块链查询
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tag } from 'tdesign-react';
import {
  SearchIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import {
  getTransactionDetail,
  getBlockDetail,
  listContracts,
  getChainStatus,
  getFiscoConnectionStatus,
} from '@/api/blockchain';

const TAB_LABELS = ['交易查询', '区块查询', '合约查询'];

const BcQueryPage: React.FC = () => {
  const [tabValue, setTabValue] = useState<number>(0);

  // 交易查询
  const [txHash, setTxHash] = useState<string>('');
  const [txResult, setTxResult] = useState<Record<string, unknown> | null>(null);

  // 区块查询
  const [blockNumber, setBlockNumber] = useState<string>('');
  const [blockResult, setBlockResult] = useState<Record<string, unknown> | null>(null);

  // 合约查询
  const [contractAddress, setContractAddress] = useState<string>('');
  const [contractResult, setContractResult] = useState<Record<string, unknown> | null>(null);

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

  // ===== 交易查询 mutation =====
  const txMutation = useMutation({
    mutationFn: async (hash: string) => {
      const res = await getTransactionDetail(hash);
      return res.data;
    },
    onSuccess: (data) => {
      setTxResult(data as Record<string, unknown>);
    },
    onError: () => {
      setTxResult(null);
    },
  });

  // ===== 区块查询 mutation =====
  const blockMutation = useMutation({
    mutationFn: async (num: string) => {
      const res = await getBlockDetail(parseInt(num, 10));
      return res.data;
    },
    onSuccess: (data) => {
      setBlockResult(data as Record<string, unknown>);
    },
    onError: () => {
      setBlockResult(null);
    },
  });

  // ===== 合约查询 (从列表中搜索) =====
  const contractMutation = useMutation({
    mutationFn: async (address: string) => {
      const res = await listContracts();
      const contracts = Array.isArray(res.data) ? res.data : [];
      const found = contracts.find((c: any) =>
        c.address === address || c.contract_address === address
      );
      if (!found) throw new Error('合约未找到');
      return found;
    },
    onSuccess: (data) => {
      setContractResult(data as unknown as Record<string, unknown>);
    },
    onError: () => {
      setContractResult(null);
    },
  });

  // ===== 查询统计 (从链状态推导) =====
  const stats = useMemo(() => {
    const status = chainStatusData as any;
    return {
      blockHeight: status?.block_height ?? status?.latest_block ?? 0,
      totalTransactions: status?.total_transactions ?? status?.tx_count ?? 0,
      nodeCount: status?.node_count ?? status?.peers ?? 0,
      isConnected: connectionData?.connected ?? (connectionData as any)?.status === 'connected' ?? false,
    };
  }, [chainStatusData, connectionData]);

  const handleTxQuery = useCallback(() => {
    if (txHash.trim()) {
      txMutation.mutate(txHash.trim());
    }
  }, [txHash, txMutation]);

  const handleBlockQuery = useCallback(() => {
    if (blockNumber.trim()) {
      blockMutation.mutate(blockNumber.trim());
    }
  }, [blockNumber, blockMutation]);

  const handleContractQuery = useCallback(() => {
    if (contractAddress.trim()) {
      contractMutation.mutate(contractAddress.trim());
    }
  }, [contractAddress, contractMutation]);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '区块链查询' }],
    [],
  );

  /** 渲染 JSON 结果卡片 */
  const renderResultCard = (title: string, result: Record<string, unknown> | null, loading?: boolean, error?: string | null) => {
    if (loading) {
      return (
        <div className="mt-4 p-6 text-center rounded-lg border border-gray-200">
          <div className="inline-block w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-2">查询中...</p>
        </div>
      );
    }
    if (error) {
      return (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
      );
    }
    if (!result) return null;
    return (
      <div className="mt-4 rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50">
          <span className="text-sm font-semibold">{title}</span>
          <Tag theme="success" icon={<CheckCircleFilledIcon />}>查询成功</Tag>
        </div>
        <div className="p-3 bg-gray-900">
          <pre className="text-xs font-mono whitespace-pre-wrap text-gray-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageHeader
        title="区块链查询"
        subtitle="区块链数据查询工具，支持交易、区块与合约查询"
        breadcrumbs={breadcrumbs}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="区块高度" value={stats.blockHeight} unit="" icon={<SearchIcon />} gradient="purple" />
        <StatCard title="总交易数" value={stats.totalTransactions} unit="笔" icon={<TrendingUpIcon />} gradient="red" />
        <StatCard title="节点数" value={stats.nodeCount} unit="个" icon={<TrendingUpIcon />} gradient="green" />
        <StatCard title={stats.isConnected ? '已连接' : '未连接'} value={1} unit="" icon={stats.isConnected ? <CheckCircleFilledIcon /> : <ErrorCircleFilledIcon />} gradient={stats.isConnected ? 'cyan' : 'red'} />
      </div>

      {/* 查询面板 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4 flex-1">
        {/* Tab 栏 */}
        <div className="flex border-b border-gray-200 mb-6">
          {TAB_LABELS.map((label, idx) => (
            <button
              key={label}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tabValue === idx
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setTabValue(idx)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 交易查询 */}
        {tabValue === 0 && (
          <div>
            <div className="flex items-center gap-4">
              <Input
                value={txHash}
                onChange={(val) => setTxHash(String(val))}
                onKeydown={(_value: string, { e }: { e: React.KeyboardEvent }) => { if (e.key === 'Enter') handleTxQuery(); }}
                placeholder="0x..."
                style={{ minWidth: 400 }}
              />
              <Button
                theme="primary"
                icon={txMutation.isPending ? <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <SearchIcon />}
                onClick={handleTxQuery}
                disabled={!txHash.trim() || txMutation.isPending}
              >
                查询
              </Button>
            </div>
            {txMutation.isError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                查询失败: {(txMutation.error as any)?.message || '交易未找到或区块链服务不可用'}
              </div>
            )}
            {renderResultCard('交易详情', txResult)}
          </div>
        )}

        {/* 区块查询 */}
        {tabValue === 1 && (
          <div>
            <div className="flex items-center gap-4">
              <Input
                value={blockNumber}
                onChange={(val) => setBlockNumber(String(val))}
                onKeydown={(_value: string, { e }: { e: React.KeyboardEvent }) => { if (e.key === 'Enter') handleBlockQuery(); }}
                placeholder="12345678"
                style={{ minWidth: 400 }}
              />
              <Button
                theme="primary"
                icon={blockMutation.isPending ? <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <SearchIcon />}
                onClick={handleBlockQuery}
                disabled={!blockNumber.trim() || blockMutation.isPending}
              >
                查询
              </Button>
            </div>
            {blockMutation.isError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                查询失败: {(blockMutation.error as any)?.message || '区块未找到或区块链服务不可用'}
              </div>
            )}
            {renderResultCard('区块信息', blockResult)}
          </div>
        )}

        {/* 合约查询 */}
        {tabValue === 2 && (
          <div>
            <div className="flex items-center gap-4">
              <Input
                value={contractAddress}
                onChange={(val) => setContractAddress(String(val))}
                onKeydown={(_value: string, { e }: { e: React.KeyboardEvent }) => { if (e.key === 'Enter') handleContractQuery(); }}
                placeholder="0x..."
                style={{ minWidth: 400 }}
              />
              <Button
                theme="primary"
                icon={contractMutation.isPending ? <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <SearchIcon />}
                onClick={handleContractQuery}
                disabled={!contractAddress.trim() || contractMutation.isPending}
              >
                查询
              </Button>
            </div>
            {contractMutation.isError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                查询失败: {(contractMutation.error as any)?.message || '合约未找到或区块链服务不可用'}
              </div>
            )}
            {renderResultCard('合约信息', contractResult)}
          </div>
        )}
      </div>
    </div>
  );
};

export default BcQueryPage;
