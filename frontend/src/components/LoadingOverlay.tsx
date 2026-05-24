/**
 * LoadingOverlay 全屏/局部加载遮罩组件
 * 基于 tdesign-react Loading
 * 迁移自 MUI Backdrop + CircularProgress → tdesign-react Loading
 */
import React from 'react';
import { Loading } from 'tdesign-react';

interface LoadingOverlayProps {
  /** 是否显示加载 */
  open: boolean;
  /** 加载提示文字 */
  message?: string;
  /** 是否全屏遮罩（否则相对定位） */
  fullscreen?: boolean;
  /** 进度值（0-100），不传则为不确定进度 */
  progress?: number;
  /** 自定义 className */
  className?: string;
  /** 子组件（当非全屏时，遮罩覆盖在子组件上方） */
  children?: React.ReactNode;
}

/**
 * LoadingOverlay 组件
 * 支持全屏和局部遮罩两种模式
 * - 全屏模式：覆盖整个视口，z-index 最高
 * - 局部模式：覆盖父容器，需要父容器设置 position: relative
 */
const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  open,
  message,
  fullscreen = false,
  progress,
  className,
  children,
}) => {
  /** 渲染加载内容 */
  const renderLoadingContent = (): React.ReactNode => (
    <div
      className={`flex flex-col items-center gap-4 p-6 ${
        fullscreen ? '' : 'bg-white rounded-lg shadow-lg'
      }`}
    >
      <Loading
        size="large"
        loading={true}
        delay={0}
        showOverlay={false}
        text={message || undefined}
      >
        <div style={{ minWidth: 52, minHeight: 52 }} />
      </Loading>
      {progress !== undefined && (
        <span className="text-sm font-bold text-gray-500">
          {`${Math.round(progress)}%`}
        </span>
      )}
      {message && !progress && (
        <span
          className="text-sm text-gray-500 text-center"
          style={{ maxWidth: 240, lineHeight: 1.5 }}
        >
          {message}
        </span>
      )}
    </div>
  );

  /** 全屏模式 */
  if (fullscreen) {
    if (!open) return null;
    return (
      <div
        className={`fixed inset-0 flex items-center justify-center ${className ?? ''}`}
        style={{
          zIndex: 1301,
          backgroundColor: 'rgba(0, 0, 0, 0.45)',
          backdropFilter: 'blur(4px)',
        }}
      >
        {renderLoadingContent()}
      </div>
    );
  }

  /** 局部模式 */
  return (
    <div className="relative">
      {children}
      {open && (
        <div
          className={`absolute inset-0 flex items-center justify-center rounded ${
            className ?? ''
          }`}
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.72)',
            zIndex: 1050,
            backdropFilter: 'blur(2px)',
          }}
        >
          {renderLoadingContent()}
        </div>
      )}
    </div>
  );
};

export default LoadingOverlay;
