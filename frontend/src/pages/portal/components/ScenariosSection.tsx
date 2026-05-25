/**
 * ScenariosSection - 典型应用场景区域
 * 4个场景卡片，左右交替布局
 */
import React from 'react';

/* ===== 场景数据 ===== */
const SCENARIOS = [
  {
    icon: '⚡',
    title: '电网调度数据共享',
    desc: '基于隐私计算技术，实现电网调度数据在保障安全前提下的跨部门、跨区域共享，提升电网运行效率和可靠性。',
    points: [
      '调度数据安全共享',
      '多级调度协同优化',
      '实时负荷预测分析',
    ],
    color: '#165DFF',
  },
  {
    icon: '☀️',
    title: '新能源消纳分析',
    desc: '融合气象、电网、发电等多源数据，构建新能源消纳分析模型，提升新能源并网消纳水平。',
    points: [
      '风光功率精准预测',
      '消纳能力动态评估',
      '弃电预警与优化',
    ],
    color: '#00B42A',
  },
  {
    icon: '🏭',
    title: '虚拟电厂运营',
    desc: '聚合分布式能源资源，通过数据驱动实现虚拟电厂的智能调度和市场化运营。',
    points: [
      '分布式资源聚合管理',
      '需求响应智能调度',
      '电力市场参与结算',
    ],
    color: '#0FC6C2',
  },
  {
    icon: '💹',
    title: '电力交易结算',
    desc: '基于区块链的电力交易结算系统，实现交易数据可信存证、智能合约自动执行。',
    points: [
      '交易数据链上存证',
      '智能合约自动结算',
      '多方对账高效协同',
    ],
    color: '#722ED1',
  },
];

/* ============================================================
 * ScenariosSection 主组件
 * ============================================================ */
const ScenariosSection: React.FC = () => {
  return (
    <section id="scenarios" className="py-16 md:py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="section-title">典型应用场景</h2>
          <p className="section-subtitle">
            深入能源行业核心业务，提供安全可信的数据流通解决方案
          </p>
        </div>

        <div className="space-y-12">
          {SCENARIOS.map((scenario, index) => (
            <div
              key={scenario.title}
              className={`flex flex-col ${index % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'} gap-8 items-center`}
            >
              {/* 图标区域 */}
              <div className="w-full md:w-1/2">
                <div
                  className="w-full h-64 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${scenario.color}10` }}
                >
                  <span className="text-8xl">{scenario.icon}</span>
                </div>
              </div>

              {/* 内容区域 */}
              <div className="w-full md:w-1/2">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">
                  {scenario.title}
                </h3>
                <p className="text-gray-600 mb-6">
                  {scenario.desc}
                </p>
                <ul className="space-y-3">
                  {scenario.points.map((point) => (
                    <li key={point} className="flex items-center gap-3">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: scenario.color }}
                      />
                      <span className="text-gray-700">{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ScenariosSection;