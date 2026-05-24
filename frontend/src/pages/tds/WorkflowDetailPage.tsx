/**
 * 工作流详情页面
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Tabs, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getWorkflow, listApprovalRecords } from '@/api/workflowManage';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';

const workflowTypeMap: Record<string, string> = {
  certification: '认证审核',
  subscription: '订阅审批',
  product_publish: '产品上架',
  product_unpublish: '产品下架',
  demand_claim: '需求认领',
  contract: '合约审批',
};

const recordStatusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  pending: 'warning',
  in_progress: 'default',
  approved: 'success',
  rejected: 'danger',
  cancelled: 'default',
};

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState('0');
  const [recordPage, setRecordPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ['workflow-manage', id],
    queryFn: () => getWorkflow(id!),
    enabled: !!id,
  });

  const { data: recordsData } = useQuery({
    queryKey: ['workflow-records', id, recordPage],
    queryFn: () => listApprovalRecords({ workflow_id: id, page: recordPage + 1, page_size: 20 }),
    enabled: !!id && tabValue === '1',
  });

  const workflow = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!workflow) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">工作流不存在</div>
      </PageContainer>
    );
  }

  const recordColumns: Column<any>[] = [
    { id: 'business_type', label: '业务类型', minWidth: 120 },
    { id: 'business_id', label: '业务ID', minWidth: 200, render: (row) => <span className="text-sm truncate block max-w-[200px]">{row.business_id}</span> },
    {
      id: 'current_step',
      label: '当前步骤',
      minWidth: 100,
      render: (row) => `${row.current_step} / ${row.total_steps}`,
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={recordStatusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    { id: 'created_at', label: '创建时间', minWidth: 160, render: (row) => new Date(row.created_at).toLocaleString('zh-CN') },
  ];

  return (
    <PageContainer>
      <PageHeader
        title={workflow.name}
        subtitle={`类型: ${workflowTypeMap[workflow.workflow_type] || workflow.workflow_type}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '工作流管理', href: '/dashboard/tds/workflows' },
          { label: workflow.name },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/workflows')}
          >
            返回
          </Button>
        }
      />

      <Tabs
        value={tabValue}
        onChange={(val) => setTabValue(String(val))}
        className="border-b border-gray-200"
      >
        <Tabs.TabPanel label="基本信息" value="0">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-gray-500 block mb-1">工作流类型</span>
                <Tag variant="outline" theme="primary">
                  {workflowTypeMap[workflow.workflow_type] || workflow.workflow_type}
                </Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">系统预设</span>
                <Tag variant="outline" theme={workflow.is_system ? 'primary' : 'default'}>{workflow.is_system ? '是' : '否'}</Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag theme={workflow.status === 'active' ? 'success' : 'default'}>{workflow.status}</Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">创建时间</span>
                <p className="text-sm text-gray-700">{new Date(workflow.created_at).toLocaleString('zh-CN')}</p>
              </div>
              {workflow.description && (
                <div className="md:col-span-2">
                  <span className="text-xs text-gray-500 block mb-1">描述</span>
                  <p className="text-sm text-gray-700">{workflow.description}</p>
                </div>
              )}
              <div className="md:col-span-2">
                <span className="text-xs text-gray-500 block mb-2">审批步骤</span>
                <div className="flex flex-col gap-2">
                  {workflow.steps?.map((step: any, index: number) => (
                    <div key={index} className="rounded border border-gray-200 p-3">
                      <div className="flex items-center gap-2">
                        <Tag theme="primary">步骤 {index + 1}</Tag>
                        <span className="text-sm">{step.name || step.step_name || `步骤 ${index + 1}`}</span>
                        {step.approver_role && (
                          <Tag variant="outline">{step.approver_role}</Tag>
                        )}
                      </div>
                    </div>
                  ))}
                  {(!workflow.steps || workflow.steps.length === 0) && (
                    <p className="text-sm text-gray-500">暂无步骤配置</p>
                  )}
                </div>
              </div>
            </div>
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel label="审批记录" value="1">
          <PageSection className="mt-2">
            <DataTable
              columns={recordColumns}
              rows={recordsData?.data?.items || []}
              loading={false}
              page={recordPage}
              pageSize={20}
              total={recordsData?.data?.total || 0}
              onPageChange={setRecordPage}
              onPageSizeChange={() => {}}
            />
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>
    </PageContainer>
  );
}
