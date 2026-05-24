/**
 * 产品市场页面
 * 展示已发布的产品，支持浏览和订阅
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button, Tag } from 'tdesign-react';
import { CartIcon as SubscribeIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import { listMarketProducts } from '@/api/productMarket';
import type { DataProduct } from '@/types/api';

export default function ProductMarketPage() {
  const navigate = useNavigate();

  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['market-products', keyword, typeFilter],
    queryFn: () => listMarketProducts({
      keyword: keyword || undefined,
      product_type: typeFilter || undefined,
    }),
  });

  const products = data?.data?.items || [];

  return (
    <PageContainer>
      <PageHeader
        title="产品市场"
        subtitle="浏览和订阅已发布的数据产品"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '产品市场' },
        ]}
      />

      <FilterBar
        fields={[
          { name: 'keyword', type: 'text', placeholder: '搜索产品名称或描述', width: 300 },
          {
            name: 'type',
            type: 'select',
            placeholder: '产品类型',
            width: 150,
            options: [
              { label: '全部', value: '' },
              { label: '数据服务', value: 'data_service' },
              { label: '数据API', value: 'data_api' },
              { label: '数据报告', value: 'data_report' },
              { label: '算法模型', value: 'algorithm_model' },
            ],
          },
        ]}
        values={{ keyword, type: typeFilter }}
        onChange={(name, value) => {
          if (name === 'keyword') setKeyword(String(value));
          if (name === 'type') setTypeFilter(String(value));
        }}
        onSearch={() => {}}
        onReset={() => {
          setKeyword('');
          setTypeFilter('');
        }}
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      ) : products.length === 0 ? (
        <PageSection className="mt-4">
          <div className="p-8 text-center">
            <p className="text-sm text-gray-500">暂无已发布的产品</p>
          </div>
        </PageSection>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mt-4">
          {products.map((product) => (
            <div key={product.id} className="rounded-xl bg-white border border-gray-200 flex flex-col">
              <div className="p-4 flex-1">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-base font-semibold text-gray-800">{product.name}</h3>
                  <Tag variant="outline">{product.product_type}</Tag>
                </div>
                <p className="text-xs text-gray-600 mb-4 min-h-[40px]">
                  {product.description?.slice(0, 100) || '暂无描述'}
                  {product.description && product.description.length > 100 ? '...' : ''}
                </p>
                <div className="flex gap-2 flex-wrap mb-1">
                  <Tag size="small">v{product.version}</Tag>
                  {product.compute_engine && (
                    <Tag size="small">{product.compute_engine}</Tag>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 p-4 border-t border-gray-100">
                <Button variant="outline" onClick={() => navigate(`/dashboard/tds/market/${product.id}`)}>
                  查看详情
                </Button>
                <Button theme="primary" icon={<SubscribeIcon />}>
                  订阅
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
