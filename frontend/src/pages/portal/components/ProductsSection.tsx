/**
 * ProductsSection - 核心数据服务区域
 * 6个产品卡片，3列grid布局，每个链接到真实页面
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Tag } from 'tdesign-react';

const PRODUCTS = [
  { icon: '📋', title: '数据资产登记', desc: '提供数据资产的确权、登记、存证服务，保障数据资产的合法性和可追溯性。', color: '#165DFF', path: '/dashboard/data/assets', tag: '数据资源中心' },
  { icon: '🔐', title: '隐私计算服务', desc: '基于联邦学习、安全多方计算、同态加密等技术，实现数据"可用不可见"。', color: '#00B42A', path: '/dashboard/compute/tasks', tag: '可信计算中心' },
  { icon: '⛓️', title: '区块链存证', desc: '利用区块链不可篡改特性，为数据交易、操作审计提供可信存证服务。', color: '#0FC6C2', path: '/dashboard/blockchain/evidence', tag: '区块链存证中心' },
  { icon: '📝', title: '智能合约管理', desc: '支持数据交易、结算、分润等业务的智能合约编写、部署和自动化执行。', color: '#722ED1', path: '/dashboard/blockchain/contracts', tag: '区块链存证中心' },
  { icon: '📊', title: '数据质量评估', desc: '提供数据完整性、准确性、一致性、时效性等多维度质量评估和监控。', color: '#F5A623', path: '/dashboard/data/quality', tag: '数据资源中心' },
  { icon: '🤖', title: 'AI 智能助手', desc: '基于大语言模型的智能对话助手，支持数据查询、安全分析、合规检查。', color: '#F5222D', path: '/agent/chat', tag: 'AI Agent' },
];

const ProductsSection: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section id="products" className="py-16 md:py-24">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="section-title">核心数据服务</h2>
          <p className="section-subtitle">提供数据全生命周期服务，覆盖数据资源、可信计算、区块链存证、运营管理四大中心</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PRODUCTS.map((product) => (
            <div
              key={product.title}
              className="card-hover bg-white rounded-xl p-6 cursor-pointer border border-gray-100 group"
              onClick={() => navigate(product.path)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl" style={{ backgroundColor: `${product.color}15` }}>
                  {product.icon}
                </div>
                <Tag size="small" variant="light" className="opacity-0 group-hover:opacity-100 transition-opacity">{product.tag}</Tag>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{product.title}</h3>
              <p className="text-gray-600 text-sm mb-4 line-clamp-2">{product.desc}</p>
              <span className="text-sm font-medium transition-colors duration-200" style={{ color: product.color }}>
                了解更多 →
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ProductsSection;
