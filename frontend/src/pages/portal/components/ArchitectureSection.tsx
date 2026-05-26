/**
 * ArchitectureSection - 平台架构展示区域
 * 一门户 · 五中心 架构图 + 技术栈标签 + 数据流
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import {
  HardDiskStorageIcon, CloudIcon, LinkIcon,
  UsergroupIcon, LockOnIcon, DashboardIcon, RocketIcon,
} from 'tdesign-icons-react';

const CENTERS = [
  { icon: <HardDiskStorageIcon />, title: '数据资源中心', desc: '数据采集接入、分类分级、元数据管理、数据质量控制、数据目录发布', color: '#1976d2', path: '/dashboard/data/sources', tech: ['PostgreSQL', 'MinIO', 'Elasticsearch'] },
  { icon: <CloudIcon />, title: '可信计算中心', desc: '联邦学习、安全多方计算、可信执行环境、同态加密、差分隐私', color: '#2e7d32', path: '/dashboard/compute/tasks', tech: ['FATE', 'TenSEAL', 'SPDZ'] },
  { icon: <LinkIcon />, title: '区块链存证中心', desc: '数据资产确权、全流程操作存证、智能合约结算、链上溯源', color: '#ed6c02', path: '/dashboard/blockchain/assets', tech: ['FISCO BCOS', 'Solidity', 'IPFS'] },
  { icon: <UsergroupIcon />, title: '运营管理中心', desc: '用户管理、服务目录、计费管理、合规审计、运营监控', color: '#7b1fa2', path: '/dashboard/ops/users', tech: ['RBAC', 'ABAC', 'DID'] },
  { icon: <LockOnIcon />, title: '安全管控中心', desc: 'DID身份认证、VC凭证管理、密钥管理、零知识证明、国密算法', color: '#d32f2f', path: '/dashboard/security/policies', tech: ['SM2/3/4', 'ZKP', 'HSM'] },
];

const TECH_STACK = [
  { label: 'FastAPI', color: '#009688' },
  { label: 'Vue 3', color: '#42b883' },
  { label: 'React', color: '#61dafb' },
  { label: 'PostgreSQL', color: '#336791' },
  { label: 'Redis', color: '#dc382d' },
  { label: 'FISCO BCOS', color: '#ed6c02' },
  { label: 'TenSEAL', color: '#2e7d32' },
  { label: 'SM2/3/4', color: '#d32f2f' },
  { label: 'Docker', color: '#2496ed' },
  { label: 'MQTT', color: '#660066' },
];

const ArchitectureSection: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section id="architecture" className="py-16 md:py-24">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-10">
          <Tag>平台架构</Tag>
          <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">一门户 · 五中心</h3>
          <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
            覆盖能源数据全生命周期的六大核心能力模块，构建"可信采集-安全传输-可控使用-可溯监管"全链路安全体系
          </p>
        </div>

        {/* 架构层级图 */}
        <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-6 md:p-8 mb-6" style={{ background: 'linear-gradient(180deg, #f8fbff 0%, #fff 100%)' }}>
          {/* 门户层 */}
          <div className="text-center mb-6 py-4 rounded-lg bg-blue-50 border border-blue-100">
            <h3 className="text-base font-semibold text-gray-800 flex items-center justify-center gap-2">
              <DashboardIcon className="text-blue-600" />
              统一门户 — 唯一访问入口
            </h3>
            <span className="text-sm text-gray-600 mt-1 block">统一身份认证 · 多角色权限路由 · 数据服务市场 · 监管大屏</span>
          </div>

          {/* 数据流箭头 */}
          <div className="text-center text-gray-300 text-2xl mb-4">▼ ▼ ▼</div>

          {/* 五中心 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            {CENTERS.map((c) => (
              <div
                key={c.title}
                className="rounded-lg bg-white border-2 p-4 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-md group"
                style={{ borderColor: `${c.color}33` }}
                onClick={() => navigate(c.path)}
              >
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg mb-3" style={{ backgroundColor: `${c.color}15`, color: c.color }}>
                  {c.icon}
                </div>
                <span className="font-bold text-gray-800 block mb-1">{c.title}</span>
                <span className="text-xs text-gray-600 block mb-2">{c.desc}</span>
                {/* 技术栈标签 */}
                <div className="flex flex-wrap gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  {c.tech.map(t => <Tag key={t} size="small" variant="light" className="text-[10px]">{t}</Tag>)}
                </div>
              </div>
            ))}
          </div>

          {/* 底部横条 */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 flex items-center gap-2">
              <LockOnIcon className="text-red-500" />
              <span className="text-sm text-gray-600">安全审计轨道 — 区块链全程存证</span>
            </div>
            <div className="flex-1 rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 flex items-center gap-2">
              <RocketIcon className="text-purple-600" />
              <span className="text-sm text-gray-600">AI 智能体轨道 — DeepSeek + LangChain</span>
            </div>
          </div>
        </div>

        {/* 技术栈 */}
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-3">核心技术栈</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {TECH_STACK.map(t => (
              <span key={t.label} className="px-3 py-1 rounded-full text-xs font-medium border" style={{ color: t.color, borderColor: `${t.color}40`, backgroundColor: `${t.color}08` }}>
                {t.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default ArchitectureSection;
