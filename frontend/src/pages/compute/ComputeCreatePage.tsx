/**
 * 创建计算任务页面
 * 步骤式表单：选择类型 → 配置参数 → 选择参与方/数据集 → 确认提交
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Textarea, Steps, Checkbox, Tag, Divider, MessagePlugin } from 'tdesign-react';
import { ChevronLeftIcon, SendIcon } from 'tdesign-icons-react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createTask } from '@/api/compute';
import { listOrganizations } from '@/api/ops';
import { listDataAssets } from '@/api/data';
import type { ComputeTask, Organization, DataAsset } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';

/** 步骤标签 */
const STEPS = ['选择计算类型', '配置参数', '选择参与方/数据集', '确认并提交'];

/** 计算类型选项 */
const COMPUTE_TYPE_OPTIONS = [
  { value: 'MPC', label: 'MPC 安全多方计算', description: '多个参与方在不泄露各自数据的前提下协同计算', params: ['protocol', 'parties_count', 'security_param'] },
  { value: 'FL', label: '联邦学习', description: '分布式机器学习，各参与方数据不出域', params: ['algorithm', 'rounds', 'learning_rate', 'batch_size'] },
  { value: 'TEE', label: 'TEE 可信执行环境', description: '在安全飞地内执行计算，保障数据机密性', params: ['runtime', 'algorithm', 'memory_limit'] },
  { value: 'HE', label: '同态加密', description: '直接对密文进行计算，无需解密', params: ['scheme', 'operation', 'key_size'] },
  { value: 'DP', label: '差分隐私', description: '在查询结果中注入噪声保护个体隐私', params: ['mechanism', 'epsilon', 'delta', 'sensitivity'] },
  { value: 'SANDBOX', label: '沙箱计算', description: '在隔离环境中执行不可信代码', params: ['algorithm', 'timeout', 'resource_limit'] },
];

/** 组织状态显示映射 */
const ORG_STATUS_MAP: Record<string, string> = {
  active: '正常', inactive: '停用', pending: '待审核',
};

const ComputeCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ===== 获取真实参与方（组织列表） =====
  const { data: orgsData, isLoading: orgsLoading } = useQuery({
    queryKey: ['organizations-for-compute'],
    queryFn: () => listOrganizations({ page: 1, page_size: 100, status: 'active' }),
  });
  const parties: Organization[] = orgsData?.data?.items ?? [];

  // ===== 获取真实数据集（数据资产列表） =====
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['data-assets-for-compute'],
    queryFn: () => listDataAssets({ page: 1, page_size: 100 }),
  });
  const datasets: DataAsset[] = assetsData?.data?.items ?? [];

  // ===== 步骤状态 =====
  const [activeStep, setActiveStep] = useState<number>(0);

  // ===== 步骤1: 计算类型 =====
  const [computeType, setComputeType] = useState<string>('');

  // ===== 步骤2: 配置参数 =====
  const [taskName, setTaskName] = useState<string>('');
  const [taskDescription, setTaskDescription] = useState<string>('');
  const [params, setParams] = useState<Record<string, string>>({});

  // ===== 步骤3: 参与方 & 数据集 =====
  const [selectedParties, setSelectedParties] = useState<string[]>([]);
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);

  // ===== Mutation =====
  const createMut = useMutation({
    mutationFn: (data: Partial<ComputeTask>) => createTask(data),
    onSuccess: () => {
      MessagePlugin.success('任务创建成功');
      queryClient.invalidateQueries({ queryKey: ['computeTasks'] });
      navigate('/dashboard/compute/tasks');
    },
    onError: () => { MessagePlugin.error('任务创建失败'); },
  });

  // ===== 当前选中类型的参数定义 =====
  const selectedTypeOption = useMemo(
    () => COMPUTE_TYPE_OPTIONS.find((o) => o.value === computeType),
    [computeType],
  );

  // ===== 步骤操作 =====
  const handleNext = useCallback(() => { setActiveStep((prev) => Math.min(prev + 1, STEPS.length - 1)); }, []);
  const handleBack = useCallback(() => { setActiveStep((prev) => Math.max(prev - 1, 0)); }, []);

  const handleSubmit = useCallback(() => {
    const config: Record<string, unknown> = {};
    Object.entries(params).forEach(([key, value]) => {
      const numVal = Number(value);
      config[key] = isNaN(numVal) ? value : numVal;
    });
    createMut.mutate({ name: taskName, task_type: computeType, scenario: taskDescription || null, config });
  }, [taskName, computeType, taskDescription, params, createMut]);

  // ===== 参与方选择 =====
  const toggleParty = useCallback((id: string) => {
    setSelectedParties((prev) => prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]);
  }, []);

  const toggleDataset = useCallback((id: string) => {
    setSelectedDatasets((prev) => prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]);
  }, []);

  // ===== 参数变更 =====
  const handleParamChange = useCallback((key: string, value: string) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  }, []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算任务', href: '/compute/tasks' }, { label: '创建任务' }],
    [],
  );

  // ===== 步骤验证 =====
  const canNext = useMemo(() => {
    switch (activeStep) {
      case 0: return !!computeType;
      case 1: return !!taskName.trim();
      case 2: return selectedParties.length > 0 || selectedDatasets.length > 0;
      case 3: return true;
      default: return false;
    }
  }, [activeStep, computeType, taskName, selectedParties, selectedDatasets]);

  // ===== 渲染步骤1 =====
  const renderStep1 = () => (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-gray-500">选择一种可信计算类型，不同类型具有不同的隐私保护机制和适用场景。</p>
      <div className="flex flex-col gap-3">
        {COMPUTE_TYPE_OPTIONS.map((opt) => (
          <div
            key={opt.value}
            onClick={() => setComputeType(opt.value)}
            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${computeType === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'}`}
          >
            <div className="flex items-center gap-3">
              <Checkbox checked={computeType === opt.value} />
              <div>
                <p className="text-sm font-semibold text-gray-800">{opt.label}</p>
                <p className="text-xs text-gray-500">{opt.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // ===== 渲染步骤2 =====
  const renderStep2 = () => (
    <div className="flex flex-col gap-4">
      <div>
        <label className="block text-sm text-gray-600 mb-1">任务名称 *</label>
        <Input value={taskName} onChange={setTaskName} />
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">任务描述</label>
        <Textarea value={taskDescription} onChange={setTaskDescription} rows={2} />
      </div>
      <Divider />
      <h4 className="text-sm font-semibold text-gray-700">{selectedTypeOption?.label ?? '计算类型'} 参数配置</h4>
      {selectedTypeOption?.params.map((paramKey) => (
        <div key={paramKey}>
          <label className="block text-sm text-gray-600 mb-1">{paramKey}</label>
          <Input value={params[paramKey] ?? ''} onChange={(val) => handleParamChange(paramKey, val)} placeholder={`请输入 ${paramKey}`} />
        </div>
      ))}
    </div>
  );

  // ===== 渲染步骤3 =====
  const renderStep3 = () => (
    <div className="flex flex-col gap-6">
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">选择参与方（组织）</h4>
        {orgsLoading ? (
          <p className="text-center text-gray-400 py-8">加载中...</p>
        ) : parties.length === 0 ? (
          <div className="bg-blue-50 text-blue-700 p-3 rounded-lg text-sm">暂无可用组织，请先在运营中心添加组织。</div>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="w-10 px-4 py-3"></th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">名称</th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">编码</th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">状态</th>
                </tr>
              </thead>
              <tbody>
                {parties.map((org) => (
                  <tr key={org.id} onClick={() => toggleParty(org.id)} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3"><Checkbox checked={selectedParties.includes(org.id)} /></td>
                    <td className="px-4 py-3">{org.name}</td>
                    <td className="px-4 py-3 text-gray-500">{org.code}</td>
                    <td className="px-4 py-3">
                      <Tag theme={org.status === 'active' ? 'success' : 'default'} variant="light">
                        {ORG_STATUS_MAP[org.status] ?? org.status}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">选择数据集（数据资产）</h4>
        {assetsLoading ? (
          <p className="text-center text-gray-400 py-8">加载中...</p>
        ) : datasets.length === 0 ? (
          <div className="bg-blue-50 text-blue-700 p-3 rounded-lg text-sm">暂无可用数据资产，请先在数据中心录入资产。</div>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="w-10 px-4 py-3"></th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">名称</th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">编码</th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">类型</th>
                  <th className="text-left px-4 py-3 font-bold text-gray-600">敏感等级</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds) => (
                  <tr key={ds.id} onClick={() => toggleDataset(ds.id)} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3"><Checkbox checked={selectedDatasets.includes(ds.id)} /></td>
                    <td className="px-4 py-3">{ds.name}</td>
                    <td className="px-4 py-3 text-gray-500">{ds.asset_code}</td>
                    <td className="px-4 py-3 text-gray-500">{ds.asset_type}</td>
                    <td className="px-4 py-3">
                      <Tag theme={ds.sensitivity_level === 'high' ? 'danger' : ds.sensitivity_level === 'medium' ? 'warning' : 'default'} variant="light">
                        {ds.sensitivity_level}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );

  // ===== 渲染步骤4 =====
  const renderStep4 = () => (
    <div className="flex flex-col gap-4">
      <div className="bg-blue-50 text-blue-700 p-3 rounded-lg text-sm">请确认以下信息无误后提交创建任务。</div>
      <div className="border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-bold text-gray-700 mb-3">任务信息</h4>
        <div className="flex flex-col gap-2">
          <div className="flex gap-2"><span className="text-sm text-gray-500 w-24">任务名称:</span><span className="text-sm font-medium">{taskName}</span></div>
          <div className="flex gap-2"><span className="text-sm text-gray-500 w-24">计算类型:</span><Tag theme="primary">{selectedTypeOption?.label ?? computeType}</Tag></div>
          {taskDescription && <div className="flex gap-2"><span className="text-sm text-gray-500 w-24">描述:</span><span className="text-sm">{taskDescription}</span></div>}
        </div>
      </div>
      <div className="border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-bold text-gray-700 mb-3">参数配置</h4>
        <div className="flex flex-col gap-1">
          {Object.entries(params).map(([key, value]) => (
            <div key={key} className="flex gap-2">
              <span className="text-sm text-gray-500 w-24">{key}:</span>
              <span className="text-sm">{value}</span>
            </div>
          ))}
          {Object.keys(params).length === 0 && <p className="text-sm text-gray-400">无参数配置</p>}
        </div>
      </div>
      <div className="border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-bold text-gray-700 mb-3">参与方 & 数据集</h4>
        <div className="flex flex-col gap-3">
          <div>
            <p className="text-xs text-gray-400 mb-1">参与方:</p>
            <div className="flex flex-wrap gap-1">
              {selectedParties.map((id) => {
                const org = parties.find((p) => p.id === id);
                return org ? <Tag key={id}>{org.name}</Tag> : null;
              })}
              {selectedParties.length === 0 && <span className="text-xs text-gray-400">未选择</span>}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-1">数据集:</p>
            <div className="flex flex-wrap gap-1">
              {selectedDatasets.map((id) => {
                const ds = datasets.find((d) => d.id === id);
                return ds ? <Tag key={id} variant="outline">{ds.name}</Tag> : null;
              })}
              {selectedDatasets.length === 0 && <span className="text-xs text-gray-400">未选择</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageHeader
        title="创建计算任务"
        subtitle="通过步骤式表单配置并创建可信计算任务"
        breadcrumbs={breadcrumbs}
        actions={[{
          label: '返回列表',
          icon: <ChevronLeftIcon />,
          onClick: () => navigate('/dashboard/compute/tasks'),
          variant: 'outlined',
        }]}
      />

      {/* 步骤条 */}
      <div className="rounded-xl bg-white border border-gray-200 p-6">
        <Steps current={activeStep} style={{ width: '100%' }}>
          {STEPS.map((label) => (<Steps.StepItem key={label} title={label} />))}
        </Steps>
      </div>

      {/* 步骤内容 */}
      <div className="rounded-xl bg-white border border-gray-200 p-6 flex-1 overflow-auto">
        {activeStep === 0 && renderStep1()}
        {activeStep === 1 && renderStep2()}
        {activeStep === 2 && renderStep3()}
        {activeStep === 3 && renderStep4()}
      </div>

      {/* 操作按钮 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex justify-between">
          <Button variant="outline" onClick={handleBack} disabled={activeStep === 0}>上一步</Button>
          <div className="flex gap-2">
            {activeStep < STEPS.length - 1 ? (
              <Button theme="primary" onClick={handleNext} disabled={!canNext}>下一步</Button>
            ) : (
              <Button theme="primary" onClick={handleSubmit} disabled={!canNext} loading={createMut.isPending} icon={<SendIcon />}>
                {createMut.isPending ? '提交中...' : '提交创建'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComputeCreatePage;
