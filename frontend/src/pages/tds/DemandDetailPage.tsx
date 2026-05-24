/**
 * 需求详情页面
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getDemand } from '@/api/demandManage';

export default function DemandDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['demand-manage', id],
    queryFn: () => getDemand(id!),
    enabled: !!id,
  });

  const demand = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!demand) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">需求不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={demand.title}
        subtitle={`类型: ${demand.demand_type}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '需求管理', href: '/dashboard/tds/demands' },
          { label: demand.title },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/demands')}
          >
            返回
          </Button>
        }
      />

      <PageSection>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="md:col-span-2">
            <span className="text-xs text-gray-500 block mb-1">需求描述</span>
            <p className="text-sm text-gray-700">{demand.description}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">预算范围</span>
            <p className="text-sm text-gray-700">{demand.budget_range || '未设定'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">截止日期</span>
            <p className="text-sm text-gray-700">{demand.deadline ? new Date(demand.deadline).toLocaleDateString('zh-CN') : '未设定'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">状态</span>
            <Tag theme={demand.status === 'open' ? 'success' : 'default'}>{demand.status}</Tag>
          </div>
          <div>
            <span className="text-xs text-gray-500 block mb-1">发布时间</span>
            <p className="text-sm text-gray-700">{new Date(demand.created_at).toLocaleString('zh-CN')}</p>
          </div>
        </div>
      </PageSection>
    </PageContainer>
  );
}
