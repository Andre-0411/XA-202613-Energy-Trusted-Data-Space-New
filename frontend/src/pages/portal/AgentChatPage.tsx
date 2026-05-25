/**
 * AI Agent 聊天页面（完整重写）
 * 支持四大Agent切换、流式打字机效果、Markdown渲染、工具调用展示、ECharts数据可视化
 * 左侧Agent选择+历史对话 | 中间聊天消息流 | 右侧能力说明+工具结果+图表
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Dialog, MessagePlugin } from 'tdesign-react';
import ReactECharts from 'echarts-for-react';
import {
  SendIcon, SearchIcon, DataBaseIcon, SwapIcon, FileSafetyIcon, ThunderIcon,
  RefreshIcon, ChatIcon, Robot1Icon, UserIcon,
  CopyIcon, CheckIcon, DownloadIcon, ChevronDownIcon,
  FileIcon, MoreIcon, DeleteIcon, AddIcon,
} from 'tdesign-icons-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer } from '@/components/common';

/* ========== 类型定义 ========== */
interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  duration?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agentType?: string;
  toolCalls?: ToolCall[];
  chart?: EChartOption;
  isStreaming?: boolean;
}

interface EChartOption {
  title?: string;
  option: Record<string, unknown>;
}

interface AgentInfo {
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  welcomeMessage: string;
  placeholder: string;
  capabilities: string[];
  tools: { name: string; description: string }[];
  suggestedQuestions: string[];
}

interface Conversation {
  id: string;
  agentType: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messageCount: number;
}

/* ========== Agent 配置 ========== */
const AGENTS: AgentInfo[] = [
  {
    key: 'query',
    label: '数据查询Agent',
    description: '数据资产检索与统计分析',
    icon: <DataBaseIcon />,
    color: '#1890ff',
    welcomeMessage: '你好！我是**数据查询Agent**，可以帮你：\n\n- 搜索数据资产目录\n- 查询数据集详情与统计\n- 分析数据分布趋势\n\n请问你想查询什么数据？',
    placeholder: '输入查询需求，例如：帮我查询所有新能源发电数据资产...',
    capabilities: ['数据资产检索', '数据目录查询', '数据统计分析', '数据血缘追踪'],
    tools: [
      { name: 'data_search', description: '全文检索数据资产' },
      { name: 'catalog_query', description: '查询数据目录结构' },
      { name: 'stats_query', description: '获取数据统计信息' },
    ],
    suggestedQuestions: [
      '帮我查询所有新能源发电数据资产',
      '查看数据目录中有哪些实时数据集',
      '统计本月新增的数据资产数量',
      '查询电网负荷数据的更新频率',
    ],
  },
  {
    key: 'trade',
    label: '交易撮合Agent',
    description: '供需匹配与合约结算',
    icon: <SwapIcon />,
    color: '#52c41a',
    welcomeMessage: '你好！我是**交易撮合Agent**，可以帮你：\n\n- 浏览数据产品市场\n- 进行供需智能匹配\n- 创建交易合约\n- 发起结算流程\n\n请问有什么交易需求？',
    placeholder: '输入交易需求，例如：帮我寻找光伏数据的供需匹配...',
    capabilities: ['供需智能匹配', '合约创建管理', '交易结算发起', '价格趋势分析'],
    tools: [
      { name: 'matching', description: '供需智能匹配' },
      { name: 'contract_create', description: '创建交易合约' },
      { name: 'settlement', description: '发起结算流程' },
    ],
    suggestedQuestions: [
      '帮我寻找光伏数据的供需匹配',
      '查看当前市场上热门的数据产品',
      '创建一份电力数据交易合约',
      '查询最近的交易结算状态',
    ],
  },
  {
    key: 'security',
    label: '安全审计Agent',
    description: '安全检查与合规审计',
    icon: <FileSafetyIcon />,
    color: '#ff4d4f',
    welcomeMessage: '你好！我是**安全审计Agent**，可以帮你：\n\n- 执行系统安全扫描\n- 进行合规性审计\n- 检测潜在安全威胁\n- 生成安全评估报告\n\n请问需要什么安全服务？',
    placeholder: '输入安全需求，例如：检查当前系统的安全状态...',
    capabilities: ['安全漏洞扫描', '合规性审计', '威胁实时检测', '隐私风险评估'],
    tools: [
      { name: 'security_scan', description: '系统安全扫描' },
      { name: 'compliance_check', description: '合规性检查' },
      { name: 'threat_detect', description: '威胁检测分析' },
    ],
    suggestedQuestions: [
      '检查当前系统的安全状态',
      '执行一次全面的合规性审计',
      '检测最近24小时的安全威胁',
      '评估数据隐私保护等级',
    ],
  },
  {
    key: 'dispatch',
    label: '调度优化Agent',
    description: '计算调度与资源优化',
    icon: <ThunderIcon />,
    color: '#722ed1',
    welcomeMessage: '你好！我是**调度优化Agent**，可以帮你：\n\n- 查看计算任务调度状态\n- 优化资源分配策略\n- 分析系统性能指标\n- 生成调度优化建议\n\n请问需要调度什么任务？',
    placeholder: '输入调度需求，例如：优化当前计算任务的调度策略...',
    capabilities: ['计算任务调度', '资源分配优化', '性能指标分析', '负载均衡策略'],
    tools: [
      { name: 'task_schedule', description: '计算任务调度' },
      { name: 'resource_optimize', description: '资源分配优化' },
      { name: 'perf_analyze', description: '性能指标分析' },
    ],
    suggestedQuestions: [
      '优化当前计算任务的调度策略',
      '查看集群资源使用情况',
      '分析最近一周的性能趋势',
      '生成资源扩容建议报告',
    ],
  },
];

/* ========== 模拟对话历史 ========== */
const MOCK_CONVERSATIONS: Conversation[] = [
  { id: 'conv-1', agentType: 'query', title: '查询新能源发电数据', lastMessage: '共找到12条匹配记录', timestamp: '2026-05-25 14:30', messageCount: 6 },
  { id: 'conv-2', agentType: 'trade', title: '光伏数据供需匹配', lastMessage: '已找到3个潜在买家', timestamp: '2026-05-25 11:20', messageCount: 8 },
  { id: 'conv-3', agentType: 'security', title: '系统安全状态检查', lastMessage: '安全状态良好，无威胁告警', timestamp: '2026-05-24 16:45', messageCount: 4 },
  { id: 'conv-4', agentType: 'dispatch', title: 'GPU资源优化建议', lastMessage: '建议扩容2个GPU节点', timestamp: '2026-05-24 10:15', messageCount: 6 },
  { id: 'conv-5', agentType: 'query', title: '气象环境数据检索', lastMessage: '已导出数据清单', timestamp: '2026-05-23 15:00', messageCount: 4 },
];

/* ========== 模拟对话数据（每个Agent 3-5轮） ========== */
const MOCK_DIALOGUES: Record<string, { role: 'user' | 'assistant'; content: string; toolCalls?: ToolCall[]; chart?: EChartOption }[]> = {
  query: [
    { role: 'user', content: '帮我查询所有新能源发电数据资产' },
    {
      role: 'assistant',
      content: '正在为你检索新能源发电相关数据资产，请稍候...',
      toolCalls: [
        { id: 'tc-q1', name: 'data_search', args: { keyword: '新能源发电', category: 'energy', time_range: 'all' }, result: '返回12条记录', duration: '1.2s' },
      ],
    },
    {
      role: 'assistant',
      content: '根据检索结果，共找到 **12** 条新能源发电数据资产，以下是详细列表：\n\n## 检索结果\n\n| 数据名称 | 数据类型 | 更新频率 | 安全等级 | 数据量 |\n|---------|---------|---------|---------|-------|\n| 光伏发电实时功率 | 实时流 | 秒级 | L3 | 2.3TB |\n| 风电场发电量统计 | 日报 | 每日 | L2 | 856GB |\n| 分布式光伏出力预测 | 小时报 | 每小时 | L2 | 1.2TB |\n| 集中式风电功率预测 | 小时报 | 每小时 | L3 | 980GB |\n| 新能源消纳统计数据 | 月报 | 每月 | L1 | 45GB |\n\n### 数据分布\n\n按类型统计：**光伏发电** 7项、**风力发电** 4项、**综合统计** 1项。',
      chart: {
        title: '新能源数据资产分布',
        option: {
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          legend: { orient: 'vertical', right: 10, top: 'center' },
          series: [{
            name: '数据类型',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
            label: { show: false },
            emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
            data: [
              { value: 7, name: '光伏发电', itemStyle: { color: '#2196f3' } },
              { value: 4, name: '风力发电', itemStyle: { color: '#4caf50' } },
              { value: 1, name: '综合统计', itemStyle: { color: '#ff9800' } },
            ],
          }],
        },
      },
    },
    { role: 'user', content: '光伏发电实时功率数据的具体字段有哪些？' },
    {
      role: 'assistant',
      content: '## 光伏发电实时功率 - 数据字段详情\n\n该数据集包含以下核心字段：\n\n### 基础信息字段\n- **plant_id** - 电站编号（唯一标识）\n- **plant_name** - 电站名称\n- **capacity_MW** - 装机容量（MW）\n- **location** - 地理坐标（经纬度）\n\n### 实时监测字段\n- **timestamp** - 采集时间戳（毫秒精度）\n- **active_power_MW** - 有功功率（MW）\n- **reactive_power_MVar** - 无功功率（MVar）\n- **voltage_kV** - 并网电压（kV）\n- **current_A** - 输出电流（A）\n\n### 环境参数\n- **irradiance_W_m2** - 辐照度（W/m²）\n- **panel_temp_C** - 组件温度（°C）\n- **ambient_temp_C** - 环境温度（°C）\n- **wind_speed_m_s** - 风速（m/s）\n\n### 质量标识\n- **data_quality** - 数据质量等级（A/B/C/D）\n- **is_anomaly** - 是否异常标记\n\n共 **16** 个字段，数据更新频率为**秒级**，支持API实时订阅。',
      toolCalls: [
        { id: 'tc-q2', name: 'catalog_query', args: { dataset_id: 'pv_realtime_power', detail: 'schema' }, result: '返回16个字段定义', duration: '0.8s' },
      ],
    },
  ],
  trade: [
    { role: 'user', content: '帮我寻找光伏数据的供需匹配' },
    {
      role: 'assistant',
      content: '正在为你分析光伏数据的供需情况，请稍候...',
      toolCalls: [
        { id: 'tc-t1', name: 'matching', args: { data_type: 'photovoltaic', match_mode: 'smart' }, result: '找到3组匹配', duration: '2.1s' },
      ],
    },
    {
      role: 'assistant',
      content: '## 供需匹配结果\n\n已为你找到 **3** 组高匹配度的供需对：\n\n### 匹配1：光伏发电预测数据 ⭐ 最佳匹配\n- **供应方**：华能新能源科技有限公司\n- **需求方**：国网电力交易中心\n- **匹配度**：95.2%\n- **数据内容**：华东地区光伏电站72小时发电预测\n- **预估价格**：¥1,200/月\n\n### 匹配2：光伏组件监测数据\n- **供应方**：隆基绿能科技股份有限公司\n- **需求方**：清华大学能源互联网研究院\n- **匹配度**：87.6%\n- **数据内容**：光伏组件IV曲线与温度监测\n- **预估价格**：¥800/月\n\n### 匹配3：分布式光伏出力数据\n- **供应方**：天合光能股份有限公司\n- **需求方**：南方电网科学研究院\n- **匹配度**：82.1%\n- **数据内容**：广东地区分布式光伏实时出力\n- **预估价格**：¥650/月\n\n需要我为你创建交易合约吗？',
      chart: {
        title: '供需匹配度对比',
        option: {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          yAxis: { type: 'category', data: ['分布式光伏出力', '光伏组件监测', '光伏发电预测'] },
          series: [{
            name: '匹配度',
            type: 'bar',
            data: [
              { value: 82.1, itemStyle: { color: '#ff9800' } },
              { value: 87.6, itemStyle: { color: '#2196f3' } },
              { value: 95.2, itemStyle: { color: '#4caf50' } },
            ],
            barWidth: 24,
            label: { show: true, position: 'right', formatter: '{c}%' },
          }],
        },
      },
    },
    { role: 'user', content: '帮我对匹配1创建交易合约' },
    {
      role: 'assistant',
      content: '正在为你创建交易合约...',
      toolCalls: [
        { id: 'tc-t2', name: 'contract_create', args: { match_id: 'match-001', buyer: 'grid_exchange', seller: 'huanneng', data_product: 'pv_forecast_72h', price: 1200, period: 'monthly' }, result: '合约创建成功', duration: '3.5s' },
      ],
    },
    {
      role: 'assistant',
      content: '## 合约创建成功 ✅\n\n交易合约已创建，详情如下：\n\n### 合约信息\n- **合约编号**：`TC-2026-0525-001`\n- **创建时间**：2026-05-25 14:32:15\n- **合约状态**：待双方确认\n\n### 交易详情\n- **供应方**：华能新能源科技有限公司\n- **需求方**：国网电力交易中心\n- **数据产品**：华东地区光伏电站72小时发电预测\n- **交易价格**：¥1,200/月\n- **结算周期**：月结\n- **数据交付方式**：API实时推送\n\n### 后续流程\n1. 📋 双方确认合约条款\n2. 💰 需求方预付首月费用\n3. 🔗 供应方开通数据接口\n4. ✅ 数据交付验收\n\n> 合约已发送至双方邮箱，请等待确认。',
    },
  ],
  security: [
    { role: 'user', content: '检查当前系统的安全状态' },
    {
      role: 'assistant',
      content: '正在执行全面安全扫描，请稍候...',
      toolCalls: [
        { id: 'tc-s1', name: 'security_scan', args: { scope: 'full', include_network: true, include_data: true }, result: '扫描完成', duration: '5.8s' },
      ],
    },
    {
      role: 'assistant',
      content: '## 安全扫描报告\n\n### 整体评估\n- **安全等级**：🟢 良好\n- **风险评分**：92/100\n- **扫描时间**：2026-05-25 15:00:23\n\n### 扫描结果概览\n\n| 检查项 | 状态 | 说明 |\n|-------|------|------|\n| 网络安全 | ✅ 通过 | 防火墙规则正常，无异常端口开放 |\n| 数据加密 | ✅ 通过 | 传输加密TLS 1.3，存储加密AES-256 |\n| 访问控制 | ⚠️ 警告 | 3个账户密码超过90天未更新 |\n| 漏洞扫描 | ✅ 通过 | 未发现高危漏洞 |\n| 日志审计 | ✅ 通过 | 审计日志完整，保留期满足要求 |\n| 合规检查 | ✅ 通过 | 符合等保三级要求 |\n\n### 待处理事项\n- ⚠️ 建议更新3个过期密码账户\n- ℹ️ 下次例行扫描时间：2026-06-01',
      chart: {
        title: '安全检查项评分',
        option: {
          radar: {
            indicator: [
              { name: '网络安全', max: 100 },
              { name: '数据加密', max: 100 },
              { name: '访问控制', max: 100 },
              { name: '漏洞管理', max: 100 },
              { name: '日志审计', max: 100 },
              { name: '合规性', max: 100 },
            ],
          },
          series: [{
            type: 'radar',
            data: [{
              value: [98, 96, 82, 95, 94, 97],
              name: '安全评分',
              areaStyle: { color: 'rgba(244, 67, 54, 0.15)' },
              lineStyle: { color: '#f44336' },
              itemStyle: { color: '#f44336' },
            }],
          }],
        },
      },
    },
    { role: 'user', content: '对访问控制警告进行详细分析' },
    {
      role: 'assistant',
      content: '正在对访问控制问题进行深入分析...',
      toolCalls: [
        { id: 'tc-s2', name: 'compliance_check', args: { check_type: 'access_control', detail: true }, result: '发现3个问题', duration: '2.3s' },
      ],
    },
    {
      role: 'assistant',
      content: '## 访问控制详细分析\n\n### 问题账户列表\n\n| 账户名 | 部门 | 密码龄期 | 最后登录 | 风险等级 |\n|-------|------|---------|---------|----------|\n| zhang_dev | 研发部 | 127天 | 2026-05-24 | 中 |\n| li_ops | 运维部 | 98天 | 2026-05-25 | 中 |\n| wang_test | 测试部 | 95天 | 2026-05-20 | 低 |\n\n### 安全建议\n\n1. **立即处理**（高优先级）\n   - 强制要求上述3个账户更新密码\n   - 启用密码复杂度策略（最少12位，含大小写+数字+特殊字符）\n\n2. **短期优化**（一周内）\n   - 启用多因素认证（MFA）\n   - 配置密码过期自动提醒（提前15天）\n\n3. **长期策略**\n   - 实施最小权限原则\n   - 定期审查账户权限（每季度一次）\n   - 建立账户生命周期管理流程',
    },
  ],
  dispatch: [
    { role: 'user', content: '优化当前计算任务的调度策略' },
    {
      role: 'assistant',
      content: '正在分析当前集群资源使用情况和任务调度状态...',
      toolCalls: [
        { id: 'tc-d1', name: 'task_schedule', args: { action: 'analyze', cluster: 'main' }, result: '分析完成', duration: '3.2s' },
        { id: 'tc-d2', name: 'resource_optimize', args: { scope: 'cluster', strategy: 'balanced' }, result: '生成优化方案', duration: '2.8s' },
      ],
    },
    {
      role: 'assistant',
      content: '## 调度优化分析报告\n\n### 当前集群状态\n\n| 资源类型 | 总量 | 已用 | 使用率 | 状态 |\n|---------|------|------|--------|------|\n| CPU | 256核 | 172核 | 67.2% | 正常 |\n| 内存 | 512GB | 276GB | 53.9% | 正常 |\n| GPU | 32卡 | 26卡 | 81.3% | 紧张 |\n| 存储 | 100TB | 68TB | 68.0% | 正常 |\n\n### 运行任务概况\n- **运行中任务**：12个\n- **排队等待任务**：3个\n- **平均任务时长**：4.2小时\n- **任务失败率**：2.1%\n\n### 优化建议\n\n1. **GPU资源优化**\n   - 将低优先级GPU任务调度至夜间执行\n   - 预计可释放 **6张GPU** 资源\n\n2. **CPU任务重排**\n   - 合并3个轻量级任务至同一节点\n   - 预计可减少 **15%** 的调度开销\n\n3. **队列优先级调整**\n   - 将实时数据处理任务设为最高优先级\n   - 批量分析任务设置资源上限',
      chart: {
        title: '集群资源使用率',
        option: {
          tooltip: { trigger: 'axis' },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: ['CPU', '内存', 'GPU', '存储'] },
          yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          series: [
            {
              name: '使用率',
              type: 'bar',
              data: [
                { value: 67.2, itemStyle: { color: '#4caf50' } },
                { value: 53.9, itemStyle: { color: '#2196f3' } },
                { value: 81.3, itemStyle: { color: '#f44336' } },
                { value: 68.0, itemStyle: { color: '#ff9800' } },
              ],
              barWidth: 40,
              label: { show: true, position: 'top', formatter: '{c}%' },
            },
          ],
        },
      },
    },
    { role: 'user', content: '执行GPU任务调度优化' },
    {
      role: 'assistant',
      content: '正在执行GPU任务调度优化方案...',
      toolCalls: [
        { id: 'tc-d3', name: 'task_schedule', args: { action: 'reorder', target: 'gpu', strategy: 'night_batch' }, result: '调度优化执行完成', duration: '4.5s' },
      ],
    },
    {
      role: 'assistant',
      content: '## GPU调度优化执行完成 ✅\n\n### 执行结果\n\n| 操作 | 详情 | 状态 |\n|------|------|------|\n| 任务迁移 | 3个低优先级任务移至夜间队列 | ✅ 完成 |\n| 资源释放 | 释放6张GPU（A100 80GB） | ✅ 完成 |\n| 优先级调整 | 实时处理任务设为P0 | ✅ 完成 |\n\n### 优化前后对比\n\n- **GPU使用率**：81.3% → 62.5%（↓18.8%）\n- **排队任务**：3个 → 0个\n- **预估节省成本**：¥2,400/天\n\n### 生效时间\n优化策略已立即生效，夜间批量任务将在 22:00-06:00 执行。',
      chart: {
        title: '优化前后GPU使用率对比',
        option: {
          tooltip: { trigger: 'axis' },
          legend: { data: ['优化前', '优化后'], top: 10 },
          radar: {
            indicator: [
              { name: 'GPU使用率', max: 100 },
              { name: '任务排队', max: 10 },
              { name: '响应延迟', max: 100 },
              { name: '成本效率', max: 100 },
            ],
          },
          series: [{
            type: 'radar',
            data: [
              { value: [81.3, 3, 75, 60], name: '优化前', areaStyle: { color: 'rgba(244, 67, 54, 0.1)' }, lineStyle: { color: '#f44336' }, itemStyle: { color: '#f44336' } },
              { value: [62.5, 0, 45, 85], name: '优化后', areaStyle: { color: 'rgba(76, 175, 80, 0.1)' }, lineStyle: { color: '#4caf50' }, itemStyle: { color: '#4caf50' } },
            ],
          }],
        },
      },
    },
  ],
};

/* ========== 快捷命令 ========== */
const QUICK_COMMANDS: Record<string, { cmd: string; label: string }[]> = {
  query: [
    { cmd: '/search', label: '搜索数据' },
    { cmd: '/catalog', label: '数据目录' },
    { cmd: '/stats', label: '数据统计' },
  ],
  trade: [
    { cmd: '/match', label: '供需匹配' },
    { cmd: '/contract', label: '创建合约' },
    { cmd: '/settle', label: '发起结算' },
  ],
  security: [
    { cmd: '/scan', label: '安全扫描' },
    { cmd: '/audit', label: '合规审计' },
    { cmd: '/threat', label: '威胁检测' },
  ],
  dispatch: [
    { cmd: '/schedule', label: '任务调度' },
    { cmd: '/optimize', label: '资源优化' },
    { cmd: '/perf', label: '性能分析' },
  ],
};

/* ========== Markdown 渲染组件 ========== */
const SimpleMarkdown: React.FC<{ content: string }> = ({ content }) => {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeLang = '';

  const flushTable = () => {
    if (tableRows.length >= 2) {
      const header = tableRows[0];
      const body = tableRows.slice(2); // skip separator row
      elements.push(
        <table key={`table-${elements.length}`} className="w-full text-sm border-collapse my-3">
          <thead>
            <tr className="bg-gray-50">
              {header.map((h, i) => (
                <th key={i} className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">{renderInline(h.trim())}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri} className="hover:bg-gray-50">
                {row.map((cell, ci) => (
                  <td key={ci} className="border border-gray-200 px-3 py-2">{renderInline(cell.trim())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>,
      );
    }
    tableRows = [];
  };

  const flushCode = () => {
    if (codeLines.length > 0) {
      elements.push(
        <div key={`code-${elements.length}`} className="my-3 rounded-lg overflow-hidden border border-gray-200">
          {codeLang && (
            <div className="bg-gray-100 px-3 py-1.5 text-xs text-gray-500 font-mono border-b border-gray-200">{codeLang}</div>
          )}
          <pre className="bg-gray-50 p-3 overflow-x-auto m-0">
            <code className="text-xs font-mono text-gray-700">{codeLines.join('\n')}</code>
          </pre>
        </div>,
      );
    }
    codeLines = [];
    codeLang = '';
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Code block detection
    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
      } else {
        if (inTable) { flushTable(); inTable = false; }
        inCodeBlock = true;
        codeLang = trimmed.slice(3).trim();
      }
      return;
    }
    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    // Table detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const cells = trimmed.split('|').filter(c => c.trim() !== '');
      if (cells.length > 0) {
        if (!cells.every(c => /^[-:]+$/.test(c.trim()))) {
          if (!inTable) inTable = true;
          tableRows.push(cells);
          return;
        } else if (inTable) {
          tableRows.push(cells);
          return;
        }
      }
    } else if (inTable) {
      flushTable();
      inTable = false;
    }

    // Headers
    if (trimmed.startsWith('## ')) {
      elements.push(<h3 key={idx} className="text-base font-bold mt-4 mb-2 text-gray-800">{renderInline(trimmed.slice(3))}</h3>);
    } else if (trimmed.startsWith('### ')) {
      elements.push(<h4 key={idx} className="text-sm font-bold mt-3 mb-1 text-gray-700">{renderInline(trimmed.slice(4))}</h4>);
    } else if (/^\d+\.\s/.test(trimmed)) {
      const match = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (match) {
        elements.push(
          <div key={idx} className="flex gap-2 my-1">
            <span className="text-gray-500 font-medium w-5 text-right">{match[1]}.</span>
            <span>{renderInline(match[2])}</span>
          </div>,
        );
      }
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div key={idx} className="flex gap-2 my-0.5">
          <span className="text-gray-400 w-5 text-right">-</span>
          <span>{renderInline(trimmed.slice(2))}</span>
        </div>,
      );
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <div key={idx} className="border-l-3 border-blue-400 pl-3 my-2 text-gray-600 text-sm italic bg-blue-50 py-2 rounded-r">
          {renderInline(trimmed.slice(2))}
        </div>,
      );
    } else if (trimmed === '') {
      elements.push(<div key={idx} className="h-2" />);
    } else {
      elements.push(<p key={idx} className="my-1 leading-relaxed">{renderInline(trimmed)}</p>);
    }
  });

  if (inTable) flushTable();
  if (inCodeBlock) flushCode();

  return <>{elements}</>;
};

const renderInline = (text: string): React.ReactNode => {
  if (!text) return text;
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*|`(.+?)`|(.+?)/g;
  let match;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match[1]) parts.push(<strong key={key++} className="text-gray-800 font-semibold">{match[1]}</strong>);
    else if (match[2]) parts.push(<code key={key++} className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono text-blue-600">{match[2]}</code>);
    else if (match[3]) parts.push(<span key={key++}>{match[3]}</span>);
  }
  return parts.length > 0 ? parts : text;
};

/* ========== 工具调用展示组件 ========== */
const ToolCallDisplay: React.FC<{ toolCall: ToolCall; agentColor: string }> = ({ toolCall, agentColor }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden my-2">
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded flex items-center justify-center" style={{ backgroundColor: `${agentColor}20`, color: agentColor }}>
            <Robot1Icon style={{ fontSize: '12px' }} />
          </div>
          <span className="font-medium text-gray-700 font-mono text-xs">{toolCall.name}</span>
          {toolCall.result && <Tag variant="light" size="small" theme="success">完成</Tag>}
          {toolCall.duration && <span className="text-xs text-gray-400">{toolCall.duration}</span>}
        </div>
        <ChevronDownIcon className={`transition-transform text-gray-400 ${expanded ? 'rotate-180' : ''}`} style={{ fontSize: '14px' }} />
      </button>
      {expanded && (
        <div className="px-3 py-2 border-t border-gray-100 text-xs">
          <div className="mb-2">
            <span className="text-gray-500 font-medium">输入参数：</span>
            <pre className="mt-1 p-2 bg-gray-50 rounded text-gray-600 overflow-x-auto font-mono text-xs">{JSON.stringify(toolCall.args, null, 2)}</pre>
          </div>
          {toolCall.result && (
            <div>
              <span className="text-gray-500 font-medium">执行结果：</span>
              <span className="ml-1 text-green-600">{toolCall.result}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* ========== AgentChatPage 主组件 ========== */
const AgentChatPage: React.FC = () => {
  const [activeAgent, setActiveAgent] = useState<string>('query');
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({
    query: [{
      id: 'welcome-query',
      role: 'assistant',
      content: AGENTS[0].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'query',
    }],
    trade: [{
      id: 'welcome-trade',
      role: 'assistant',
      content: AGENTS[1].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'trade',
    }],
    security: [{
      id: 'welcome-security',
      role: 'assistant',
      content: AGENTS[2].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'security',
    }],
    dispatch: [{
      id: 'welcome-dispatch',
      role: 'assistant',
      content: AGENTS[3].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'dispatch',
    }],
  });
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [conversations] = useState<Conversation[]>(MOCK_CONVERSATIONS);
  const [demoDialogIndex, setDemoDialogIndex] = useState<Record<string, number>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const streamTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentAgent = useMemo(() => AGENTS.find(a => a.key === activeAgent)!, [activeAgent]);
  const currentMessages = messages[activeAgent] || [];
  const currentCommands = QUICK_COMMANDS[activeAgent] || [];
  const currentConversations = useMemo(() => conversations.filter(c => c.agentType === activeAgent), [conversations, activeAgent]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages, streamingText]);

  // Cleanup streaming timer
  useEffect(() => {
    return () => {
      if (streamTimerRef.current) clearInterval(streamTimerRef.current);
    };
  }, []);

  // Copy message content
  const handleCopy = useCallback((id: string, content: string) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }, []);

  // Typewriter streaming effect
  const streamMessage = useCallback((fullContent: string, agentType: string, toolCalls?: ToolCall[], chart?: EChartOption) => {
    let charIndex = 0;
    setStreamingText('');
    setIsTyping(true);

    if (streamTimerRef.current) clearInterval(streamTimerRef.current);

    streamTimerRef.current = setInterval(() => {
      charIndex += 2; // 2 chars per tick for faster streaming
      if (charIndex >= fullContent.length) {
        if (streamTimerRef.current) clearInterval(streamTimerRef.current);
        setStreamingText('');
        setIsTyping(false);

        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: fullContent,
          timestamp: new Date().toISOString(),
          agentType,
          toolCalls,
          chart,
        };
        setMessages(prev => ({
          ...prev,
          [agentType]: [...(prev[agentType] || []), assistantMsg],
        }));
      } else {
        setStreamingText(fullContent.slice(0, charIndex));
      }
    }, 20);
  }, []);

  // Send message with demo dialogue
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || isTyping) return;

    const trimmedInput = inputValue.trim();
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmedInput,
      timestamp: new Date().toISOString(),
      agentType: activeAgent,
    };

    setMessages(prev => ({
      ...prev,
      [activeAgent]: [...(prev[activeAgent] || []), userMsg],
    }));
    setInputValue('');

    // Find matching demo dialogue
    const demoDialog = MOCK_DIALOGUES[activeAgent];
    const currentIndex = demoDialogIndex[activeAgent] || 0;

    // Try to find next assistant response in demo dialogue
    if (demoDialog && currentIndex < demoDialog.length) {
      const nextIdx = demoDialog.findIndex((d, i) => i >= currentIndex && d.role === 'assistant');
      if (nextIdx >= 0) {
        const demoMsg = demoDialog[nextIdx];
        // Update index for next round
        setDemoDialogIndex(prev => ({ ...prev, [activeAgent]: nextIdx + 1 }));

        // Show tool calls first if any
        if (demoMsg.toolCalls && demoMsg.toolCalls.length > 0) {
          const toolMsg: ChatMessage = {
            id: `tool-${Date.now()}`,
            role: 'assistant',
            content: demoMsg.content,
            timestamp: new Date().toISOString(),
            agentType: activeAgent,
            toolCalls: demoMsg.toolCalls,
          };
          setMessages(prev => ({
            ...prev,
            [activeAgent]: [...(prev[activeAgent] || []), toolMsg],
          }));

          // Then stream the full response
          setTimeout(() => {
            const nextAssistant = demoDialog.find((d, i) => i > nextIdx && d.role === 'assistant');
            if (nextAssistant) {
              setDemoDialogIndex(prev => ({ ...prev, [activeAgent]: demoDialog.indexOf(nextAssistant) + 1 }));
              streamMessage(nextAssistant.content, activeAgent, undefined, nextAssistant.chart);
            }
          }, 800);
          return;
        }

        streamMessage(demoMsg.content, activeAgent, demoMsg.toolCalls, demoMsg.chart);
        setDemoDialogIndex(prev => ({ ...prev, [activeAgent]: nextIdx + 1 }));
        return;
      }
    }

    // Fallback: generic response
    const fallbackResponses: Record<string, string> = {
      query: '正在为你检索相关数据，请稍候...\n\n已找到相关信息，如需更精确的结果，请提供更详细的查询条件。',
      trade: '正在分析交易需求，请稍候...\n\n已生成交易方案，如需创建合约请确认。',
      security: '正在执行安全检查，请稍候...\n\n安全检查完成，未发现异常。',
      dispatch: '正在分析调度需求，请稍候...\n\n已生成调度优化建议。',
    };
    streamMessage(fallbackResponses[activeAgent] || '正在处理你的请求...', activeAgent);
  }, [inputValue, isTyping, activeAgent, demoDialogIndex, streamMessage]);

  // Handle quick commands
  const handleCommand = useCallback((cmd: string) => {
    const cmdMap: Record<string, string> = {
      '/search': '帮我搜索数据资产目录',
      '/catalog': '查看数据目录结构',
      '/stats': '获取数据统计信息',
      '/match': '帮我进行供需智能匹配',
      '/contract': '创建一份交易合约',
      '/settle': '发起交易结算',
      '/scan': '执行系统安全扫描',
      '/audit': '进行合规性审计',
      '/threat': '检测安全威胁',
      '/schedule': '查看任务调度状态',
      '/optimize': '优化资源分配策略',
      '/perf': '分析系统性能指标',
    };
    const message = cmdMap[cmd] || cmd;
    setInputValue(message);
  }, []);

  // Load demo dialogue
  const handleLoadDemo = useCallback(() => {
    const demo = MOCK_DIALOGUES[activeAgent];
    if (!demo) return;

    // Reset messages to just welcome
    setMessages(prev => ({
      ...prev,
      [activeAgent]: [{
        id: `welcome-${activeAgent}`,
        role: 'assistant',
        content: currentAgent.welcomeMessage,
        timestamp: new Date().toISOString(),
        agentType: activeAgent,
      }],
    }));
    setDemoDialogIndex({ [activeAgent]: 0 });

    // Add first user message from demo
    const firstUser = demo.find(d => d.role === 'user');
    if (firstUser) {
      setTimeout(() => {
        const userMsg: ChatMessage = {
          id: `demo-user-${Date.now()}`,
          role: 'user',
          content: firstUser.content,
          timestamp: new Date().toISOString(),
          agentType: activeAgent,
        };
        setMessages(prev => ({
          ...prev,
          [activeAgent]: [...(prev[activeAgent] || []), userMsg],
        }));

        // Find and stream first assistant response
        const firstAssistant = demo.find((d, i) => i > 0 && d.role === 'assistant');
        if (firstAssistant) {
          setDemoDialogIndex({ [activeAgent]: demo.indexOf(firstAssistant) + 1 });
          if (firstAssistant.toolCalls && firstAssistant.toolCalls.length > 0) {
            const toolMsg: ChatMessage = {
              id: `demo-tool-${Date.now()}`,
              role: 'assistant',
              content: firstAssistant.content,
              timestamp: new Date().toISOString(),
              agentType: activeAgent,
              toolCalls: firstAssistant.toolCalls,
            };
            setMessages(prev => ({
              ...prev,
              [activeAgent]: [...(prev[activeAgent] || []), toolMsg],
            }));

            // Stream next response
            const nextAssistant = demo.find((d, i) => i > demo.indexOf(firstAssistant) && d.role === 'assistant');
            if (nextAssistant) {
              setTimeout(() => {
                setDemoDialogIndex({ [activeAgent]: demo.indexOf(nextAssistant) + 1 });
                streamMessage(nextAssistant.content, activeAgent, undefined, nextAssistant.chart);
              }, 800);
            }
          } else {
            streamMessage(firstAssistant.content, activeAgent, firstAssistant.toolCalls, firstAssistant.chart);
          }
        }
      }, 500);
    }
  }, [activeAgent, currentAgent, streamMessage]);

  // Clear conversation
  const handleClear = useCallback(() => {
    if (streamTimerRef.current) clearInterval(streamTimerRef.current);
    setStreamingText('');
    setIsTyping(false);
    setDemoDialogIndex({});
    setMessages(prev => ({
      ...prev,
      [activeAgent]: [{
        id: `welcome-${activeAgent}`,
        role: 'assistant',
        content: currentAgent.welcomeMessage,
        timestamp: new Date().toISOString(),
        agentType: activeAgent,
      }],
    }));
  }, [activeAgent, currentAgent]);

  // Export conversation
  const handleExport = useCallback(() => {
    const msgs = messages[activeAgent] || [];
    const exportText = msgs.map(m => {
      const time = new Date(m.timestamp).toLocaleString('zh-CN');
      const role = m.role === 'user' ? '用户' : currentAgent.label;
      return `[${time}] ${role}:\n${m.content}\n`;
    }).join('\n---\n\n');

    const blob = new Blob([exportText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentAgent.label}_对话记录_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    MessagePlugin.success('对话记录已导出');
  }, [activeAgent, messages, currentAgent]);

  // Breadcrumbs
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: 'AI 智能助手' }],
    [],
  );

  return (
    <PageContainer padding="none" bgColor="#f0f2f5">
      <div className="flex flex-col h-[calc(100vh-64px)]">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 sm:px-6 py-2 flex-shrink-0">
          <PageHeader
            title="AI 智能助手"
            subtitle="基于大模型的能源数据空间智能问答服务"
            breadcrumbs={breadcrumbs}
            iconActions={[
              { icon: <DownloadIcon />, onClick: handleExport, tooltip: '导出对话' },
              { icon: <RefreshIcon />, onClick: handleClear, tooltip: '清空对话' },
              { icon: showRightPanel ? <ChevronDownIcon style={{ transform: 'rotate(90deg)' }} /> : <ChevronDownIcon style={{ transform: 'rotate(-90deg)' }} />, onClick: () => setShowRightPanel(!showRightPanel), tooltip: showRightPanel ? '隐藏侧栏' : '显示侧栏' },
            ]}
          />
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* ====== 左侧面板 ====== */}
          <div className="w-60 bg-white border-r border-gray-200 flex-shrink-0 hidden md:flex flex-col">
            {/* Agent 选择 */}
            <div className="p-3 border-b border-gray-100">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">选择 Agent</h4>
              <div className="flex flex-col gap-1">
                {AGENTS.map(agent => (
                  <button
                    key={agent.key}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left ${
                      activeAgent === agent.key
                        ? 'bg-blue-50 border border-blue-200'
                        : 'hover:bg-gray-50 border border-transparent'
                    }`}
                    onClick={() => setActiveAgent(agent.key)}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: `${agent.color}15`, color: agent.color }}
                    >
                      {agent.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className={`text-sm font-medium truncate ${activeAgent === agent.key ? 'text-blue-700' : 'text-gray-800'}`}>
                        {agent.label}
                      </div>
                      <div className="text-xs text-gray-500 truncate">{agent.description}</div>
                    </div>
                    {activeAgent === agent.key && (
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* 历史对话 */}
            <div className="flex-1 overflow-auto">
              <div className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">历史对话</h4>
                  <span className="text-xs text-gray-400">{currentConversations.length}</span>
                </div>
                <div className="flex flex-col gap-1">
                  {currentConversations.length === 0 ? (
                    <div className="text-center py-6 text-gray-400">
                      <ChatIcon style={{ fontSize: '24px' }} />
                      <div className="text-xs mt-1">暂无历史对话</div>
                    </div>
                  ) : (
                    currentConversations.map(conv => (
                      <div
                        key={conv.id}
                        className="px-3 py-2.5 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <FileIcon className="text-gray-400 flex-shrink-0" style={{ fontSize: '14px' }} />
                          <span className="text-sm font-medium text-gray-700 truncate">{conv.title}</span>
                        </div>
                        <div className="text-xs text-gray-500 truncate pl-5">{conv.lastMessage}</div>
                        <div className="flex items-center justify-between mt-1 pl-5">
                          <span className="text-xs text-gray-400">{conv.timestamp}</span>
                          <span className="text-xs text-gray-400">{conv.messageCount}条</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Agent 统计 */}
            <div className="p-3 border-t border-gray-100 bg-gray-50">
              <div className="flex items-center gap-2 mb-2">
                <Robot1Icon className="text-gray-400" style={{ fontSize: '14px' }} />
                <span className="text-xs text-gray-500 font-medium">Agent 信息</span>
              </div>
              <div className="text-xs text-gray-600 space-y-1.5">
                <div className="flex justify-between">
                  <span>当前Agent</span>
                  <span className="font-medium" style={{ color: currentAgent.color }}>{currentAgent.label}</span>
                </div>
                <div className="flex justify-between">
                  <span>对话轮次</span>
                  <span className="font-medium">{Math.floor((currentMessages.length - 1) / 2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>工具调用</span>
                  <span className="font-medium">{currentMessages.reduce((acc, m) => acc + (m.toolCalls?.length || 0), 0)}次</span>
                </div>
              </div>
            </div>
          </div>

          {/* ====== 中间聊天区域 ====== */}
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            {/* 消息列表 */}
            <div className="flex-1 overflow-auto px-4 sm:px-6 py-4 space-y-4">
              {currentMessages.map((msg) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1"
                      style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                    >
                      {currentAgent.icon}
                    </div>
                  )}

                  <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white rounded-tr-sm'
                          : 'bg-white border border-gray-200 text-gray-700 rounded-tl-sm shadow-sm'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <span>{msg.content}</span>
                      ) : (
                        <SimpleMarkdown content={msg.content} />
                      )}
                    </div>

                    {/* 工具调用 */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="mt-2">
                        {msg.toolCalls.map(tc => (
                          <ToolCallDisplay key={tc.id} toolCall={tc} agentColor={currentAgent.color} />
                        ))}
                      </div>
                    )}

                    {/* 图表 */}
                    {msg.chart && (
                      <div className="mt-2 bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                        <div className="text-xs font-medium text-gray-600 mb-2">{msg.chart.title}</div>
                        <ReactECharts
                          option={msg.chart.option}
                          style={{ height: 250, width: '100%' }}
                          opts={{ renderer: 'canvas' }}
                          notMerge
                        />
                      </div>
                    )}

                    {/* 消息操作 */}
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1 mt-1.5 ml-1">
                        <span className="text-xs text-gray-400">
                          {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <Tooltip content={copiedId === msg.id ? '已复制' : '复制'}>
                          <button
                            className="p-1 hover:bg-gray-100 rounded transition-colors"
                            onClick={() => handleCopy(msg.id, msg.content)}
                          >
                            {copiedId === msg.id
                              ? <CheckIcon className="text-green-500" style={{ fontSize: '14px' }} />
                              : <CopyIcon className="text-gray-400" style={{ fontSize: '14px' }} />
                            }
                          </button>
                        </Tooltip>
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                      <UserIcon className="text-white" style={{ fontSize: '16px' }} />
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming text */}
              {streamingText && (
                <div className="flex gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1"
                    style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                  >
                    {currentAgent.icon}
                  </div>
                  <div className="max-w-[80%]">
                    <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-gray-700 shadow-sm">
                      <SimpleMarkdown content={streamingText} />
                      <span className="inline-block w-0.5 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                    </div>
                  </div>
                </div>
              )}

              {/* Typing indicator (when waiting for response) */}
              {isTyping && !streamingText && (
                <div className="flex gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                  >
                    {currentAgent.icon}
                  </div>
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* 快捷命令 */}
            <div className="px-4 sm:px-6 py-2 flex items-center gap-2 flex-wrap">
              {currentCommands.map(cmd => (
                <button
                  key={cmd.cmd}
                  className="px-3 py-1 text-xs rounded-full border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
                  onClick={() => handleCommand(cmd.cmd)}
                >
                  {cmd.label}
                </button>
              ))}
              <button
                className="px-3 py-1 text-xs rounded-full border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
                onClick={handleLoadDemo}
              >
                加载示例对话
              </button>
            </div>

            {/* 输入区域 */}
            <div className="bg-white border-t border-gray-200 px-4 sm:px-6 py-3 flex-shrink-0">
              <div className="flex gap-3 items-end max-w-4xl mx-auto">
                <div className="flex-1 relative">
                  <Input
                    ref={inputRef}
                    value={inputValue}
                    onChange={setInputValue}
                    placeholder={currentAgent.placeholder}
                    onEnter={handleSend}
                    disabled={isTyping}
                    size="large"
                    className="!rounded-xl"
                  />
                </div>
                <Button
                  theme="primary"
                  icon={<SendIcon />}
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isTyping}
                  size="large"
                  className="!rounded-xl !px-5"
                >
                  发送
                </Button>
              </div>
              <div className="text-center mt-1.5">
                <span className="text-xs text-gray-400">AI 回复仅供参考，重要决策请以官方数据为准</span>
              </div>
            </div>
          </div>

          {/* ====== 右侧面板 ====== */}
          {showRightPanel && (
            <div className="w-72 bg-white border-l border-gray-200 flex-shrink-0 hidden lg:flex flex-col overflow-auto">
              {/* Agent 能力说明 */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-2 mb-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                  >
                    {currentAgent.icon}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-800">{currentAgent.label}</div>
                    <div className="text-xs text-gray-500">{currentAgent.description}</div>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <div className="text-xs font-medium text-gray-500 mb-1">核心能力</div>
                  {currentAgent.capabilities.map((cap, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: currentAgent.color }} />
                      {cap}
                    </div>
                  ))}
                </div>
              </div>

              {/* 可用工具 */}
              <div className="p-4 border-b border-gray-100">
                <div className="text-xs font-medium text-gray-500 mb-2">可用工具</div>
                <div className="space-y-1.5">
                  {currentAgent.tools.map((tool, i) => (
                    <div key={i} className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-gray-50">
                      <Robot1Icon className="text-gray-400" style={{ fontSize: '12px' }} />
                      <div>
                        <div className="text-xs font-mono font-medium text-gray-700">{tool.name}</div>
                        <div className="text-xs text-gray-500">{tool.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 推荐问题 */}
              <div className="p-4 border-b border-gray-100">
                <div className="text-xs font-medium text-gray-500 mb-2">推荐问题</div>
                <div className="space-y-1.5">
                  {currentAgent.suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-gray-50 text-xs text-gray-600 transition-colors flex items-start gap-2"
                      onClick={() => { setInputValue(q); }}
                    >
                      <SearchIcon className="text-gray-400 flex-shrink-0 mt-0.5" style={{ fontSize: '12px' }} />
                      <span>{q}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 数据可视化区域 */}
              <div className="p-4 flex-1">
                <div className="text-xs font-medium text-gray-500 mb-2">数据概览</div>
                <div className="space-y-3">
                  <div className="rounded-lg border border-gray-200 p-3">
                    <div className="text-xs text-gray-500 mb-1">今日查询量</div>
                    <div className="text-xl font-bold" style={{ color: currentAgent.color }}>128</div>
                    <div className="text-xs text-green-600 mt-0.5">↑ 12% 较昨日</div>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <div className="text-xs text-gray-500 mb-1">平均响应时间</div>
                    <div className="text-xl font-bold text-gray-800">1.2s</div>
                    <div className="text-xs text-green-600 mt-0.5">↓ 8% 较昨日</div>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <div className="text-xs text-gray-500 mb-1">工具调用成功率</div>
                    <div className="text-xl font-bold text-gray-800">98.5%</div>
                    <div className="text-xs text-gray-500 mt-0.5">稳定运行中</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
};

export default AgentChatPage;
