/**
 * StatusTag 状态标签组件
 * 基于 tdesign-react Tag 的通用状态展示，内置颜色映射
 * 迁移自 MUI Chip → tdesign-react Tag
 */
import React from 'react';
import { Tag } from 'tdesign-react';

/** Chip 颜色类型（保持原有接口兼容） */
type ChipColor = 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';

/** tdesign-react Tag theme 类型 */
type TagTheme = 'default' | 'primary' | 'warning' | 'danger' | 'success';

/** 状态到颜色的映射规则 */
interface StatusColorRule {
  /** 匹配的关键词列表（小写） */
  keywords: string[];
  /** MUI Chip 颜色 */
  color: ChipColor;
  /** 自定义背景色（覆盖默认） */
  bgColor?: string;
  /** 自定义文字色（覆盖默认） */
  textColor?: string;
}

/** 预定义颜色规则 — 按优先级排列 */
const STATUS_COLOR_RULES: StatusColorRule[] = [
  // 成功/完成/运行
  {
    keywords: ['active', 'running', 'completed', 'success', 'approved', 'published', 'verified', 'healthy', 'valid', 'done', 'paid', 'signed'],
    color: 'success',
  },
  // 警告/待处理
  {
    keywords: ['pending', 'waiting', 'processing', 'warning', 'queued', 'partial', 'progress', 'draft', 'pending_approval', 'billing'],
    color: 'warning',
  },
  // 错误/失败/拒绝
  {
    keywords: ['error', 'failed', 'rejected', 'denied', 'unhealthy', 'invalid', 'expired', 'overdue', 'revoked', 'disputed', 'locked'],
    color: 'error',
  },
  // 信息/初始化
  {
    keywords: ['info', 'new', 'created', 'initialized', 'ready', 'available', 'open', 'subscribed'],
    color: 'info',
  },
  // 禁用/停止/关闭
  {
    keywords: ['inactive', 'disabled', 'stopped', 'closed', 'deactivated', 'offline', 'cancelled', 'settled', 'minted'],
    color: 'default',
  },
  // 安全相关 - 紧急
  {
    keywords: ['critical', 'urgent'],
    color: 'error',
  },
  // 安全相关 - 高危
  {
    keywords: ['high', 'elevated'],
    color: 'warning',
  },
  // 安全相关 - 低危
  {
    keywords: ['low', 'minor'],
    color: 'info',
  },
];

/** 中文状态映射补充 */
const CN_STATUS_MAP: Record<string, string> = {
  '运行中': 'running',
  '已完成': 'completed',
  '成功': 'success',
  '失败': 'failed',
  '待处理': 'pending',
  '处理中': 'processing',
  '已拒绝': 'rejected',
  '已审批': 'approved',
  '已发布': 'published',
  '已验证': 'verified',
  '已撤销': 'revoked',
  '已过期': 'expired',
  '已停用': 'inactive',
  '已激活': 'active',
  '已锁定': 'locked',
  '已结算': 'settled',
  '紧急': 'critical',
  '高危': 'high',
  '中危': 'medium',
  '低危': 'low',
};

/** MUI ChipColor → tdesign Tag theme 映射 */
const CHIP_COLOR_TO_TAG_THEME: Record<ChipColor, TagTheme> = {
  default: 'default',
  primary: 'primary',
  secondary: 'default',
  error: 'danger',
  info: 'primary',
  success: 'success',
  warning: 'warning',
};

/** 圆点颜色映射 */
const DOT_COLOR_MAP: Record<string, string> = {
  success: '#4caf50',
  warning: '#ff9800',
  error: '#f44336',
  info: '#2196f3',
  default: '#9e9e9e',
  primary: '#1976d2',
  danger: '#f44336',
};

/**
 * 根据状态文本推断颜色
 * @param status - 状态文本（英文或中文）
 * @returns ChipColor
 */
function resolveStatusColor(status: string | undefined | null): ChipColor {
  if (!status) return 'default';
  // 先尝试中文映射
  const mappedStatus = CN_STATUS_MAP[status] ?? status;
  const lowerStatus = mappedStatus.toLowerCase();

  for (const rule of STATUS_COLOR_RULES) {
    if (rule.keywords.some((kw) => lowerStatus.includes(kw))) {
      return rule.color;
    }
  }

  return 'default';
}

/**
 * 格式化状态文本显示
 * 将下划线分隔转为可读格式
 */
function formatStatusLabel(status: string | undefined | null): string {
  if (!status) return '未知';
  if (CN_STATUS_MAP[status]) return status;
  return String(status)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface StatusTagProps {
  /** 状态值（英文或中文） */
  status: string | undefined | null;
  /** 强制指定颜色（覆盖自动推断） */
  color?: ChipColor;
  /** 是否显示小圆点图标 */
  showDot?: boolean;
  /** 自定义显示文本（覆盖 status 原文） */
  label?: string;
  /** 自定义尺寸 */
  size?: 'small' | 'medium';
  /** 点击回调 */
  onClick?: () => void;
  /** 自定义 className */
  className?: string;
}

/**
 * StatusTag 组件
 * 自动根据状态文本推断颜色，支持中英文状态
 */
const StatusTag: React.FC<StatusTagProps> = ({
  status,
  color,
  showDot = true,
  label,
  size = 'small',
  onClick,
  className,
}) => {
  const resolvedColor = color ?? resolveStatusColor(status);
  const displayLabel = label ?? formatStatusLabel(status);
  const tagTheme = CHIP_COLOR_TO_TAG_THEME[resolvedColor] ?? 'default';
  const dotColor = DOT_COLOR_MAP[resolvedColor] ?? DOT_COLOR_MAP[tagTheme] ?? '#9e9e9e';

  const dotIcon = showDot ? (
    <span
      style={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        backgroundColor: dotColor,
        display: 'inline-block',
        marginRight: 4,
      }}
    />
  ) : undefined;

  return (
    <Tag
      theme={tagTheme}
      variant="light"
      size={size === 'small' ? 'small' : 'medium'}
      onClick={onClick}
      icon={dotIcon}
      className={className}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      {displayLabel}
    </Tag>
  );
};

export default StatusTag;

/** 导出颜色推断函数供外部使用 */
export { resolveStatusColor, formatStatusLabel };
