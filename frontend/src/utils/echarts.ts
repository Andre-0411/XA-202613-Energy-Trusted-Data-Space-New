/**
 * ECharts 按需引入注册模块
 * 仅引入项目中实际使用的图表类型和组件，
 * 有效减少打包体积。
 */
import * as echarts from 'echarts/core';

/* ---------- 图表类型 ---------- */
import { BarChart } from 'echarts/charts';
import { LineChart } from 'echarts/charts';
import { PieChart } from 'echarts/charts';
import { GaugeChart } from 'echarts/charts';

/* ---------- 组件 ---------- */
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components';

/* ---------- 渲染器 ---------- */
import { CanvasRenderer } from 'echarts/renderers';

/* ---------- 注册 ---------- */
echarts.use([
  // 图表
  BarChart,
  LineChart,
  PieChart,
  GaugeChart,
  // 组件
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  // 渲染器
  CanvasRenderer,
]);

export default echarts;
