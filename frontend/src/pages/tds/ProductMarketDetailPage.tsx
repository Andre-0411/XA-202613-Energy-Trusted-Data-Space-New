/**
 * 产品市场详情页面
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button, Tag } from 'tdesign-react';
import { ArrowLeftIcon, CartIcon as SubscribeIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getMarketProduct, subscribeProduct } from '@/api/productMarket';

export default function ProductMarketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['market-product', id],
    queryFn: () => getMarketProduct(id!),
    enabled: !!id,
  });

  const subscribeMutation = useMutation({
    mutationFn: () => subscribeProduct({ product_id: id! }),
    onSuccess: () => alert('订阅申请已提交'),
  });

  const product = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!product) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">产品不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={product.name}
        subtitle={`类型: ${product.product_type} | 版本: ${product.version}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '产品市场', href: '/dashboard/tds/market' },
          { label: product.name },
        ]}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              icon={<ArrowLeftIcon />}
              onClick={() => navigate('/dashboard/tds/market')}
            >
              返回
            </Button>
            <Button
              theme="primary"
              icon={<SubscribeIcon />}
              onClick={() => subscribeMutation.mutate()}
              disabled={subscribeMutation.isPending}
            >
              {subscribeMutation.isPending ? '提交中...' : '订阅'}
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <PageSection title="产品描述">
            <p className="text-sm text-gray-700">{product.description || '暂无描述'}</p>
          </PageSection>
        </div>
        <div>
          <PageSection title="产品信息">
            <div className="flex flex-col gap-4">
              <div>
                <span className="text-xs text-gray-500 block mb-1">类型</span>
                <Tag>{product.product_type}</Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">版本</span>
                <p className="text-sm text-gray-700">{product.version}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">计算引擎</span>
                <p className="text-sm text-gray-700">{product.compute_engine || '-'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag theme="success">{product.status}</Tag>
              </div>
            </div>
          </PageSection>
        </div>
      </div>
    </PageContainer>
  );
}
