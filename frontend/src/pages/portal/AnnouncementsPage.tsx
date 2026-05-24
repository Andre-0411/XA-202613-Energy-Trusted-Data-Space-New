/**
 * 公告通知页面
 * 展示系统公告、合规提醒、告警通知统一推送
 * 数据来源: /api/v1/notification/ (PortalNotification DB)
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Select, Tag, Tabs, Pagination, Dialog, MessagePlugin } from 'tdesign-react';
import {
  RefreshIcon,
  NotificationIcon,
  InfoCircleIcon,
  ErrorCircleIcon,
  CheckCircleFilledIcon,
  MailIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  batchMarkAsRead,
  type Notification,
} from '@/api/system';

/** 公告类型映射 */
type AnnouncementType = 'system' | 'compliance' | 'alert' | 'update';

/** 公告优先级映射 */
type AnnouncementPriority = 'low' | 'medium' | 'high' | 'critical';

/** 公告类型选项 */
const ANNOUNCEMENT_TYPE_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'system', label: '系统公告' },
  { value: 'task', label: '任务通知' },
  { value: 'security', label: '安全告警' },
  { value: 'billing', label: '计费通知' },
];

/** 优先级选项 */
const PRIORITY_OPTIONS = [
  { value: 'all', label: '全部优先级' },
  { value: 'low', label: '低' },
  { value: 'normal', label: '普通' },
  { value: 'high', label: '高' },
  { value: 'urgent', label: '紧急' },
];

/** 将 notification category 映射为展示类型 */
function mapCategoryToType(category: string): AnnouncementType {
  switch (category) {
    case 'security': return 'alert';
    case 'billing': return 'compliance';
    case 'task': return 'update';
    default: return 'system';
  }
}

const AnnouncementsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态管理 =====
  const [tabValue, setTabValue] = useState<string>('all');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 查看详情对话框状态 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<Notification | null>(null);

  // ===== API 查询 =====
  const { data: notifData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['notifications', page, pageSize, typeFilter, priorityFilter, tabValue],
    queryFn: async () => {
      const params: any = {
        page: page,
        page_size: pageSize,
      };
      if (typeFilter !== 'all') params.category = typeFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (tabValue === 'unread') params.is_read = false;

      const res = await getNotifications(params);
      return res.data;
    },
  });

  const notifications = notifData?.data?.items ?? [];
  const totalCount = notifData?.data?.total ?? 0;
  const unreadCount = notifData?.data?.unread_count ?? 0;

  // ===== 获取未读数 (用于 badge) =====
  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: async () => {
      const res = await getUnreadCount();
      return res.data;
    },
  });
  const badgeUnreadCount = unreadData?.data?.unread_count ?? unreadCount;

  // ===== 统计数据 (从列表数据聚合) =====
  const stats = useMemo(() => ({
    totalAnnouncements: totalCount,
    unreadAnnouncements: unreadCount,
  }), [totalCount, unreadCount]);

  // ===== 标记已读 mutation =====
  const markReadMutation = useMutation({
    mutationFn: (id: string) => markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
    onError: (err: Error) => {
      MessagePlugin.error('标记已读失败: ' + err.message);
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      MessagePlugin.success('已全部标记为已读');
    },
    onError: (err: Error) => {
      MessagePlugin.error('全部标记已读失败: ' + err.message);
    },
  });

  // ===== 事件处理 =====
  const handleRefresh = useCallback(() => {
    setSearchKeyword('');
    setTypeFilter('all');
    setPriorityFilter('all');
    setPage(1);
    refetch();
  }, [refetch]);

  const handleViewDetail = useCallback((notification: Notification) => {
    setSelectedAnnouncement(notification);
    setDetailOpen(true);
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id);
    }
  }, [markReadMutation]);

  const handleMarkAllRead = useCallback(() => {
    markAllReadMutation.mutate();
  }, [markAllReadMutation]);

  // ===== 获取类型图标 =====
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'info': return <InfoCircleIcon size="16px" />;
      case 'warning': return <ErrorCircleIcon size="16px" />;
      case 'error': return <ErrorCircleIcon size="16px" />;
      case 'success': return <CheckCircleFilledIcon size="16px" />;
      default: return <NotificationIcon size="16px" />;
    }
  };

  // ===== 获取类型颜色 =====
  const getTypeTagTheme = (type: string): string => {
    switch (type) {
      case 'info': return 'primary';
      case 'warning': return 'warning';
      case 'error': return 'danger';
      case 'success': return 'success';
      default: return 'default';
    }
  };

  // ===== 获取优先级颜色 =====
  const getPriorityTagTheme = (priority: string): string => {
    switch (priority) {
      case 'low': return 'success';
      case 'normal': return 'primary';
      case 'high': return 'warning';
      case 'urgent': return 'danger';
      default: return 'default';
    }
  };

  // ===== 获取优先级标签 =====
  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'low': return '低';
      case 'normal': return '普通';
      case 'high': return '高';
      case 'urgent': return '紧急';
      default: return priority;
    }
  };

  if (isError) {
    return (
      <div className="flex flex-col gap-4 h-full overflow-auto">
        <PageHeader title="公告通知" subtitle="系统公告、合规提醒、告警通知统一推送" breadcrumbs={[homeBreadcrumb]} />
        <div className="rounded-xl bg-white p-8 text-center shadow">
          <ErrorCircleIcon size="48px" className="text-red-500 mb-2" />
          <p className="text-gray-600 mb-2">加载公告数据失败</p>
          <p className="text-sm text-gray-400 mb-4">{(error as Error)?.message || '未知错误'}</p>
          <Button theme="primary" onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full overflow-auto">
      <PageHeader
        title="公告通知"
        subtitle="系统公告、合规提醒、告警通知统一推送"
        breadcrumbs={[homeBreadcrumb]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
          { icon: <MailIcon />, onClick: handleMarkAllRead, tooltip: '全部标为已读' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl p-5 text-white shadow-lg" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <div className="flex items-center gap-3">
            <NotificationIcon size="40px" />
            <div>
              <p className="text-2xl font-bold">{stats.totalAnnouncements}</p>
              <p className="text-sm opacity-80">总公告数</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl p-5 text-white shadow-lg" style={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }}>
          <div className="flex items-center gap-3">
            <MailIcon size="40px" />
            <div>
              <p className="text-2xl font-bold">{stats.unreadAnnouncements}</p>
              <p className="text-sm opacity-80">未读公告</p>
            </div>
          </div>
        </div>
      </div>

      {/* 标签页切换 */}
      <div className="rounded-xl bg-white shadow p-1">
        <Tabs
          value={tabValue}
          onChange={(v) => { setTabValue(v as string); setPage(1); }}
        >
          <Tabs.TabPanel label="全部公告" value="all" />
          <Tabs.TabPanel
            label={
              <span className="flex items-center gap-1">
                未读公告
                {badgeUnreadCount > 0 && (
                  <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full">
                    {badgeUnreadCount > 99 ? '99+' : badgeUnreadCount}
                  </span>
                )}
              </span>
            }
            value="unread"
          />
        </Tabs>
      </div>

      {/* 搜索与筛选 */}
      <div className="rounded-xl bg-white shadow p-4">
        <div className="flex flex-col md:flex-row gap-3 items-start md:items-center">
          <Select
            value={typeFilter}
            onChange={(v) => { setTypeFilter(v as string); setPage(1); }}
            options={ANNOUNCEMENT_TYPE_OPTIONS}
            className="w-[140px]"
          />
          <Select
            value={priorityFilter}
            onChange={(v) => { setPriorityFilter(v as string); setPage(1); }}
            options={PRIORITY_OPTIONS}
            className="w-[140px]"
          />
          <Button variant="outline" onClick={handleRefresh} icon={<RefreshIcon />}>
            刷新
          </Button>
        </div>
      </div>

      {/* 公告列表 */}
      <LoadingOverlay open={isLoading}>
        {notifications.length === 0 ? (
          <div className="rounded-xl bg-white shadow p-8 text-center">
            <h6 className="text-lg text-gray-500 mb-2">暂无公告</h6>
            <p className="text-sm text-gray-400">
              {tabValue === 'unread' ? '所有公告已读' : '暂无符合条件的公告'}
            </p>
          </div>
        ) : (
          <div className="rounded-xl bg-white shadow">
            {notifications.map((notification: Notification, index: number) => (
              <React.Fragment key={notification.id}>
                <div
                  onClick={() => handleViewDetail(notification)}
                  className={"flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-gray-50 " +
                    (notification.is_read ? 'bg-white' : 'bg-blue-50/50')
                  }
                >
                  <div className={"flex-shrink-0 " + (getTypeTagTheme(notification.type) === 'danger' ? 'text-red-500' : getTypeTagTheme(notification.type) === 'warning' ? 'text-yellow-500' : getTypeTagTheme(notification.type) === 'success' ? 'text-green-500' : 'text-blue-500')}>
                    {getTypeIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={"text-sm truncate " + (notification.is_read ? 'font-normal' : 'font-semibold')}>
                        {notification.title}
                      </span>
                      <Tag theme={getPriorityTagTheme(notification.priority) as any} variant="outline">
                        {getPriorityLabel(notification.priority)}
                      </Tag>
                      {!notification.is_read && (
                        <Tag theme="danger">未读</Tag>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-gray-400">{notification.sender}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(notification.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  </div>
                </div>
                {index < notifications.length - 1 && <hr className="border-gray-100" />}
              </React.Fragment>
            ))}
          </div>
        )}
      </LoadingOverlay>

      {/* 分页控件 */}
      {totalCount > 0 && (
        <div className="rounded-xl bg-white shadow p-3 flex justify-center">
          <Pagination
            current={page}
            pageSize={pageSize}
            total={totalCount}
            onChange={(pageInfo) => setPage(pageInfo.current)}
            onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
            pageSizeOptions={[10, 20, 50]}
            showPageSize
          />
        </div>
      )}

      {/* 查看详情对话框 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header={
          <div className="flex items-center gap-2">
            {selectedAnnouncement && getTypeIcon(selectedAnnouncement.type)}
            <span className="text-lg font-semibold">{selectedAnnouncement?.title}</span>
          </div>
        }
        footer={
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
        }
        width="60%"
      >
        {selectedAnnouncement && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Tag theme={getTypeTagTheme(selectedAnnouncement.type) as any} variant="outline">
                {ANNOUNCEMENT_TYPE_OPTIONS.find(t => t.value === selectedAnnouncement.category)?.label || selectedAnnouncement.category}
              </Tag>
              <Tag theme={getPriorityTagTheme(selectedAnnouncement.priority) as any} variant="outline">
                优先级：{getPriorityLabel(selectedAnnouncement.priority)}
              </Tag>
            </div>

            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {selectedAnnouncement.content}
            </p>

            <hr className="border-gray-200" />

            <div className="flex flex-wrap gap-6">
              <span className="text-sm text-gray-500">
                <strong>发布来源：</strong>{selectedAnnouncement.sender}
              </span>
              <span className="text-sm text-gray-500">
                <strong>发布时间：</strong>{new Date(selectedAnnouncement.created_at).toLocaleString('zh-CN')}
              </span>
              {selectedAnnouncement.read_at && (
                <span className="text-sm text-gray-500">
                  <strong>阅读时间：</strong>{new Date(selectedAnnouncement.read_at).toLocaleString('zh-CN')}
                </span>
              )}
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default AnnouncementsPage;
