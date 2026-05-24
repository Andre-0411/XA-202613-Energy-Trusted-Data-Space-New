// @ts-nocheck
/**
 * PageHeader 通用页头组件
 * 标题 + 面包屑导航 + 右侧操作区
 * 迁移自 MUI → tdesign-react + Tailwind CSS
 */
import React, { useState } from 'react';
import { Button, Breadcrumb } from 'tdesign-react';
import {
  ChevronRightIcon,
  HomeIcon,
  MoreIcon,
} from 'tdesign-icons-react';

/** 面包屑项 */
export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
}

/** 操作按钮 */
export interface PageAction {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'contained' | 'outlined' | 'text';
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';
  disabled?: boolean;
}

interface PageHeaderProps {
  /** 页面标题 */
  title: string;
  /** 页面副标题 */
  subtitle?: string;
  /** 面包屑导航项 */
  breadcrumbs?: BreadcrumbItem[];
  /** 主要操作按钮列表 */
  actions?: PageAction[];
  /** 单个操作按钮（快捷写法，自动包装为 actions 数组） */
  action?: React.ReactNode;
  /** 图标操作按钮（如刷新、设置等） */
  iconActions?: Array<{
    icon: React.ReactNode;
    onClick: () => void;
    tooltip?: string;
    disabled?: boolean;
  }>;
  /** 右侧自定义内容（如状态指示器） */
  rightContent?: React.ReactNode;
  /** 自定义 className */
  className?: string;
}

/** MUI variant → tdesign-react theme/variant 映射 */
function mapButtonVariant(
  variant?: 'contained' | 'outlined' | 'text',
): { theme?: string; variant?: string } {
  switch (variant) {
    case 'contained':
      return { theme: 'primary' };
    case 'outlined':
      return { theme: 'default', variant: 'outline' };
    case 'text':
      return { variant: 'text' };
    default:
      return { theme: 'primary' };
  }
}

/** MUI color → tdesign-react theme 映射 */
function mapButtonColor(
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success',
): string {
  switch (color) {
    case 'primary':
      return 'primary';
    case 'secondary':
      return 'default';
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'default';
    case 'success':
      return 'success';
    default:
      return 'primary';
  }
}

/**
 * PageHeader 组件
 * 提供统一的页头布局：标题行 + 面包屑 + 操作按钮
 */
const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs = [],
  actions = [],
  action,
  iconActions = [],
  rightContent,
  className,
}) => {
  /** 如果传了 action（单个 ReactNode），渲染到标题右侧 */
  const actionNode = action ?? null;
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 900;
  const [actionsExpanded, setActionsExpanded] = useState(false);

  /** 渲染面包屑（移动端隐藏） */
  const renderBreadcrumbs = (): React.ReactNode => {
    if (breadcrumbs.length === 0 || isMobile) return null;

    const breadcrumbItems = breadcrumbs.map((item, index) => {
      const isLast = index === breadcrumbs.length - 1;
      return {
        content: (
          <span className="flex items-center gap-1">
            {item.icon && (
              <span className="flex items-center">{item.icon}</span>
            )}
            {item.href && !isLast ? (
              <a
                href={item.href}
                className="no-underline hover:text-blue-600"
                style={{
                  color: 'inherit',
                  fontWeight: isLast ? 600 : 400,
                  fontSize: '0.875rem',
                }}
              >
                {item.label}
              </a>
            ) : (
              <span
                style={{
                  fontWeight: isLast ? 600 : 400,
                  fontSize: '0.875rem',
                }}
              >
                {item.label}
              </span>
            )}
          </span>
        ),
        href: !isLast && item.href ? item.href : undefined,
      };
    });

    return (
      <div className="mb-1">
        <Breadcrumb
          separator={<ChevronRightIcon style={{ fontSize: '12px' }} />}
          maxItemWidth={160}
        >
          {breadcrumbItems.map((item, index) => (
            <Breadcrumb.BreadcrumbItem key={`bc-${index}`} href={item.href}>
              {item.content}
            </Breadcrumb.BreadcrumbItem>
          ))}
        </Breadcrumb>
      </div>
    );
  };

  /** 渲染操作按钮 */
  const renderActions = (): React.ReactNode => {
    if (actions.length === 0 && iconActions.length === 0 && !rightContent) return null;

    /* 移动端：折叠操作区 */
    if (isMobile) {
      const allActions = [...actions, ...iconActions];
      if (allActions.length === 0 && !rightContent) return null;

      return (
        <div>
          <Button
            variant="text"
            theme="primary"
            icon={<MoreIcon />}
            onClick={() => setActionsExpanded(!actionsExpanded)}
            style={{ minWidth: 44, minHeight: 44 }}
          />
          {actionsExpanded && (
            <div className="mt-1 flex flex-col items-end gap-2">
              {rightContent}
              {actions.map((act, index) => (
                <Button
                  key={`action-${index}`}
                  theme={mapButtonColor(act.color)}
                  variant={mapButtonVariant(act.variant).variant as any}
                  onClick={() => {
                    act.onClick();
                    setActionsExpanded(false);
                  }}
                  disabled={act.disabled}
                  icon={act.icon}
                  block
                  style={{ minHeight: 44 }}
                >
                  {act.label}
                </Button>
              ))}
              {iconActions.length > 0 && (
                <div className="flex gap-1">
                  {iconActions.map((iconAction, index) => (
                    <Button
                      key={`icon-action-${index}`}
                      variant="text"
                      theme="primary"
                      icon={iconAction.icon}
                      onClick={() => {
                        iconAction.onClick();
                        setActionsExpanded(false);
                      }}
                      disabled={iconAction.disabled}
                      title={iconAction.tooltip ?? ''}
                      style={{ minWidth: 44, minHeight: 44 }}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    /* 桌面端：水平排列 */
    return (
      <div className="flex items-center gap-2">
        {rightContent}
        {actions.map((act, index) => {
          const variantInfo = mapButtonVariant(act.variant);
          return (
            <Button
              key={`action-${index}`}
              theme={mapButtonColor(act.color)}
              variant={variantInfo.variant as any}
              onClick={act.onClick}
              disabled={act.disabled}
              icon={act.icon}
              size="small"
            >
              {act.label}
            </Button>
          );
        })}
        {iconActions.map((iconAction, index) => (
          <Button
            key={`icon-action-${index}`}
            variant="text"
            theme="primary"
            icon={iconAction.icon}
            onClick={iconAction.onClick}
            disabled={iconAction.disabled}
            title={iconAction.tooltip ?? ''}
            size="small"
          />
        ))}
      </div>
    );
  };

  return (
    <div className={`flex flex-col mb-6 ${className ?? ''}`}>
      {renderBreadcrumbs()}
      <div className="flex flex-wrap items-start sm:items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h5 className="text-xl sm:text-2xl font-bold text-gray-900 truncate m-0">
            {title}
          </h5>
          {subtitle && !isMobile && (
            <span className="text-sm text-gray-500 mt-1 block">
              {subtitle}
            </span>
          )}
        </div>
        {actionNode && (
          <div className="flex items-center gap-2">
            {actionNode}
          </div>
        )}
        {!actionNode && renderActions()}
      </div>
    </div>
  );
};

/** 生成标准首页面包屑 */
export const homeBreadcrumb: BreadcrumbItem = {
  label: '首页',
  href: '/',
  icon: <HomeIcon />,
};

export default PageHeader;
