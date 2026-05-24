/**
 * 机构详情页面
 * 展示机构详细信息、认证状态、成员管理
 */
import { useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Input, Select, Tag, Tabs } from 'tdesign-react';
import { ArrowLeftIcon, EditIcon, SaveIcon, CloseIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getOrganization, updateOrganization } from '@/api/orgManagement';
import type { Organization } from '@/types/api';

const { TabPanel } = Tabs;

export default function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const isEditMode = searchParams.get('edit') === 'true';

  const [tabValue, setTabValue] = useState(0);
  const [editData, setEditData] = useState<Partial<Organization>>({});
  const [editing, setEditing] = useState(isEditMode);

  const { data: orgData, isLoading } = useQuery({
    queryKey: ['organization', id],
    queryFn: () => getOrganization(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Organization>) => {
      const { did, ...rest } = data;
      const cleaned = { ...rest, ...(did != null ? { did } : {}) };
      return updateOrganization(id!, cleaned);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization', id] });
      setEditing(false);
    },
  });

  const org = orgData?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!org) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">机构不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={org.name}
        subtitle={`机构编码: ${org.code}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '机构管理', href: '/dashboard/tds/organizations' },
          { label: org.name },
        ]}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              icon={<ArrowLeftIcon />}
              onClick={() => navigate('/dashboard/tds/organizations')}
            >
              返回
            </Button>
            {!editing ? (
              <Button icon={<EditIcon />} onClick={() => {
                setEditData({ name: org.name, code: org.code });
                setEditing(true);
              }}>
                编辑
              </Button>
            ) : (
              <>
                <Button
                  theme="primary"
                  icon={<SaveIcon />}
                  onClick={() => updateMutation.mutate(editData)}
                  disabled={updateMutation.isPending}
                >
                  保存
                </Button>
                <Button
                  icon={<CloseIcon />}
                  onClick={() => setEditing(false)}
                >
                  取消
                </Button>
              </>
            )}
          </div>
        }
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(val as number)}>
        <TabPanel value={0} label="基本信息">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-gray-500 block mb-1">机构名称</span>
                {editing ? (
                  <Input
                    value={editData.name || ''}
                    onChange={(val) => setEditData({ ...editData, name: String(val) })}
                  />
                ) : (
                  <p className="text-sm text-gray-700">{org.name}</p>
                )}
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">机构编码</span>
                {editing ? (
                  <Input
                    value={editData.code || ''}
                    onChange={(val) => setEditData({ ...editData, code: String(val) })}
                  />
                ) : (
                  <p className="text-sm text-gray-700">{org.code}</p>
                )}
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">DID</span>
                <p className="text-sm text-gray-700 font-mono">{org.did || '未分配'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">层级</span>
                <Tag variant="outline">{`L${org.level}`}</Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag
                  theme={org.status === 'active' ? 'success' : org.status === 'pending' ? 'warning' : 'danger'}
                >
                  {org.status}
                </Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">创建时间</span>
                <p className="text-sm text-gray-700">{new Date(org.created_at).toLocaleString('zh-CN')}</p>
              </div>
            </div>
          </PageSection>
        </TabPanel>

        <TabPanel value={1} label="认证管理">
          <PageSection className="mt-2">
            <p className="text-xs text-gray-500">认证管理功能开发中...</p>
          </PageSection>
        </TabPanel>

        <TabPanel value={2} label="成员管理">
          <PageSection className="mt-2">
            <p className="text-xs text-gray-500">成员管理功能开发中...</p>
          </PageSection>
        </TabPanel>

        <TabPanel value={3} label="角色权限">
          <PageSection className="mt-2">
            <p className="text-xs text-gray-500">角色权限管理功能开发中...</p>
          </PageSection>
        </TabPanel>
      </Tabs>
    </PageContainer>
  );
}
