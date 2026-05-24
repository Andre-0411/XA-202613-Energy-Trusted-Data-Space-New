/**
 * 隐私计算路由页面
 * 场景-技术矩阵 / 自动路由推荐 / 引擎状态监控
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Textarea, Select } from 'tdesign-react';
import {
  RefreshIcon, MapRoutePlanningIcon, ShieldErrorIcon, DashboardIcon,
  CheckCircleIcon, CloseCircleIcon, InfoCircleIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  routePrivacyTask, listPrivacyTechnologies, listPrivacyScenarios, getPrivacyEngineStatus
} from '@/api/compute';
import type { PrivacyRouteResult, PrivacyTechnology, PrivacyScenario } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import LoadingOverlay from '@/components/LoadingOverlay';

/** 场景选项 */
const SCENARIO_OPTIONS = [
  { value: '负荷预测', label: '负荷预测', tech: 'FL' },
  { value: '价格协商', label: '价格协商', tech: 'MPC' },
  { value: '碳排放', label: '碳排放核算', tech: 'TEE' },
  { value: '安全审计', label: '安全审计', tech: 'HE' },
  { value: '联合预测', label: '联合预测', tech: 'FL' },
  { value: '安全结算', label: '安全结算', tech: 'MPC' },
  { value: '调度优化', label: '调度优化', tech: 'TEE' },
  { value: '统计查询', label: '统计查询', tech: 'HE' },
];

/** 数据敏感度选项 */
const SENSITIVITY_OPTIONS = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'critical', label: '极高' },
];

const PrivacyComputePage: React.FC = () => {
  // 表单状态
  const [taskDescription, setTaskDescription] = useState('');
  const [scenario, setScenario] = useState('');
  const [dataSensitivity, setDataSensitivity] = useState('high');
  const [participants, setParticipants] = useState(2);

  // ===== 数据查询 =====
  const { data: technologiesData, isLoading: techLoading } = useQuery({
    queryKey: ['privacy-technologies'],
    queryFn: () => listPrivacyTechnologies(),
  });

  const { data: scenariosData, isLoading: scenariosLoading } = useQuery({
    queryKey: ['privacy-scenarios'],
    queryFn: () => listPrivacyScenarios(),
  });

  const { data: engineStatusData, isLoading: engineLoading, refetch: refetchEngineStatus } = useQuery({
    queryKey: ['privacy-engine-status'],
    queryFn: () => getPrivacyEngineStatus(),
  });

  // ===== 路由推荐 =====
  const routeMutation = useMutation({
    mutationFn: () => routePrivacyTask({
      task_description: taskDescription,
      scenario: scenario || undefined,
      data_sensitivity: dataSensitivity,
      participants,
    }),
    onError: () => {
      MessagePlugin.error('路由推荐失败');
    },
  });

  // 处理数据
  const technologies: PrivacyTechnology[] = technologiesData?.data?.technologies ?? [];
  const scenarios: PrivacyScenario[] = scenariosData?.data?.scenarios ?? [];
  const engineStatus = engineStatusData?.data?.engines ?? {};
  const routeResult: PrivacyRouteResult | null = routeMutation.data?.data ?? null;

  // ===== 场景-技术矩阵图表 =====
  const matrixChartOption = useMemo(() => {
    const techs = ['FL', 'MPC', 'TEE', 'HE', 'DP', 'PSI'];
    const scenarioNames = scenarios.map((s) => s.scenario);

    // 构建矩阵数据
    const data: [number, number, number][] = [];
    scenarios.forEach((s, y) => {
      techs.forEach((tech, x) => {
        const value = s.recommended_technology === tech ? 2
          : s.alternatives.includes(tech) ? 1
          : 0;
        if (value > 0) {
          data.push([x, y, value]);
        }
      });
    });

    return {
      tooltip: {
        position: 'top',
        formatter: (params: any) => {
          const [x, y, value] = params.data;
          const tech = techs[x];
          const scenarioName = scenarioNames[y];
          const label = value === 2 ? '推荐' : '备选';
          return `${scenarioName} → ${tech} (${label})`;
        },
      },
      grid: { left: '15%', right: '10%', bottom: '15%', top: '5%' },
      xAxis: { type: 'category', data: techs, splitArea: { show: true } },
      yAxis: { type: 'category', data: scenarioNames, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: 2,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: { color: ['#f5f5f5', '#fff9c4', '#4caf50'] },
        pieces: [
          { value: 0, label: '无', color: '#f5f5f5' },
          { value: 1, label: '备选', color: '#fff9c4' },
          { value: 2, label: '推荐', color: '#4caf50' },
        ],
      },
      series: [{
        name: '场景-技术矩阵',
        type: 'heatmap',
        data,
        label: {
          show: true,
          formatter: (params: any) => {
            const value = params.data[2];
            return value === 2 ? '★' : value === 1 ? '○' : '';
          },
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      }],
    };
  }, [scenarios]);

  // ===== 提交路由 =====
  const handleRoute = useCallback(() => {
    if (!taskDescription.trim()) return;
    routeMutation.mutate();
  }, [taskDescription, routeMutation]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '隐私计算路由' }],
    [],
  );

  // 引擎状态图标
  const getEngineStatusIcon = (available: boolean) => {
    return available
      ? <CheckCircleIcon style={{ color: '#4caf50', fontSize: 14 }} />
      : <CloseCircleIcon style={{ color: '#f44336', fontSize: 14 }} />;
  };

  const isLoading = techLoading || scenariosLoading || engineLoading;

  return (
    <div className="flex flex-col gap-4 h-full overflow-auto">
      <PageHeader
        title="隐私计算路由"
        subtitle="基于场景自动推荐最佳隐私计算技术方案"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => refetchEngineStatus(),
            tooltip: '刷新引擎状态',
          },
        ]}
      />

      {/* 引擎状态 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-2">引擎状态</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(engineStatus).map(([tech, status]: [string, any]) => (
            <Tag
              key={tech}
              size="small"
              variant="outline"
              icon={getEngineStatusIcon(status.available)}
              style={{
                borderColor: status.available ? '#4caf50' : '#f44336',
                color: status.available ? '#4caf50' : '#f44336',
              }}
            >
              {tech}: {status.name}
            </Tag>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* 路由表单 */}
        <div className="md:col-span-5 rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">任务配置</p>
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-1">任务描述</p>
              <Textarea
                rows={3}
                value={taskDescription}
                onChange={setTaskDescription}
                placeholder="例如：多方联合负荷预测，保护用户用电隐私"
              />
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-1">业务场景</p>
              <Select
                value={scenario}
                onChange={(val) => setScenario(val as string)}
                options={[{ label: '自动推断', value: '' }, ...SCENARIO_OPTIONS.map(opt => ({
                  label: opt.label,
                  value: opt.value,
                }))]}
                clearable
              />
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-1">数据敏感度</p>
              <Select
                value={dataSensitivity}
                onChange={(val) => setDataSensitivity(val as string)}
                options={SENSITIVITY_OPTIONS}
              />
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-1">参与方数量</p>
              <Input
                type="number"
                value={String(participants)}
                onChange={(val) => setParticipants(Math.max(2, parseInt(val) || 2))}
                size="small"
              />
            </div>

            <Button
              theme="primary"
              icon={<MapRoutePlanningIcon />}
              onClick={handleRoute}
              disabled={!taskDescription.trim() || routeMutation.isPending}
              block
            >
              {routeMutation.isPending ? '分析中...' : '获取路由推荐'}
            </Button>
          </div>
        </div>

        {/* 路由结果 */}
        <div className="md:col-span-7 rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">路由推荐结果</p>

          {routeMutation.isError && (
            <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              路由推荐失败: {(routeMutation.error as any)?.message || '未知错误'}
            </div>
          )}

          {routeResult && (
            <div className="flex flex-col gap-3">
              {/* 推荐技术 */}
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <ShieldErrorIcon style={{ fontSize: 32, color: '#2196f3' }} />
                  <div>
                    <p className="text-lg font-bold">{routeResult.technology_name}</p>
                    <p className="text-sm text-gray-500">
                      场景: {routeResult.scenario} - {routeResult.scenario_description}
                    </p>
                  </div>
                </div>
              </div>

              {/* 技术详情 */}
              {routeResult.technology_info && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <p className="text-sm font-semibold mb-2">技术详情</p>
                  <p className="text-sm mb-2">{routeResult.technology_info.description}</p>
                  <div className="flex flex-wrap gap-1">
                    {routeResult.technology_info.strengths?.map((s, i) => (
                      <Tag key={i} size="small" variant="outline" style={{ borderColor: '#4caf50', color: '#4caf50' }}>{s}</Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 推荐理由 */}
              <div className="border border-gray-200 rounded-lg p-4">
                <p className="text-sm font-semibold mb-2">推荐理由</p>
                <p className="text-sm">{routeResult.reasoning}</p>
              </div>

              {/* 备选方案 */}
              {routeResult.alternatives && routeResult.alternatives.length > 0 && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <p className="text-sm font-semibold mb-2">备选方案</p>
                  <div className="flex flex-col gap-2">
                    {routeResult.alternatives.map((alt, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="text-sm">{alt.technology_name}</span>
                        <Tag
                          size="small"
                          variant="outline"
                          style={{
                            borderColor: alt.available ? '#4caf50' : '#f44336',
                            color: alt.available ? '#4caf50' : '#f44336',
                          }}
                        >
                          {alt.available ? '可用' : '不可用'}
                        </Tag>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 建议配置 */}
              {routeResult.config && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <p className="text-sm font-semibold mb-2">建议配置</p>
                  <table className="w-full text-sm">
                    <tbody>
                      {Object.entries(routeResult.config).map(([key, value]) => (
                        <tr key={key} className="border-b border-gray-100 last:border-0">
                          <td className="py-2 font-semibold">{key}</td>
                          <td className="py-2">{JSON.stringify(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {!routeResult && !routeMutation.isPending && (
            <div className="text-center py-8 text-gray-400">
              <MapRoutePlanningIcon style={{ fontSize: 48, opacity: 0.5, marginBottom: 8 }} />
              <p>请输入任务描述并点击"获取路由推荐"</p>
            </div>
          )}
        </div>
      </div>

      {/* 场景-技术矩阵 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-1">场景-技术矩阵</p>
        <p className="text-sm text-gray-400 mb-3">★ 推荐技术 | ○ 备选技术</p>
        <ReactECharts option={matrixChartOption} style={{ height: 400 }} />
      </div>

      {/* 技术列表 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">隐私计算技术</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {technologies.map((tech) => (
            <div key={tech.technology} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <p className="text-sm font-semibold">{tech.name}</p>
                <Tag
                  size="small"
                  variant="outline"
                  icon={getEngineStatusIcon(tech.available)}
                  style={{
                    borderColor: tech.available ? '#4caf50' : '#f44336',
                    color: tech.available ? '#4caf50' : '#f44336',
                  }}
                >
                  {tech.available ? '可用' : '不可用'}
                </Tag>
              </div>
              <p className="text-sm text-gray-500 mb-2">{tech.description}</p>
              <div className="flex flex-wrap gap-1">
                {tech.strengths?.slice(0, 3).map((s, i) => (
                  <Tag key={i} size="small" variant="outline">{s}</Tag>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default PrivacyComputePage;
