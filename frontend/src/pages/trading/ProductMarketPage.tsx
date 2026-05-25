/**
 * 产品市场页面
 * 产品卡片网格（3列）、搜索筛选、订阅确认
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Rate, MessagePlugin } from 'tdesign-react';
import { SearchIcon, RefreshIcon, CartIcon, StarFilledIcon, UserIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import request from '@/api/request';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer from '@/components/common/PageContainer';

// ===== API =====
const listMarketProducts = (params?: any) => request.get('/product-market/products', { params });
const subscribeProduct = (data: any) => request.post('/product-market/subscriptions', data);

// ===== 类型 =====
interface DataProduct {
  id: string;
  name: string;
  description?: string;
  product_type?: string;
  price?: number;
  pricing_model?: string;
  rating?: number;
  rating_count?: number;
  subscription_count?: number;
  version?: string;
  status?: string;
}

const CATEGORY_OPTIONS = [
  { value: '', label: '全部分类' },
  { value: 'data_service', label: '数据服务' },
  { value: 'data_api', label: '数据API' },
  { value: 'data_report', label: '数据报告' },
  { value: 'algorithm_model', label: '算法模型' },
  { value: 'data_tool', label: '数据工具' },
];

const CATEGORY_ICON: Record<string, string> = {
  data_service: '📊',
  data_api: '🔌',
  data_report: '📋',
  algorithm_model: '🤖',
  data_tool: '🛠️',
};

const ProductMarketPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 =====
  const [keyword, setKeyword] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // ===== 订阅确认 =====
  const [subscribeOpen, setSubscribeOpen] = useState(false);
  const [subscribeTarget, setSubscribeTarget] = useState<DataProduct | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['market-products', keyword, categoryFilter],
    queryFn: () => listMarketProducts({
      keyword: keyword || undefined,
      product_type: categoryFilter || undefined,
    }),
  });

  const res = data?.data || data;
  const list: DataProduct[] = res?.items || res?.list || res || [];

  // ===== 订阅 =====
  const subscribeMut = useMutation({
    mutationFn: (d: any) => subscribeProduct(d),
    onSuccess: () => {
      MessagePlugin.success('订阅申请已提交，等待审批');
      queryClient.invalidateQueries({ queryKey: ['market-products'] });
      setSubscribeOpen(false);
    },
    onError: () => MessagePlugin.error('订阅失败'),
  });

  const handleSubscribe = useCallback(() => {
    if (!subscribeTarget) return;
    subscribeMut.mutate({ product_id: subscribeTarget.id });
  }, [subscribeTarget, subscribeMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '交易中心' }, { label: '产品市场' }],
    [],
  );

  // ===== 价格格式化 =====
  const formatPrice = (price?: number, model?: string) => {
    if (price === undefined || price === null) return '面议';
    if (price === 0) return '免费';
    return `¥${price.toLocaleString()}/${model === 'monthly' ? '月' : model === 'yearly' ? '年' : '次'}`;
  };

  return (
    <PageContainer>
      <PageHeader
        title="产品市场"
        subtitle="浏览和订阅已发布的数据产品与服务"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => refetch(), tooltip: '刷新' },
        ]}
      />

      {/* 搜索筛选栏 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <Input
            prefixIcon={<SearchIcon />}
            value={keyword}
            onChange={setKeyword}
            placeholder="搜索产品名称或描述"
            style={{ minWidth: 280 }}
            clearable
          />
          <Select
            value={categoryFilter}
            onChange={setCategoryFilter}
            options={CATEGORY_OPTIONS}
            style={{ minWidth: 150 }}
            clearable
          />
          <Button onClick={() => { setKeyword(''); setCategoryFilter(''); }}>重置</Button>
        </div>
      </div>

      {/* 产品卡片网格（3列） */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      ) : list.length === 0 ? (
        <div className="rounded-xl bg-white border border-gray-200 p-12 text-center">
          <p className="text-gray-400">暂无产品数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {list.map((product) => (
            <div key={product.id} className="rounded-xl bg-white border border-gray-200 flex flex-col hover:shadow-md transition-shadow">
              <div className="p-5 flex-1">
                {/* 图标 + 名称 */}
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center text-2xl flex-shrink-0">
                    {CATEGORY_ICON[product.product_type ?? ''] ?? '📦'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-gray-800 truncate">{product.name}</h3>
                    {product.product_type && (
                      <Tag size="small" variant="outline" className="mt-1">
                        {CATEGORY_OPTIONS.find(c => c.value === product.product_type)?.label ?? product.product_type}
                      </Tag>
                    )}
                  </div>
                </div>

                {/* 描述 */}
                <p className="text-sm text-gray-600 mb-3 line-clamp-2 min-h-[40px]">
                  {product.description || '暂无描述'}
                </p>

                {/* 价格 */}
                <div className="text-lg font-bold text-orange-600 mb-2">
                  {formatPrice(product.price, product.pricing_model)}
                </div>

                {/* 评分 + 订阅数 */}
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  <div className="flex items-center gap-1">
                    <Rate
                      value={product.rating ?? 0}
                      size="small"
                      disabled
                      allowHalf
                    />
                    <span className="text-gray-500 ml-1">
                      {product.rating?.toFixed(1) ?? '—'}
                    </span>
                    {product.rating_count !== undefined && (
                      <span className="text-gray-400">({product.rating_count})</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <UserIcon style={{ fontSize: '0.75rem' }} />
                    <span>{product.subscription_count ?? 0} 订阅</span>
                  </div>
                </div>
              </div>

              {/* 底部操作栏 */}
              <div className="flex items-center gap-2 p-4 border-t border-gray-100">
                <Button
                  theme="primary"
                  icon={<CartIcon />}
                  onClick={() => { setSubscribeTarget(product); setSubscribeOpen(true); }}
                  className="flex-1"
                >
                  订阅
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 订阅确认 Dialog */}
      <Dialog
        visible={subscribeOpen}
        onClose={() => setSubscribeOpen(false)}
        header="确认订阅"
        width="420px"
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => setSubscribeOpen(false)}>取消</Button>
            <Button theme="primary" loading={subscribeMut.isPending} onClick={handleSubscribe}>确认订阅</Button>
          </div>
        }
      >
        {subscribeTarget && (
          <div className="flex flex-col gap-3">
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-xl">
                  {CATEGORY_ICON[subscribeTarget.product_type ?? ''] ?? '📦'}
                </div>
                <div>
                  <div className="font-semibold">{subscribeTarget.name}</div>
                  <div className="text-sm text-orange-600 font-bold">
                    {formatPrice(subscribeTarget.price, subscribeTarget.pricing_model)}
                  </div>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-500">
              订阅后将提交审批，审批通过后即可使用该产品。确认订阅吗？
            </p>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default ProductMarketPage;
