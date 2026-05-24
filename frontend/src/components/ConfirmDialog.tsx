/**
 * ConfirmDialog 确认对话框组件
 * 基于 tdesign-react Dialog + Button 的通用确认/取消弹窗
 * 迁移自 MUI → tdesign-react
 */
import React, { useCallback } from 'react';
import { Dialog, Button } from 'tdesign-react';
import {
  InfoCircleFilledIcon,
  ErrorCircleFilledIcon,
  CloseIcon,
  DeleteIcon,
  CheckCircleFilledIcon,
} from 'tdesign-icons-react';

/** 对话框类型 —— 影响图标与按钮颜色 */
export type ConfirmDialogType = 'info' | 'warning' | 'danger' | 'success';

/** 对话框图标映射 */
const TYPE_ICON_MAP: Record<ConfirmDialogType, React.ReactNode> = {
  info: <InfoCircleFilledIcon style={{ fontSize: 40, color: '#2196f3' }} />,
  warning: <ErrorCircleFilledIcon style={{ fontSize: 40, color: '#ff9800' }} />,
  danger: <DeleteIcon style={{ fontSize: 40, color: '#f44336' }} />,
  success: <CheckCircleFilledIcon style={{ fontSize: 40, color: '#4caf50' }} />,
};

/** 确认按钮主题映射 */
const TYPE_BUTTON_THEME_MAP: Record<ConfirmDialogType, 'primary' | 'warning' | 'danger' | 'success'> = {
  info: 'primary',
  warning: 'warning',
  danger: 'danger',
  success: 'success',
};

interface ConfirmDialogProps {
  /** 是否打开 */
  open: boolean;
  /** 标题 */
  title: string;
  /** 描述内容 */
  message: string;
  /** 对话框类型 */
  type?: ConfirmDialogType;
  /** 确认按钮文本 */
  confirmText?: string;
  /** 取消按钮文本 */
  cancelText?: string;
  /** 确认回调 */
  onConfirm: () => void;
  /** 取消/关闭回调 */
  onCancel: () => void;
  /** 确认按钮是否加载中 */
  loading?: boolean;
  /** 是否显示右上角关闭按钮 */
  showCloseButton?: boolean;
  /** 详情列表（显示在描述下方的键值对） */
  details?: Array<{ label: string; value: string }>;
  /** 自定义 className */
  className?: string;
}

/**
 * ConfirmDialog 组件
 * 统一的确认/警告/危险操作弹窗
 */
const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  message,
  type = 'info',
  confirmText = '确认',
  cancelText = '取消',
  onConfirm,
  onCancel,
  loading = false,
  showCloseButton = true,
  details = [],
  className,
}) => {
  /** 处理确认 */
  const handleConfirm = useCallback(() => {
    if (!loading) {
      onConfirm();
    }
  }, [loading, onConfirm]);

  /** 处理取消 */
  const handleCancel = useCallback(() => {
    if (!loading) {
      onCancel();
    }
  }, [loading, onCancel]);

  /** 构建 Dialog footer */
  const renderFooter = () => (
    <div className="flex justify-end gap-2">
      <Button
        theme="default"
        variant="outline"
        onClick={handleCancel}
        disabled={loading}
        style={{ minWidth: 80 }}
      >
        {cancelText}
      </Button>
      <Button
        theme={TYPE_BUTTON_THEME_MAP[type]}
        onClick={handleConfirm}
        loading={loading}
        style={{ minWidth: 80 }}
      >
        {confirmText}
      </Button>
    </div>
  );

  /** 构建 Dialog header */
  const renderHeader = () => (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-3">
        {TYPE_ICON_MAP[type]}
        <span className="text-lg font-semibold">{title}</span>
      </div>
      {showCloseButton && (
        <Button
          variant="text"
          theme="default"
          icon={<CloseIcon />}
          onClick={handleCancel}
          disabled={loading}
          size="small"
        />
      )}
    </div>
  );

  return (
    <Dialog
      visible={open}
      header={renderHeader()}
      onClose={handleCancel}
      footer={renderFooter()}
      destroyOnClose
      className={className}
      style={{ maxWidth: '520px' }}
    >
      <div className="pt-2">
        <p
          className="text-sm leading-relaxed whitespace-pre-line m-0"
          style={{ color: 'var(--td-text-color-primary, rgba(0,0,0,0.87))' }}
        >
          {message}
        </p>

        {/* 详情列表 */}
        {details.length > 0 && (
          <div
            className="mt-4 p-4 rounded-md"
            style={{
              backgroundColor: '#f5f5f5',
              border: '1px solid #e0e0e0',
            }}
          >
            {details.map((detail, index) => (
              <div
                key={`detail-${index}`}
                className="flex justify-between py-1.5"
                style={{
                  borderBottom:
                    index < details.length - 1 ? '1px solid #e0e0e0' : 'none',
                }}
              >
                <span className="text-sm text-gray-500">{detail.label}</span>
                <span className="text-sm font-medium">{detail.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Dialog>
  );
};

export default ConfirmDialog;
