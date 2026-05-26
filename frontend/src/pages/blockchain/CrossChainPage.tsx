/**
 * 跨链互操作页面
 * 跨链概览/跨链交易/跨链桥管理/中继节点
 */
import React, { useState, useEffect } from 'react';
import { Button, Table, Tag, Dialog, Input, Select, Tabs, MessagePlugin, Row, Col, Card } from 'tdesign-react';
import { AddIcon, LinkIcon } from 'tdesign-icons-react';
import request from '@/api/request';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';

const STATUS_MAP: Record<string, { label: string; theme: string }> = {
  confirmed: { label: '已确认', theme: 'success' }, pending: { label: '待确认', theme: 'warning' },
  failed: { label: '失败', theme: 'danger' }, active: { label: '在线', theme: 'success' },
  syncing: { label: '同步中', theme: 'warning' }, inactive: { label: '离线', theme: 'default' },
};

const CrossChainPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [homeBreadcrumb, { label: '区块链中心' }, { label: '跨链互操作' }];
  const [tab, setTab] = useState('overview');
  const [txs] = useState([
    { id: '1', hash: '0xa3f8...7d2e', source_chain: 'FISCO BCOS', target_chain: '以太坊', type: '数据存证', status: 'confirmed', time: '2026-05-26 10:30' },
    { id: '2', hash: '0xb7c1...4f9a', source_chain: '蚂蚁链', target_chain: 'FISCO BCOS', type: '资产转移', status: 'pending', time: '2026-05-26 10:25' },
    { id: '3', hash: '0xd2e5...8b3c', source_chain: '以太坊', target_chain: 'FISCO BCOS', type: '身份验证', status: 'confirmed', time: '2026-05-26 10:20' },
    { id: '4', hash: '0xe9f0...1a6d', source_chain: 'FISCO BCOS', target_chain: '蚂蚁链', type: '数据存证', status: 'failed', time: '2026-05-26 10:15' },
  ]);
  const [chains] = useState([
    { id: '1', name: 'FISCO BCOS', type: '联盟链', status: 'active', block_height: 12580, last_sync: '1分钟前' },
    { id: '2', name: '以太坊测试网', type: '公有链', status: 'active', block_height: 5823410, last_sync: '3分钟前' },
    { id: '3', name: '蚂蚁链', type: '联盟链', status: 'syncing', block_height: 892340, last_sync: '5分钟前' },
  ]);
  const [bridges] = useState([
    { id: '1', name: 'FISCO-ETH桥', chain_a: 'FISCO BCOS', chain_b: '以太坊测试网', status: 'active', volume: 1560 },
    { id: '2', name: 'FISCO-蚂蚁桥', chain_a: 'FISCO BCOS', chain_b: '蚂蚁链', status: 'active', volume: 890 },
  ]);
  const [relays] = useState([
    { id: '1', name: '主中继节点', address: '10.241.2.64:8545', status: 'active', latency: '12ms', tx_count: 2340 },
    { id: '2', name: '备用中继-1', address: '10.241.2.65:8545', status: 'active', latency: '18ms', tx_count: 1205 },
    { id: '3', name: '备用中继-2', address: '10.241.2.66:8545', status: 'inactive', latency: '-', tx_count: 0 },
  ]);

  const [stats] = useState({ connected_chains: 3, cross_txs: 4450, success_rate: 99.2, avg_latency: '15ms' });

  const txColumns = [
    { title: '交易哈希', colKey: 'hash', width: 160, cell: ({ row }: any) => <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{row.hash}</code> },
    { title: '源链 → 目标链', colKey: 'source_chain', width: 220, cell: ({ row }: any) => (
      <div className="flex items-center gap-2"><Tag size="small">{row.source_chain}</Tag><span>→</span><Tag size="small">{row.target_chain}</Tag></div>
    )},
    { title: '类型', colKey: 'type', width: 100, cell: ({ row }: any) => <Tag variant="light">{row.type}</Tag> },
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => { const s = STATUS_MAP[row.status] || { label: row.status, theme: 'default' }; return <Tag theme={s.theme as any} variant="light">{s.label}</Tag>; } },
    { title: '时间', colKey: 'time', width: 150 },
    { title: '操作', colKey: 'action', width: 80, cell: () => <Button size="small" variant="text">详情</Button> },
  ];

  const chainColumns = [
    { title: '链名称', colKey: 'name', width: 160, cell: ({ row }: any) => <div className="flex items-center gap-2"><LinkIcon /><span className="font-medium">{row.name}</span></div> },
    { title: '类型', colKey: 'type', width: 100, cell: ({ row }: any) => <Tag variant="light">{row.type}</Tag> },
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => <Tag theme={STATUS_MAP[row.status]?.theme as any || 'default'} variant="light">{STATUS_MAP[row.status]?.label || row.status}</Tag> },
    { title: '区块高度', colKey: 'block_height', width: 150, cell: ({ row }: any) => <span className="font-mono">{row.block_height.toLocaleString()}</span> },
    { title: '最后同步', colKey: 'last_sync', width: 120 },
  ];

  const bridgeColumns = [
    { title: '桥名称', colKey: 'name', width: 160 },
    { title: '连接链', colKey: 'chain_a', width: 250, cell: ({ row }: any) => (
      <div className="flex items-center gap-2"><Tag>{row.chain_a}</Tag><span>⇄</span><Tag>{row.chain_b}</Tag></div>
    )},
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => <Tag theme={row.status === 'active' ? 'success' : 'default'} variant="light">{STATUS_MAP[row.status]?.label || row.status}</Tag> },
    { title: '累计交易量', colKey: 'volume', width: 120, cell: ({ row }: any) => <span className="font-semibold">{row.volume.toLocaleString()}</span> },
  ];

  const relayColumns = [
    { title: '节点名称', colKey: 'name', width: 160 },
    { title: '地址', colKey: 'address', width: 180, cell: ({ row }: any) => <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{row.address}</code> },
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => <Tag theme={row.status === 'active' ? 'success' : 'default'} variant="light">{STATUS_MAP[row.status]?.label || row.status}</Tag> },
    { title: '延迟', colKey: 'latency', width: 80 },
    { title: '处理交易数', colKey: 'tx_count', width: 120, cell: ({ row }: any) => <span className="font-semibold">{row.tx_count.toLocaleString()}</span> },
  ];

  return (
    <PageContainer>
      <PageHeader title="跨链互操作" breadcrumbs={breadcrumbs} />
      <Tabs value={tab} onChange={(v) => setTab(v as string)}>
        <Tabs.TabPanel value="overview" label="跨链概览">
          <Row gutter={16} className="mb-4">
            {[
              { label: '已连接链', value: stats.connected_chains, color: '#165DFF', icon: '🔗' },
              { label: '跨链交易', value: stats.cross_txs, color: '#0FC6C2', icon: '💱' },
              { label: '成功率', value: `${stats.success_rate}%`, color: '#00B42A', icon: '✅' },
              { label: '平均延迟', value: stats.avg_latency, color: '#FF7D00', icon: '⚡' },
            ].map((item, i) => (
              <Col key={i} span={3}>
                <Card className="text-center py-4">
                  <div className="text-2xl mb-1">{item.icon}</div>
                  <div className="text-2xl font-bold" style={{ color: item.color }}>{item.value}</div>
                  <div className="text-sm text-gray-500">{item.label}</div>
                </Card>
              </Col>
            ))}
          </Row>
          <h3 className="text-lg font-semibold mb-3">已连接区块链网络</h3>
          <Table data={chains} columns={chainColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="transactions" label="跨链交易">
          <h3 className="text-lg font-semibold mb-3">跨链交易记录</h3>
          <Table data={txs} columns={txColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="bridges" label="跨链桥管理">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold">跨链桥</h3>
            <Button theme="primary" icon={<AddIcon />}>创建跨链桥</Button>
          </div>
          <Table data={bridges} columns={bridgeColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="relays" label="中继节点">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold">中继节点</h3>
            <Button theme="primary" icon={<AddIcon />}>添加节点</Button>
          </div>
          <Table data={relays} columns={relayColumns} rowKey="id" bordered />
        </Tabs.TabPanel>
      </Tabs>
    </PageContainer>
  );
};

export default CrossChainPage;
