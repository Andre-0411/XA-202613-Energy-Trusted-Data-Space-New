/**
 * ProductsSection - 数据产品与服务区域
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import {
  FlashlightIcon, SunnyIcon, ThunderIcon,
  ServerIcon, InstitutionIcon, PlantumlIcon,
} from 'tdesign-icons-react';

/* ===== 数据产品 ===== */
const DATA_PRODUCTS = [
  {
    icon: <FlashlightIcon />,
    title: '电网运行数据',
    desc: '输变电设备运行状态、负荷数据、电网拓扑、调度指令等核心电网数据',
    count: '42项',
    color: '#1976d2',
  },
  {
    icon: <SunnyIcon />,
    title: '新能源数据',
    desc: '风电/光伏发电功率预测、气象数据、消纳分析、并网运行数据',
    count: '28项',
    color: '#2e7d32',
  },
  {
    icon: <ThunderIcon />,
    title: '气象环境数据',
    desc: '风速风向、辐照度、温度湿度、降水预报、极端天气预警',
    count: '18项',
    color: '#0288d1',
  },
  {
    icon: <ServerIcon />,
    title: '设备状态数据',
    desc: '变压器、开关柜、换流阀等设备的运行参数、缺陷记录、检修数据',
    count: '25项',
    color: '#ed6c02',
  },
  {
    icon: <InstitutionIcon />,
    title: '电力市场数据',
    desc: '电价行情、交易量、市场供需、结算数据、碳排放配额',
    count: '15项',
    color: '#7b1fa2',
  },
  {
    icon: <PlantumlIcon />,
    title: '碳管理数据',
    desc: '碳排放核算、碳足迹追踪、绿证交易、碳中和路径分析',
    count: '21项',
    color: '#00897b',
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
        <div className="text-center mb-10">
          <Tag>数据服务</Tag>
          <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">数据产品与服务</h3>
          <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
            覆盖电力、能源及跨行业数据融合应用，提供160余项标准化数据资源，支持即插即用
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {DATA_PRODUCTS.map((p) => (
            <div
              key={p.title}
              className="rounded-xl bg-white border border-gray-200 cursor-pointer transition-all duration-300 hover:-translate-y-1.5 hover:shadow-lg group"
              onClick={() => navigate('/dashboard/data/catalog')}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-3">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-xl transition-all duration-300 group-hover:text-white"
                    style={{ backgroundColor: `${p.color}18`, color: p.color }}
                  >
                    {p.icon}
                  </div>
                  <Tag>{p.count}</Tag>
                </div>
                <h3 className="text-base font-semibold text-gray-800 mb-1">{p.title}</h3>
                <span className="text-sm text-gray-600">{p.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ProductsSection;
