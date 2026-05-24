/**
 * 数据产品详情页面
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Tabs, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getDataProduct } from '@/api/productManage';

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState('0');

  const { data, isLoading } = useQuery({
    queryKey: ['product-manage', id],
    queryFn: () => getDataProduct(id!),
    enabled: !!id,
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
          { label: '数据产品管理', href: '/dashboard/tds/products' },
          { label: product.name },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/products')}
          >
            返回
          </Button>
        }
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(String(val))}>
        <Tabs.TabPanel value="0" label="基本信息">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="col-span-2">
                <span className="text-xs text-gray-500 block mb-1">描述</span>
                <p className="text-sm text-gray-700">{product.description || '暂无描述'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <div className="mt-1">
                  <Tag theme={product.status === 'published' ? 'success' : 'default'}>{product.status}</Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">计算引擎</span>
                <p className="text-sm text-gray-700">{product.compute_engine || '-'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">创建时间</span>
                <p className="text-sm text-gray-700">{new Date(product.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">更新时间</span>
                <p className="text-sm text-gray-700">{new Date(product.updated_at).toLocaleString('zh-CN')}</p>
              </div>
            </div>
          </PageSection>
        </Tabs.TabPanel>
        <Tabs.TabPanel value="1" label="技术规格">
          <p className="text-sm text-gray-500 mt-2">技术规格功能开发中...</p>
        </Tabs.TabPanel>
        <Tabs.TabPanel value="2" label="定价配置">
          <p className="text-sm text-gray-500 mt-2">定价配置功能开发中...</p>
        </Tabs.TabPanel>
        <Tabs.TabPanel value="3" label="交付配置">
          <p className="text-sm text-gray-500 mt-2">交付配置功能开发中...</p>
        </Tabs.TabPanel>
        <Tabs.TabPanel value="4" label="合规文档">
          <p className="text-sm text-gray-500 mt-2">合规文档功能开发中...</p>
        </Tabs.TabPanel>
        <Tabs.TabPanel value="5" label="验收记录">
          <p className="text-sm text-gray-500 mt-2">验收记录功能开发中...</p>
        </Tabs.TabPanel>
      </Tabs>
    </PageContainer>
  );
}
