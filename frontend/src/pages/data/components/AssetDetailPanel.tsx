/**
 * AssetDetailPanel - 数据资产详情面板组件
 * 资产详情弹窗 + 发布确认弹窗 + 新建资产弹窗
 */
import React from 'react';
import { Button, Dialog, Input, Select, Tag, Textarea } from 'tdesign-react';
import {
  CheckCircleFilledIcon,
} from 'tdesign-icons-react';
import type { DataAsset } from '@/types/api';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import { CATEGORY_OPTIONS, SENSITIVITY_OPTIONS } from './AssetStats';

/** 分类选择选项 */
const CATEGORY_SELECT_OPTIONS = CATEGORY_OPTIONS.map((opt) => ({
  value: opt.value,
  label: `${opt.icon} ${opt.label}`,
}));

/** 资产表单数据 */
export interface AssetFormData {
  name: string;
  asset_code: string;
  asset_type: string;
  category: string;
  sensitivity_level: string;
  description: string;
}

export const INITIAL_FORM: AssetFormData = {
  name: '',
  asset_code: '',
  asset_type: 'table',
  category: '发电',
  sensitivity_level: '4',
  description: '',
};

/** 获取分类图标 */
const getCategoryIcon = (category: string) => {
  const cat = CATEGORY_OPTIONS.find((c) => c.value === category);
  return cat?.icon || '📊';
};

/** 获取分类颜色 */
const getCategoryColor = (category: string) => {
  const cat = CATEGORY_OPTIONS.find((c) => c.value === category);
  return cat?.color || '#6b7280';
};

/** 敏感级别颜色映射 - 四级安全等级 */
const sensitivityColor = (level: string): 'success' | 'info' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'success' | 'info' | 'warning' | 'error'> = {
    '1': 'error',     // 核心
    '2': 'warning',   // 重要
    '3': 'info',      // 一般
    '4': 'success',   // 公开
    // 兼容旧值
    public: 'success',
    internal: 'info',
    confidential: 'warning',
    secret: 'error',
  };
  return map[level] ?? 'default';
};

interface AssetDetailPanelProps {
  // 新建弹窗
  formOpen: boolean;
  formData: AssetFormData;
  onFormClose: () => void;
  onFormSubmit: () => void;
  onFieldChange: (field: keyof AssetFormData, value: string) => void;
  createPending: boolean;

  // 详情弹窗
  detailOpen: boolean;
  detailItem: DataAsset | null;
  onDetailClose: () => void;
  onPublishFromDetail: (item: DataAsset) => void;

  // 发布确认弹窗
  publishTarget: DataAsset | null;
  onPublishConfirm: () => void;
  onPublishCancel: () => void;
  publishPending: boolean;
}

/** AssetDetailPanel 组件 */
const AssetDetailPanel: React.FC<AssetDetailPanelProps> = ({
  formOpen,
  formData,
  onFormClose,
  onFormSubmit,
  onFieldChange,
  createPending,
  detailOpen,
  detailItem,
  onDetailClose,
  onPublishFromDetail,
  publishTarget,
  onPublishConfirm,
  onPublishCancel,
  publishPending,
}) => {
  return (
    <>
      {/* 新建弹窗 */}
      <Dialog
        header="新建数据资产"
        visible={formOpen}
        onClose={onFormClose}
        onConfirm={onFormSubmit}
        confirmBtn={{ disabled: !formData.name || !formData.asset_code || createPending, content: '创建' }}
        cancelBtn={{ content: '取消' }}
        destroyOnClose
      >
        <div className="flex flex-col gap-4 py-2">
          <div>
            <label className="block text-sm text-gray-600 mb-1">资产名称 *</label>
            <Input
              value={formData.name}
              onChange={(val) => onFieldChange('name', String(val))}
              placeholder="请输入资产名称"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">资产编码 *</label>
            <Input
              value={formData.asset_code}
              onChange={(val) => onFieldChange('asset_code', String(val))}
              placeholder="请输入资产编码"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">分类</label>
            <Select
              value={formData.category}
              options={CATEGORY_SELECT_OPTIONS}
              onChange={(val) => onFieldChange('category', String(val))}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">敏感级别</label>
            <Select
              value={formData.sensitivity_level}
              options={SENSITIVITY_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label }))}
              onChange={(val) => onFieldChange('sensitivity_level', String(val))}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">描述</label>
            <Textarea
              value={formData.description}
              onChange={(val: string) => onFieldChange('description', val)}
              placeholder="请输入描述"
              rows={3}
            />
          </div>
        </div>
      </Dialog>

      {/* 资产详情弹窗 */}
      <Dialog
        header={
          <div className="flex items-center gap-2">
            <span className="text-xl">{detailItem ? getCategoryIcon(detailItem.category) : '📊'}</span>
            <span>资产详情 - {detailItem?.name}</span>
          </div>
        }
        visible={detailOpen}
        onClose={onDetailClose}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onDetailClose}>关闭</Button>
            {detailItem && detailItem.status !== 'published' && (
              <Button
                theme="primary"
                icon={<CheckCircleFilledIcon />}
                onClick={() => { onDetailClose(); onPublishFromDetail(detailItem); }}
              >
                发布到目录
              </Button>
            )}
          </div>
        }
        destroyOnClose
      >
        {detailItem && (
          <div className="flex flex-col gap-4 py-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">资产编码</p>
                <p className="font-mono">{detailItem.asset_code}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">资产类型</p>
                <p>{detailItem.asset_type}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">数据分类</p>
                <Tag
                  variant="light"
                  style={{
                    backgroundColor: getCategoryColor(detailItem.category) + '20',
                    color: getCategoryColor(detailItem.category),
                  }}
                >
                  {CATEGORY_OPTIONS.find((o) => o.value === detailItem.category)?.label ?? detailItem.category}
                </Tag>
              </div>
              <div>
                <p className="text-xs text-gray-500">敏感级别</p>
                <StatusTag
                  status={SENSITIVITY_OPTIONS.find((o) => o.value === detailItem.sensitivity_level)?.label ?? detailItem.sensitivity_level}
                  color={sensitivityColor(detailItem.sensitivity_level)}
                />
              </div>
              <div>
                <p className="text-xs text-gray-500">发布状态</p>
                <StatusTag status={detailItem.status} />
              </div>
              <div>
                <p className="text-xs text-gray-500">所属组织</p>
                <p>{detailItem.owner_org_id}</p>
              </div>
              <div className="sm:col-span-2">
                <p className="text-xs text-gray-500">描述</p>
                <p>{detailItem.description || '暂无描述'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">创建时间</p>
                <p>{new Date(detailItem.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">更新时间</p>
                <p>{new Date(detailItem.updated_at).toLocaleString('zh-CN')}</p>
              </div>
            </div>

            <hr className="border-gray-200" />

            <h4 className="font-semibold">元数据信息</h4>
            <div className="rounded-lg bg-gray-50 p-4">
              <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                {JSON.stringify(detailItem.metadata || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Dialog>

      {/* 发布确认弹窗 */}
      <ConfirmDialog
        open={!!publishTarget}
        title="发布到数据目录"
        message={`确定要将资产「${publishTarget?.name ?? ''}」发布到数据目录吗？发布后其他组织可检索和申请使用。`}
        type="info"
        confirmText="发布"
        onConfirm={onPublishConfirm}
        onCancel={onPublishCancel}
        loading={publishPending}
      />
    </>
  );
};

export default AssetDetailPanel;
