/**
 * 数据目录详情页面
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Tabs, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getCatalog } from '@/api/catalogManage';

const { TabPanel } = Tabs;

export default function CatalogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ['catalog-manage', id],
    queryFn: () => getCatalog(id!),
    enabled: !!id,
  });

  const catalog = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!catalog) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">目录不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={catalog.name}
        subtitle={`分类: ${catalog.category} | 敏感等级: ${catalog.sensitivity_level}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '数据目录管理', href: '/dashboard/tds/catalog' },
          { label: catalog.name },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/catalog')}
          >
            返回
          </Button>
        }
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(val as number)}>
        <TabPanel value={0} label="基本信息">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <span className="text-xs text-gray-500 block mb-1">描述</span>
                <p className="text-sm text-gray-700">{catalog.description || '暂无描述'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">标签</span>
                <div className="flex items-center gap-1 flex-wrap">
                  {catalog.tags?.map((tag: string, i: number) => <Tag key={i}>{tag}</Tag>)}
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag theme={catalog.status === 'published' ? 'success' : 'default'}>
                  {catalog.status}
                </Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">创建时间</span>
                <p className="text-sm text-gray-700">{new Date(catalog.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">发布时间</span>
                <p className="text-sm text-gray-700">{catalog.published_at ? new Date(catalog.published_at).toLocaleString('zh-CN') : '-'}</p>
              </div>
            </div>
          </PageSection>
        </TabPanel>
        <TabPanel value={1} label="管控模板">
          <p className="text-xs text-gray-500 mt-2">管控模板功能开发中...</p>
        </TabPanel>
        <TabPanel value={2} label="访问规则">
          <p className="text-xs text-gray-500 mt-2">访问规则功能开发中...</p>
        </TabPanel>
        <TabPanel value={3} label="订阅情况">
          <p className="text-xs text-gray-500 mt-2">订阅情况功能开发中...</p>
        </TabPanel>
      </Tabs>
    </PageContainer>
  );
}
