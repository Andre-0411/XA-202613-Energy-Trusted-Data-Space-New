/**
 * ProductsSection - 核心数据服务区域
 * 6个产品卡片，3列grid布局
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';

/* ===== 产品数据 ===== */
const PRODUCTS = [
  {
    icon: '📋',
    title: '数据资产登记',
    desc: '提供数据资产的确权、登记、存证服务，保障数据资产的合法性和可追溯性。',
    color: '#165DFF',
  },
  {
    icon: '🔐',
    title: '隐私计算服务',
    desc: '基于联邦学习、安全多方计算等技术，实现数据"可用不可见"的安全计算。',
    color: '#00B42A',
  },
  {
    icon: '⛓️',
    title: '区块链存证',
    desc: '利用区块链不可篡改特性，为数据交易、操作审计提供可信存证服务。',
    color: '#0FC6C2',
  },
  {
    icon: '📝',
    title: '智能合约管理',
    desc: '支持数据交易、结算、分润等业务的智能合约编写、部署和执行。',
    color: '#722ED1',
  },
  {
    icon: '📊',
    title: '数据质量评估',
    desc: '提供数据完整性、准确性、一致性等多维度质量评估和监控服务。',
    color: '#F5A623',
  },
  {
    icon: '🤝',
    title: '供需智能撮合',
    desc: '基于AI算法智能匹配数据供需双方，提高数据流通效率和精准度。',
    color: '#F5222D',
  },
];

/* ============================================================
 * ProductsSection 主组件
 * ============================================================ */
const ProductsSection: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section id="products" className="py-16 md:py-24">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="section-title">核心数据服务</h2>
          <p className="section-subtitle">
            提供数据全生命周期服务，保障数据安全、可信、高效流通
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PRODUCTS.map((product) => (
            <div
              key={product.title}
              className="card-hover bg-white rounded-xl p-6 cursor-pointer border border-gray-100"
              onClick={() => navigate('/dashboard/data/catalog')}
            >
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl mb-4"
                style={{ backgroundColor: `${product.color}15` }}
              >
                {product.icon}
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {product.title}
              </h3>
              <p className="text-gray-600 text-sm mb-4">
                {product.desc}
              </p>
              <a
                href="#"
                className="text-sm font-medium transition-colors duration-200"
                style={{ color: product.color }}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  navigate('/dashboard/data/catalog');
                }}
              >
                了解更多 →
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ProductsSection;