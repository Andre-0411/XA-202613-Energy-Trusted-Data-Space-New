/**
 * 连接器详情页面
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Tabs, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getManagedConnector } from '@/api/connectorManage';

const { TabPanel } = Tabs;

export default function ConnectorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ['connector-manage', id],
    queryFn: () => getManagedConnector(id!),
    enabled: !!id,
  });

  const connector = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!connector) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">连接器不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={connector.name}
        subtitle={`类型: ${connector.connector_type} | 版本: ${connector.version}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '连接器管理', href: '/dashboard/tds/connectors' },
          { label: connector.name },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/connectors')}
          >
            返回
          </Button>
        }
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(val as number)}>
        <TabPanel value={0} label="基本信息">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag theme={connector.status === 'online' ? 'success' : 'danger'}>
                  {connector.status}
                </Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">最后心跳</span>
                <p className="text-sm text-gray-700">
                  {connector.last_heartbeat_at ? new Date(connector.last_heartbeat_at).toLocaleString('zh-CN') : '-'}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">注册时间</span>
                <p className="text-sm text-gray-700">{new Date(connector.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">更新时间</span>
                <p className="text-sm text-gray-700">{new Date(connector.updated_at).toLocaleString('zh-CN')}</p>
              </div>
            </div>
          </PageSection>
        </TabPanel>
        <TabPanel value={1} label="数据源">
          <p className="text-xs text-gray-500 mt-2">数据源管理功能开发中...</p>
        </TabPanel>
        <TabPanel value={2} label="元数据发现">
          <p className="text-xs text-gray-500 mt-2">元数据发现功能开发中...</p>
        </TabPanel>
        <TabPanel value={3} label="文件库">
          <p className="text-xs text-gray-500 mt-2">文件库功能开发中...</p>
        </TabPanel>
        <TabPanel value={4} label="API代理">
          <p className="text-xs text-gray-500 mt-2">API代理功能开发中...</p>
        </TabPanel>
      </Tabs>
    </PageContainer>
  );
}
