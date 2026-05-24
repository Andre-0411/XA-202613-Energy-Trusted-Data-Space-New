/**
 * FormDialog 通用表单弹窗组件
 * 基于 tdesign-react Dialog + Form 的通用表单弹窗
 */
import React, { useState } from 'react';
import { Dialog, Button, Form, Input, Select, MessagePlugin } from 'tdesign-react';

interface FormField {
  name: string;
  label: string;
  type: 'text' | 'select' | 'textarea' | 'number';
  placeholder?: string;
  required?: boolean;
  options?: Array<{ label: string; value: any }>;
  rules?: any[];
}

interface FormDialogProps {
  visible: boolean;
  title: string;
  fields: FormField[];
  initialValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onCancel: () => void;
  submitText?: string;
  loading?: boolean;
  width?: number;
}

/**
 * FormDialog 组件
 * 提供可配置的表单弹窗，支持多种字段类型
 */
const FormDialog: React.FC<FormDialogProps> = ({
  visible,
  title,
  fields,
  initialValues = {},
  onSubmit,
  onCancel,
  submitText = '提交',
  loading = false,
  width = 640,
}) => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    try {
      const result = await form.validate();
      const values = (result && typeof result === 'object' && !Array.isArray(result)) ? result : {};
      setSubmitting(true);
      await onSubmit(values as Record<string, any>);
      MessagePlugin.success('操作成功');
      form.reset();
    } catch (err) {
      // 表单验证失败，不做额外处理
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    form.reset();
    onCancel();
  };

  /** 渲染表单项 */
  const renderField = (field: FormField) => {
    switch (field.type) {
      case 'text':
        return <Input placeholder={field.placeholder} />;
      case 'textarea':
        return <Input placeholder={field.placeholder} />;
      case 'number':
        return <Input type="number" placeholder={field.placeholder} />;
      case 'select':
        return (
          <Select
            options={field.options || []}
            placeholder={field.placeholder}
            clearable
          />
        );
      default:
        return <Input placeholder={field.placeholder} />;
    }
  };

  /** 构建验证规则 */
  const buildRules = (field: FormField) => {
    if (field.rules) return field.rules;
    if (field.required) {
      return [{ required: true, message: `请输入${field.label}` }];
    }
    return undefined;
  };

  return (
    <Dialog
      visible={visible}
      header={title}
      onClose={handleCancel}
      onConfirm={handleConfirm}
      confirmLoading={submitting || loading}
      confirmBtn={submitText}
      cancelBtn="取消"
      width={width}
      destroyOnClose
      preventScrollThrough
    >
      <Form
        form={form}
        initialData={initialValues}
        labelWidth={100}
        layout="vertical"
      >
        {fields.map((field) => (
          <Form.FormItem
            key={field.name}
            label={field.label}
            name={field.name}
            rules={buildRules(field)}
          >
            {renderField(field)}
          </Form.FormItem>
        ))}
      </Form>
    </Dialog>
  );
};

export default FormDialog;
