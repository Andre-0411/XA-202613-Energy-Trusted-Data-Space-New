/**
 * MetadataEditor - 元数据编辑器组件
 * 新建/编辑元数据表单弹窗
 */
import React from 'react';
import { Button, Dialog, Input, Select, Textarea } from 'tdesign-react';

/** 元数据表单数据 */
export interface MetadataFormData {
  asset_id: string;
  standard: string;
  schema_version: string;
  fields_json: string;
}

export const INITIAL_FORM: MetadataFormData = {
  asset_id: '',
  standard: 'energy-gb',
  schema_version: '1.0.0',
  fields_json: '[]',
};

const STANDARD_OPTIONS = [
  { value: 'energy-gb', label: '能源国标' },
  { value: 'dublin-core', label: 'Dublin Core' },
  { value: 'custom', label: '自定义' },
];

interface MetadataEditorProps {
  formOpen: boolean;
  editingId: string | null;
  formData: MetadataFormData;
  onClose: () => void;
  onSubmit: () => void;
  onFieldChange: (field: keyof MetadataFormData, value: string) => void;
  submitPending: boolean;
}

/** MetadataEditor 组件 */
const MetadataEditor: React.FC<MetadataEditorProps> = ({
  formOpen,
  editingId,
  formData,
  onClose,
  onSubmit,
  onFieldChange,
  submitPending,
}) => {
  return (
    <Dialog
      header={editingId ? '编辑元数据' : '新建元数据'}
      visible={formOpen}
      onClose={onClose}
      onConfirm={onSubmit}
      confirmBtn={{ disabled: !formData.asset_id || submitPending, content: editingId ? '保存' : '创建' }}
      cancelBtn={{ content: '取消' }}
      destroyOnClose
    >
      <div className="flex flex-col gap-4 py-2">
        <div>
          <label className="block text-sm text-gray-600 mb-1">资产 ID *</label>
          <Input
            value={formData.asset_id}
            onChange={(val) => onFieldChange('asset_id', String(val))}
            placeholder="请输入资产 ID"
            disabled={!!editingId}
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">标准</label>
          <Select
            value={formData.standard}
            options={STANDARD_OPTIONS}
            onChange={(val) => onFieldChange('standard', String(val))}
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Schema 版本</label>
          <Input
            value={formData.schema_version}
            onChange={(val) => onFieldChange('schema_version', String(val))}
            placeholder="请输入版本号"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">字段定义 (JSON)</label>
          <Textarea
            value={formData.fields_json}
            onChange={(val) => onFieldChange('fields_json', String(val))}
            placeholder='[{"name": "field1", "type": "string"}]'
            rows={5}
          />
        </div>
      </div>
    </Dialog>
  );
};

export default MetadataEditor;
export { STANDARD_OPTIONS };
