/**
 * 通知中心页面
 * 展示系统通知、已读/未读状态管理、通知筛选等功能
 * 集成WebSocket实时通知推送
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Tooltip, Checkbox, MessagePlugin } from 'tdesign-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getNotifications, getUnreadCount, markAsRead, markAllAsRead,
  batchDeleteNotifications, batchMarkAsRead,
  type Notification,
} from '@/api/system';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import WebSocketStatus from '@/components/common/WebSocketStatus';
import { useNotifications } from '@/hooks/useNotifications';
import {
  TimeIcon, CheckCircleFilledIcon, DeleteIcon, CheckDoubleIcon,
  ErrorCircleFilledIcon, ErrorIcon, InfoCircleFilledIcon, MailIcon,
  NotificationIcon, NotificationFilledIcon, RefreshIcon, SearchIcon,
} from 'tdesign-icons-react';

/** 通知类型配置 */
const NOTIFICATION_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  info: { icon: <InfoCircleFilledIcon />, color: '#2196f3', label: '信息' },
  warning: { icon: <ErrorCircleFilledIcon />, color: '#ff9800', label: '警告' },
  error: { icon: <ErrorIcon />, color: '#f44336', label: '错误' },
  success: { icon: <CheckCircleFilledIcon />, color: '#4caf50', label: '成功' },
};

/** 优先级配置 */
const PRIORITY_CONFIG: Record<string, { color: string; label: string }> = {
  low: { color: '#9e9e9e', label: '低' },
  normal: { color: '#2196f3', label: '普通' },
  high: { color: '#ff9800', label: '高' },
  urgent: { color: '#f44336', label: '紧急' },
};

/** 分类配置 */
const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ReactNode }> = {
  system: { label: '系统通知', icon: <NotificationIcon /> },
  task: { label: '任务通知', icon: <CheckCircleFilledIcon /> },
  security: { label: '安全告警', icon: <ErrorCircleFilledIcon /> },
  billing: { label: '账单通知', icon: <InfoCircleFilledIcon /> },
};

const TYPE_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'info', label: '信息' },
  { value: 'warning', label: '警告' },
  { value: 'error', label: '错误' },
  { value: 'success', label: '成功' },
];

const CATEGORY_OPTIONS = [
  { value: 'all', label: '全部分类' },
  { value: 'system', label: '系统通知' },
  { value: 'task', label: '任务通知' },
  { value: 'security', label: '安全告警' },
  { value: 'billing', label: '账单通知' },
];

const PRIORITY_OPTIONS = [
  { value: 'all', label: '全部优先级' },
  { value: 'low', label: '低' },
  { value: 'normal', label: '普通' },
  { value: 'high', label: '高' },
  { value: 'urgent', label: '紧急' },
];

const NotificationCenterPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== WebSocket实时通知 =====
  const { wsStatus, isConnected, reconnect } = useNotifications({ enabled: true });

  // ===== 状态管理 =====
  const [tabValue, setTabValue] = useState<number>(0);
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);

  // ===== 数据查询 =====
  const { data: notificationsData, isLoading, refetch } = useQuery({
    queryKey: ['notifications', tabValue, filterType, filterCategory, filterPriority],
    queryFn: () => getNotifications({
      page: 1,
      page_size: 50,
      is_read: tabValue === 0 ? undefined : tabValue === 1 ? false : true,
      type: filterType !== 'all' ? filterType : undefined,
      category: filterCategory !== 'all' ? filterCategory : undefined,
      priority: filterPriority !== 'all' ? filterPriority : undefined,
    }),
  });

  const { data: unreadData } = useQuery({
    queryKey: ['unreadCount'],
    queryFn: getUnreadCount,
    refetchInterval: 30000,
  });

  const notifications: Notification[] = notificationsData?.data?.data?.items ?? [];
  const totalCount: number = notificationsData?.data?.data?.total ?? 0;
  const unreadCount: number = unreadData?.data?.data?.unread_count ?? 0;

  // ===== Mutations =====
  const markReadMut = useMutation({
    mutationFn: markAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
      MessagePlugin.success('已标记为已读');
    },
  });

  const markAllReadMut = useMutation({
    mutationFn: markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
      MessagePlugin.success('已全部标记为已读');
    },
  });

  const batchDeleteMut = useMutation({
    mutationFn: batchDeleteNotifications,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
      setSelectedIds([]);
      MessagePlugin.success('删除成功');
    },
  });

  const batchReadMut = useMutation({
    mutationFn: batchMarkAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
      setSelectedIds([]);
      MessagePlugin.success('已批量标记为已读');
    },
  });

  // ===== 筛选后的通知 =====
  const filteredNotifications = useMemo(() => {
    if (!searchKeyword.trim()) return notifications;
    const keyword = searchKeyword.toLowerCase();
    return notifications.filter(n =>
      n.title.toLowerCase().includes(keyword) ||
      n.content.toLowerCase().includes(keyword) ||
      n.sender.toLowerCase().includes(keyword)
    );
  }, [notifications, searchKeyword]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    total: totalCount,
    unread: unreadCount,
    today: notifications.filter(n => {
      const today = new Date().toDateString();
      return new Date(n.created_at).toDateString() === today;
    }).length,
    urgent: notifications.filter(n => n.priority === 'urgent' && !n.is_read).length,
  }), [notifications, totalCount, unreadCount]);

  // ===== ECharts配置 =====
  const typeChartOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, right: 10, top: 20 },
    series: [{
      name: '通知类型',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: notifications.filter(n => n.type === 'info').length, name: '信息', itemStyle: { color: '#2196f3' } },
        { value: notifications.filter(n => n.type === 'warning').length, name: '警告', itemStyle: { color: '#ff9800' } },
        { value: notifications.filter(n => n.type === 'error').length, name: '错误', itemStyle: { color: '#f44336' } },
        { value: notifications.filter(n => n.type === 'success').length, name: '成功', itemStyle: { color: '#4caf50' } },
      ],
    }],
  }), [notifications]);

  const categoryChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    xAxis: {
      type: 'category' as const,
      data: ['系统通知', '任务通知', '安全告警', '账单通知'],
    },
    yAxis: { type: 'value' as const },
    series: [{
      type: 'bar',
      data: [
        { value: notifications.filter(n => n.category === 'system').length, itemStyle: { color: '#667eea' } },
        { value: notifications.filter(n => n.category === 'task').length, itemStyle: { color: '#764ba2' } },
        { value: notifications.filter(n => n.category === 'security').length, itemStyle: { color: '#f093fb' } },
        { value: notifications.filter(n => n.category === 'billing').length, itemStyle: { color: '#4facfe' } },
      ],
      barWidth: '40%',
    }],
  }), [notifications]);

  // ===== 事件处理 =====
  const handleSelectAll = useCallback(() => {
    if (selectedIds.length === filteredNotifications.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredNotifications.map(n => n.id));
    }
  }, [selectedIds, filteredNotifications]);

  const handleSelect = useCallback((id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  }, []);

  const handleViewDetail = useCallback((notification: Notification) => {
    setSelectedNotification(notification);
    setDetailOpen(true);
    if (!notification.is_read) {
      markReadMut.mutate(notification.id);
    }
  }, [markReadMut]);

  const handleBatchDelete = useCallback(() => {
    if (selectedIds.length > 0) {
      batchDeleteMut.mutate(selectedIds);
    }
  }, [selectedIds, batchDeleteMut]);

  const handleBatchRead = useCallback(() => {
    if (selectedIds.length > 0) {
      batchReadMut.mutate(selectedIds);
    }
  }, [selectedIds, batchReadMut]);

  const handleRefresh = useCallback(() => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
  }, [refetch, queryClient]);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const TAB_LABELS = ['全部', '未读', '已读'];

  return (
    <PageContainer>
      <PageHeader
        title="通知中心"
        subtitle="管理系统通知、告警消息和任务提醒"
        breadcrumbs={[homeBreadcrumb]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
        ]}
        rightContent={
          <WebSocketStatus status={wsStatus} onReconnect={reconnect} showLabel />
        }
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="全部通知" value={stats.total} icon={<NotificationIcon />} color="primary" />
        <MetricsCard title="未读通知" value={stats.unread} icon={<NotificationFilledIcon />} color="warning" />
        <MetricsCard title="今日新增" value={stats.today} icon={<TimeIcon />} color="success" />
        <MetricsCard title="紧急未读" value={stats.urgent} icon={<ErrorCircleFilledIcon />} color="error" />
      </StatGrid>

      {/* ECharts图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="通知类型分布" option={typeChartOption} height={300} />
        <ChartCard title="通知分类统计" option={categoryChartOption} height={300} />
      </div>

      {/* 筛选和操作区域 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex flex-wrap items-center gap-4">
          <Input
            placeholder="搜索通知..."
            value={searchKeyword}
            onChange={(val) => setSearchKeyword(String(val))}
            prefixIcon={<SearchIcon />}
            style={{ width: 200 }}
          />
          <Select
            value={filterType}
            options={TYPE_OPTIONS}
            onChange={(val) => setFilterType(String(val))}
            style={{ width: 130 }}
          />
          <Select
            value={filterCategory}
            options={CATEGORY_OPTIONS}
            onChange={(val) => setFilterCategory(String(val))}
            style={{ width: 130 }}
          />
          <Select
            value={filterPriority}
            options={PRIORITY_OPTIONS}
            onChange={(val) => setFilterPriority(String(val))}
            style={{ width: 130 }}
          />
          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                icon={<MailIcon />}
                onClick={handleBatchRead}
              >
                批量已读 ({selectedIds.length})
              </Button>
              <Button
                variant="outline"
                theme="danger"
                icon={<DeleteIcon />}
                onClick={handleBatchDelete}
              >
                批量删除 ({selectedIds.length})
              </Button>
            </div>
          )}
          <Button
            theme="primary"
            icon={<CheckDoubleIcon />}
            onClick={() => markAllReadMut.mutate()}
            disabled={unreadCount === 0}
          >
            全部已读
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200">
          {TAB_LABELS.map((label, index) => (
            <button
              key={index}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tabValue === index
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setTabValue(index)}
            >
              {label}
              {index === 1 && unreadCount > 0 && (
                <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                  {unreadCount}
                </span>
              )}
              {index === 0 && ` (${totalCount})`}
            </button>
          ))}
        </div>
      </div>

      {/* 通知列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : filteredNotifications.length === 0 ? (
        <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-12 text-center">
          <NotificationIcon className="text-gray-300 text-5xl mb-4" />
          <h3 className="text-base font-semibold text-gray-800 mb-2">暂无通知</h3>
          <span className="text-sm text-gray-500">
            {tabValue === 1 ? '所有通知都已读' : '没有符合条件的通知'}
          </span>
        </div>
      ) : (
        <div className="rounded-xl bg-white border border-gray-200 shadow-sm overflow-hidden">
          <div className="divide-y divide-gray-100">
            {filteredNotifications.map((notification) => {
              const typeConfig = NOTIFICATION_TYPE_CONFIG[notification.type] || NOTIFICATION_TYPE_CONFIG.info;
              const priorityConfig = PRIORITY_CONFIG[notification.priority] || PRIORITY_CONFIG.normal;
              const categoryConfig = CATEGORY_CONFIG[notification.category] || CATEGORY_CONFIG.system;

              return (
                <div
                  key={notification.id}
                  className={`flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors hover:bg-gray-50 ${
                    notification.is_read ? 'bg-white' : 'bg-blue-50/50'
                  }`}
                  onClick={() => handleViewDetail(notification)}
                >
                  <span onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.includes(notification.id)}
                      onChange={() => handleSelect(notification.id)}
                    />
                  </span>
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${typeConfig.color}20`, color: typeConfig.color }}
                  >
                    {typeConfig.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-sm ${notification.is_read ? 'font-normal' : 'font-semibold'} truncate`}>
                        {notification.title}
                      </span>
                      <Tag
                        size="small"
                        style={{ backgroundColor: `${priorityConfig.color}20`, color: priorityConfig.color, fontWeight: 600 }}
                      >
                        {priorityConfig.label}
                      </Tag>
                      <Tag size="small" variant="outline" icon={categoryConfig.icon as React.ReactElement}>
                        {categoryConfig.label}
                      </Tag>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 truncate">{notification.content}</span>
                      <span className="text-xs text-gray-400 flex-shrink-0">{formatTime(notification.created_at)}</span>
                      <span className="text-xs text-gray-400 flex-shrink-0">{notification.sender}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {!notification.is_read && (
                      <Tooltip content="标记已读">
                        <span
                          className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
                          onClick={(e) => { e.stopPropagation(); markReadMut.mutate(notification.id); }}
                        >
                          <MailIcon />
                        </span>
                      </Tooltip>
                    )}
                    <Tooltip content="删除">
                      <span
                        className="cursor-pointer hover:bg-red-50 rounded p-1 inline-flex items-center text-red-500"
                        onClick={(e) => { e.stopPropagation(); batchDeleteMut.mutate([notification.id]); }}
                      >
                        <DeleteIcon />
                      </span>
                    </Tooltip>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 通知详情对话框 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header="通知详情"
        footer={
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
        }
      >
        {selectedNotification && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{
                  backgroundColor: `${NOTIFICATION_TYPE_CONFIG[selectedNotification.type]?.color}20`,
                  color: NOTIFICATION_TYPE_CONFIG[selectedNotification.type]?.color,
                }}
              >
                {NOTIFICATION_TYPE_CONFIG[selectedNotification.type]?.icon}
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-800">{selectedNotification.title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <Tag
                    size="small"
                    style={{
                      backgroundColor: `${PRIORITY_CONFIG[selectedNotification.priority]?.color}20`,
                      color: PRIORITY_CONFIG[selectedNotification.priority]?.color,
                    }}
                  >
                    {PRIORITY_CONFIG[selectedNotification.priority]?.label}
                  </Tag>
                  <Tag size="small" variant="outline">
                    {CATEGORY_CONFIG[selectedNotification.category]?.label}
                  </Tag>
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-700">
              {selectedNotification.content}
            </p>

            <hr className="border-gray-200" />

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-gray-500">发送者</span>
                <p className="text-sm text-gray-700">{selectedNotification.sender}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">发送时间</span>
                <p className="text-sm text-gray-700">
                  {new Date(selectedNotification.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <p className="text-sm text-gray-700">
                  {selectedNotification.is_read ? '已读' : '未读'}
                </p>
              </div>
              {selectedNotification.read_at && (
                <div>
                  <span className="text-xs text-gray-500">阅读时间</span>
                  <p className="text-sm text-gray-700">
                    {new Date(selectedNotification.read_at).toLocaleString('zh-CN')}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default NotificationCenterPage;
