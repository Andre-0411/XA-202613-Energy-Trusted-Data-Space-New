/**
 * ScenariosSection - 核心应用场景区域
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import {
  SunnyIcon, ServerIcon, InstitutionIcon, FlashlightIcon,
} from 'tdesign-icons-react';

/* ===== 应用场景 ===== */
const SCENARIOS = [
  {
    title: '新能源智能消纳',
    desc: '融合电网实时运行、气象预测、发电企业数据，构建"选址-并网-调控"全流程服务，提升新能源消纳率。',
    metrics: [
      { label: '装机用户数提升', value: '30%' },
      { label: '弃光率降低', value: '1%' },
      { label: '电压合格率提升', value: '10%' },
    ],
    color: '#2e7d32',
    icon: <SunnyIcon />,
  },
  {
    title: '设备智能运维',
    desc: '汇聚设备运行、缺陷记录、环境信息，为制造商提供真实运行反馈与协同研发支持。',
    metrics: [
      { label: '年节省成本', value: '1000万+' },
      { label: '设备故障率降低', value: '56%' },
      { label: '运维效率提升', value: '40%' },
    ],
    color: '#ed6c02',
    icon: <ServerIcon />,
  },
  {
    title: '电力数据赋能普惠金融',
    desc: '基于用电行为构建企业信用画像模型，将电表读数转化为信用读数，服务金融机构信贷决策。',
    metrics: [
      { label: '服务企业', value: '1000+' },
      { label: '授信金额', value: '16亿+' },
      { label: '不良率降低', value: '35%' },
    ],
    color: '#1976d2',
    icon: <InstitutionIcon />,
  },
  {
    title: '虚拟电厂协同调度',
    desc: '聚合分布式电源、储能、可控负荷，参与电网调峰调频和电力市场交易，实现源网荷储协同优化。',
    metrics: [
      { label: '调度响应时间', value: '<500ms' },
      { label: '消纳率提升', value: '≥3%' },
      { label: '参与方数量', value: '50+' },
    ],
    color: '#7b1fa2',
    icon: <FlashlightIcon />,
  },
];

/* ============================================================
 * ScenariosSection 主组件
 * ============================================================ */
const ScenariosSection: React.FC = () => {
  return (
    <section id="scenarios" className="py-16 md:py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-10">
          <Tag>应用场景</Tag>
          <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">核心应用场景</h3>
          <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
            围绕电网调度、新能源消纳、虚拟电厂运营、电力市场交易四大核心场景，提供安全可靠的数据要素支撑
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {SCENARIOS.map((s) => (
            <div
              key={s.title}
              className="rounded-xl bg-white border border-gray-200 transition-all duration-300 hover:-translate-y-1 hover:shadow-md overflow-visible"
            >
              <div className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
                    style={{ backgroundColor: `${s.color}18`, color: s.color }}
                  >
                    {s.icon}
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-gray-800">{s.title}</h3>
                    <span className="text-sm text-gray-600">{s.desc}</span>
                  </div>
                </div>
                <hr className="border-gray-200 my-4" />
                <div className="grid grid-cols-3 gap-4">
                  {s.metrics.map((m) => (
                    <div key={m.label} className="text-center">
                      <h2 className="text-xl font-semibold text-gray-800">{m.value}</h2>
                      <span className="text-xs text-gray-500">{m.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ScenariosSection;
