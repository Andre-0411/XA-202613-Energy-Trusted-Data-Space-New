/**
 * 订阅详情页面
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getDataSubscription } from '@/api/dataSubscription';

export default function SubscriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['data-subscription', id],
    queryFn: () => getDataSubscription(id!),
    enabled: !!id,
  });

  const sub = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!sub) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">订阅不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="订阅详情"
        subtitle={`ID: ${sub.id}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '数据订阅管理', href: '/dashboard/tds/subscriptions' },
          { label: '订阅详情' },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/subscriptions')}
          >
            返回
          </Button>
        }
      />

      <PageSection>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <span className="text-xs text-gray-500 block mb-1">目录ID</span>
            <p className="text-sm font-mono text-gray-700">{sub.catalog_id}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">状态</span>
            <Tag theme={sub.status === 'approved' ? 'success' : sub.status === 'pending' ? 'warning' : 'danger'}>{sub.status}</Tag>
          </div>
          <div className="md:col-span-2">
            <span className="text-xs text-gray-500 block mb-1">申请理由</span>
            <p className="text-sm text-gray-700">{sub.reason || '无'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">过期时间</span>
            <p className="text-sm text-gray-700">{sub.expires_at ? new Date(sub.expires_at).toLocaleString('zh-CN') : '永久'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">申请时间</span>
            <p className="text-sm text-gray-700">{new Date(sub.created_at).toLocaleString('zh-CN')}</p>
          </div>
        </div>
      </PageSection>
    </PageContainer>
  );
}
