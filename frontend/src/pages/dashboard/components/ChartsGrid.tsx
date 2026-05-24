/**
 * ChartsGrid - 仪表盘图表网格区域
 * 渲染角色配置的 ECharts 图表
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import ReactECharts from 'echarts-for-react';

/* ===== Props ===== */
interface ChartWidget {
  id: string;
  title: string;
  icon: React.ReactNode;
  chipLabel: string;
  option: Record<string, unknown>;
}

interface ChartsGridProps {
  chartWidgets: ChartWidget[];
  chartHeight: number;
}

/* ============================================================
 * ChartsGrid 主组件
 * ============================================================ */
const ChartsGrid: React.FC<ChartsGridProps> = ({ chartWidgets, chartHeight }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6">
      {chartWidgets.map((chart) => (
        <div key={chart.id} className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2 m-0">
              {chart.icon}
              {chart.title}
            </h3>
            <Tag variant="outline">{chart.chipLabel}</Tag>
          </div>
          <ReactECharts option={chart.option} style={{ height: chartHeight }} />
        </div>
      ))}
    </div>
  );
};

export default ChartsGrid;
