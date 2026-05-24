/**
 * 系统配置管理页面
 * 提供系统参数配置、邮件设置、通知设置、安全配置等管理功能
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Tag, Textarea, Tooltip, MessagePlugin } from 'tdesign-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getConfigCategories, getConfigsByCategory, updateConfig, resetCategoryConfig,
  exportAllConfigs, type ConfigItem, type ConfigCategory,
} from '@/api/system';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import { CheckIcon, ChevronDownIcon, CloseIcon, EditIcon, FolderOpenIcon, InfoCircleFilledIcon, MailIcon, NotificationIcon, RefreshIcon, SaveIcon, ServerIcon, SettingIcon, ShieldErrorFilledIcon } from 'tdesign-icons-react';

/** 分类图标映射 */
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  general: <SettingIcon />,
  email: <MailIcon />,
  notification: <NotificationIcon />,
  security: <ShieldErrorFilledIcon />,
  storage: <ServerIcon />,
};

const SystemConfigPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态管理 =====
  const [tabValue, setTabValue] = useState<number>(0);
  const [editMode, setEditMode] = useState<Record<string, boolean>>({});
  const [editValues, setEditValues] = useState<Record<string, any>>({});

  // ===== 数据查询 =====
  const { data: categoriesData, isLoading: categoriesLoading } = useQuery({
    queryKey: ['configCategories'],
    queryFn: getConfigCategories,
  });

  const categories: ConfigCategory[] = categoriesData?.data?.data ?? [];
  const currentCategory = categories[tabValue]?.key || 'general';

  const { data: configsData, isLoading: configsLoading, refetch } = useQuery({
    queryKey: ['configs', currentCategory],
    queryFn: () => getConfigsByCategory(currentCategory),
    enabled: !!currentCategory,
  });

  const configs: ConfigItem[] = configsData?.data?.data ?? [];

  // ===== Mutations =====
  const updateConfigMut = useMutation({
    mutationFn: ({ category, key, value }: { category: string; key: string; value: any }) =>
      updateConfig(category, key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configs'] });
      MessagePlugin.success('配置已更新');
      setEditMode({});
      setEditValues({});
    },
    onError: () => {
      MessagePlugin.error('更新失败');
    },
  });

  const resetConfigMut = useMutation({
    mutationFn: resetCategoryConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configs'] });
      MessagePlugin.success('配置已重置');
    },
  });

  const exportConfigMut = useMutation({
    mutationFn: exportAllConfigs,
    onSuccess: (data: any) => {
      const blob = new Blob([JSON.stringify(data.data?.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'system-config.json';
      a.click();
      URL.revokeObjectURL(url);
      MessagePlugin.success('配置已导出');
    },
  });

  // ===== 统计数据 =====
  const stats = useMemo(() => {
    const totalConfigs = configs.length;
    const sensitiveConfigs = configs.filter(c => c.is_sensitive).length;
    const modifiedConfigs = Object.keys(editMode).length;
    return { totalConfigs, sensitiveConfigs, modifiedConfigs };
  }, [configs, editMode]);

  // ===== ECharts配置 =====
  const configChartOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, right: 10, top: 20 },
    series: [{
      name: '配置分类',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
      labelLine: { show: false },
      data: categories.map((cat, index) => ({
        value: index === tabValue ? 1 : 0.5,
        name: cat.name,
        itemStyle: {
          color: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b'][index % 5],
          opacity: index === tabValue ? 1 : 0.6,
        },
      })),
    }],
  }), [categories, tabValue]);

  // ===== 事件处理 =====
  const handleEdit = useCallback((key: string, value: any) => {
    setEditMode(prev => ({ ...prev, [key]: true }));
    setEditValues(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleCancelEdit = useCallback((key: string) => {
    setEditMode(prev => ({ ...prev, [key]: false }));
    setEditValues(prev => {
      const newValues = { ...prev };
      delete newValues[key];
      return newValues;
    });
  }, []);

  const handleSave = useCallback((key: string) => {
    const value = editValues[key];
    if (value !== undefined) {
      updateConfigMut.mutate({ category: currentCategory, key, value });
    }
  }, [editValues, currentCategory, updateConfigMut]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // ===== 渲染配置项 =====
  const renderConfigItem = (config: ConfigItem) => {
    const isEditing = editMode[config.key];
    const editValue = editValues[config.key];
    const isBoolean = typeof config.value === 'boolean';
    const isNumber = typeof config.value === 'number';
    const isArray = Array.isArray(config.value);

    return (
      <div className="rounded-xl bg-white border border-gray-200" key={config.key}>
        <div className="p-4">
          <div className="flex flex-row items-start justify-between">
            <div className="flex-1">
              <div className="flex flex-row items-center gap-2">
                <span className="text-sm font-semibold text-gray-800">
                  {config.description || config.key}
                </span>
                {config.is_sensitive && (
                  <Tag theme="warning" variant="outline">敏感</Tag>
                )}
              </div>
              <span className="text-xs text-gray-500">
                配置键: {config.key}
              </span>

              {isEditing ? (
                <div className="flex flex-row items-center gap-2 mt-2">
                  {isBoolean ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className={`w-10 h-5 rounded-full relative transition-colors ${editValue ? 'bg-blue-500' : 'bg-gray-300'}`}
                        onClick={() => setEditValues(prev => ({ ...prev, [config.key]: !prev[config.key] }))}
                      >
                        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${editValue ? 'translate-x-5' : ''}`} />
                      </button>
                      <span className="text-sm text-gray-600">{editValue ? '启用' : '禁用'}</span>
                    </div>
                  ) : isNumber ? (
                    <Input
                      type="number"
                      value={String(editValue)}
                      onChange={(val) => setEditValues(prev => ({ ...prev, [config.key]: Number(val) }))}
                    />
                  ) : isArray ? (
                    <Input
                      value={Array.isArray(editValue) ? editValue.join(', ') : String(editValue)}
                      onChange={(val) => setEditValues(prev => ({ ...prev, [config.key]: String(val).split(',').map((s: string) => s.trim()) }))}
                      tips="多个值用逗号分隔"
                    />
                  ) : (
                    <Input
                      value={config.is_sensitive ? '' : String(editValue)}
                      onChange={(val) => setEditValues(prev => ({ ...prev, [config.key]: val }))}
                      type={config.is_sensitive ? 'password' : 'text'}
                      placeholder={config.is_sensitive ? '请输入新密码' : ''}
                    />
                  )}
                  <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => handleSave(config.key)}>
                    <CheckIcon />
                  </span>
                  <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-gray-500" onClick={() => handleCancelEdit(config.key)}>
                    <CloseIcon />
                  </span>
                </div>
              ) : (
                <div className="flex flex-row items-center gap-2 mt-1">
                  {isBoolean ? (
                    <Tag theme={config.value ? 'success' : 'default'}>
                      {config.value ? '已启用' : '已禁用'}
                    </Tag>
                  ) : isArray ? (
                    <div className="flex flex-row gap-1 flex-wrap">
                      {(config.value as string[]).map((item, index) => (
                        <Tag key={index} variant="outline">{item}</Tag>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-gray-600">
                      {config.is_sensitive ? '********' : String(config.value)}
                    </span>
                  )}
                </div>
              )}
            </div>
            {!isEditing && (
              <Tooltip content="编辑">
                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-gray-500" onClick={() => handleEdit(config.key, config.value)}>
                  <EditIcon />
                </span>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <PageContainer>
      <PageHeader
        title="系统配置"
        subtitle="管理系统参数、邮件、通知、安全等配置"
        breadcrumbs={[homeBreadcrumb]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
          { icon: <FolderOpenIcon />, onClick: () => exportConfigMut.mutate(), tooltip: '导出配置' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="配置项总数" value={stats.totalConfigs} icon={<SettingIcon />} color="primary" />
        <MetricsCard title="敏感配置" value={stats.sensitiveConfigs} icon={<ShieldErrorFilledIcon />} color="warning" />
        <MetricsCard title="待保存修改" value={stats.modifiedConfigs} icon={<EditIcon />} color="info" />
        <MetricsCard title="配置分类" value={categories.length} icon={<InfoCircleFilledIcon />} color="success" />
      </StatGrid>

      {/* ECharts图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="配置分类分布" option={configChartOption} height={300} />
        <PageSection title="配置管理说明">
          <div className="flex flex-col gap-2">
            <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <InfoCircleFilledIcon className="text-blue-500 mt-0.5" />
              <span className="text-sm text-blue-700">修改配置后请点击保存按钮生效。敏感配置（如密码）修改后将显示为星号。</span>
            </div>
            <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <ShieldErrorFilledIcon className="text-yellow-500 mt-0.5" />
              <span className="text-sm text-yellow-700">安全配置修改可能影响系统访问，请谨慎操作。</span>
            </div>
            <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
              <CheckIcon className="text-green-500 mt-0.5" />
              <span className="text-sm text-green-700">所有配置修改都会记录在操作日志中，便于审计追踪。</span>
            </div>
          </div>
        </PageSection>
      </div>

      {/* 配置分类标签页 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200 overflow-x-auto">
          {categories.map((cat, index) => (
            <button
              key={cat.key}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                tabValue === index
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setTabValue(index)}
            >
              {CATEGORY_ICONS[cat.key] || <SettingIcon />}
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* 配置内容 */}
      {configsLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : (
        <div>
          <div className="flex flex-row justify-between items-center mb-4">
            <div>
              <h3 className="text-base font-semibold text-gray-800">
                {categories[tabValue]?.name || '配置'}
              </h3>
              <span className="text-xs text-gray-600">
                {categories[tabValue]?.description}
              </span>
            </div>
            <Button
              variant="outline"
              icon={<RefreshIcon />}
              onClick={() => resetConfigMut.mutate(currentCategory)}
              theme="warning"
            >
              重置为默认
            </Button>
          </div>

          <div className="flex flex-col gap-3">
            {configs.map(renderConfigItem)}
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default SystemConfigPage;
