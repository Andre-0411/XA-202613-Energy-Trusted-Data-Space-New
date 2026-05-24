/**
 * 组织管理页面
 * 左侧组织树 + 右侧详情/成员列表 + CRUD + 统计卡片
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, MessagePlugin, Pagination } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, RefreshIcon, ChevronDownIcon,
  ChevronRightIcon, UserBusinessFilledIcon, UsergroupIcon,
  FolderOpenIcon, InfoCircleIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listOrganizations, createOrganization, updateOrganization,
  deleteOrganization, getOrganizationMembers, getOrganizationStats,
} from '@/api/ops';
import type { Organization, User } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import MetricsCard from '@/components/common/MetricsCard';


// ==================== 常量 ====================

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'ACTIVE', label: '活跃' },
  { value: 'DISABLED', label: '禁用' },
];

const LEVEL_OPTIONS = [
  { value: 1, label: '一级' },
  { value: 2, label: '二级' },
  { value: 3, label: '三级' },
  { value: 4, label: '四级' },
];

const orgStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '活跃', DISABLED: '禁用' };
  return m[s] ?? s;
};

// ==================== 树节点组件 ====================

interface OrgTreeNodeProps {
  org: Organization;
  allOrgs: Organization[];
  selectedId: string | null;
  onSelect: (org: Organization) => void;
  depth: number;
}

/** 递归组织树节点 */
const OrgTreeNode: React.FC<OrgTreeNodeProps> = ({ org, allOrgs, selectedId, onSelect, depth }) => {
  const children = allOrgs.filter((o) => o.parent_id === org.id);
  const hasChildren = children.length > 0;
  const [open, setOpen] = useState<boolean>(depth < 2);

  const isSelected = selectedId === org.id;

  return (
    <div>
      <div
        className={`flex items-center py-1.5 px-2 rounded cursor-pointer transition-colors ${isSelected ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}`}
        style={{ paddingLeft: `${(1.5 + depth * 2) * 4}px` }}
        onClick={() => onSelect(org)}
      >
        {hasChildren ? (
          <span
            className="mr-1 p-0.5 cursor-pointer inline-flex items-center"
            onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
          >
            {open ? <ChevronDownIcon style={{ fontSize: '0.875rem' }} /> : <ChevronRightIcon style={{ fontSize: '0.875rem' }} />}
          </span>
        ) : (
          <span className="w-7 mr-1" />
        )}
        <FolderOpenIcon style={{ fontSize: '0.875rem', marginRight: '4px' }} className="text-gray-400" />
        <span className={`text-sm truncate flex-1 ${isSelected ? 'font-semibold' : ''}`}>{org.name}</span>
        <Tag variant="outline" size="small" style={{ marginLeft: '4px', height: '20px', fontSize: '0.7rem' }}>L{org.level}</Tag>
      </div>
      {hasChildren && open && (
        <div>
          {children.map((child) => (
            <OrgTreeNode
              key={child.id}
              org={child}
              allOrgs={allOrgs}
              selectedId={selectedId}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ==================== 主组件 ====================

const OpsOrgPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const orgGrowthOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增组织', '活跃组织'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增组织', type: 'bar', data: [3, 5, 4, 6, 8, 7, 9], itemStyle: { color: '#667eea' } },
      { name: '活跃组织', type: 'line', smooth: true, data: [25, 28, 30, 33, 38, 42, 48], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const orgLevelOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '组织层级',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 12, name: '一级组织', itemStyle: { color: '#667eea' } },
          { value: 18, name: '二级组织', itemStyle: { color: '#43e97b' } },
          { value: 15, name: '三级组织', itemStyle: { color: '#f093fb' } },
          { value: 8, name: '四级组织', itemStyle: { color: '#4facfe' } },
        ],
      },
    ],
  }), []);

  // ===== 选中 & 筛选 =====
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [memberPage, setMemberPage] = useState<number>(0);
  const [memberPageSize, setMemberPageSize] = useState<number>(10);

  // ===== 创建/编辑弹窗 =====
  const [editOpen, setEditOpen] = useState<boolean>(false);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editId, setEditId] = useState<string>('');
  const [formName, setFormName] = useState<string>('');
  const [formCode, setFormCode] = useState<string>('');
  const [formParentId, setFormParentId] = useState<string>('');
  const [formDid, setFormDid] = useState<string>('');
  const [formLevel, setFormLevel] = useState<number>(1);

  // ===== 删除确认 =====
  const [deleteTarget, setDeleteTarget] = useState<Organization | null>(null);

  // ===== 数据查询 =====
  const { data: orgData, isLoading: orgLoading } = useQuery({
    queryKey: ['organizations', filterStatus],
    queryFn: () => listOrganizations({ page: 1, page_size: 500, status: filterStatus || undefined }),
    retry: false,
  });

  const allOrgs: Organization[] = orgData?.data?.items ?? [];
  const rootOrgs = allOrgs.filter((o) => !o.parent_id);

  // 选中组织的成员列表
  const { data: memberData, isLoading: memberLoading } = useQuery({
    queryKey: ['orgMembers', selectedOrg?.id, memberPage, memberPageSize],
    queryFn: () => getOrganizationMembers(selectedOrg!.id, { page: memberPage + 1, page_size: memberPageSize }),
    enabled: !!selectedOrg,
  });

  const members: User[] = memberData?.data?.items ?? [];
  const memberTotal: number = memberData?.data?.total ?? 0;

  // 组织统计
  const { data: statsData } = useQuery({
    queryKey: ['orgStats', selectedOrg?.id],
    queryFn: () => getOrganizationStats(selectedOrg!.id),
    enabled: !!selectedOrg,
  });

  const stats = statsData?.data ?? {};

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<Organization>) => createOrganization(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      closeEditDialog();
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: Partial<Organization> }) => updateOrganization(id, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      closeEditDialog();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteOrganization(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      if (deleteTarget?.id === selectedOrg?.id) {
        setSelectedOrg(null);
      }
      setDeleteTarget(null);
    },
  });

  // ===== 辅助方法 =====
  const closeEditDialog = useCallback(() => {
    setEditOpen(false);
    setEditMode(false);
    setEditId('');
    setFormName('');
    setFormCode('');
    setFormParentId('');
    setFormDid('');
    setFormLevel(1);
  }, []);

  const openCreateDialog = useCallback(() => {
    setEditMode(false);
    setEditId('');
    setFormName('');
    setFormCode('');
    setFormParentId(selectedOrg?.id ?? '');
    setFormDid('');
    setFormLevel(selectedOrg ? Math.min(selectedOrg.level + 1, 4) : 1);
    setEditOpen(true);
  }, [selectedOrg]);

  const openEditDialog = useCallback((org: Organization) => {
    setEditMode(true);
    setEditId(org.id);
    setFormName(org.name);
    setFormCode(org.code);
    setFormParentId(org.parent_id ?? '');
    setFormDid(org.did ?? '');
    setFormLevel(org.level);
    setEditOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (editMode) {
      updateMut.mutate({
        id: editId,
        data: {
          name: formName,
          code: formCode,
          parent_id: formParentId || null,
          did: formDid || null,
          level: formLevel,
        },
      });
    } else {
      createMut.mutate({
        name: formName,
        code: formCode,
        parent_id: formParentId || null,
        did: formDid || null,
        level: formLevel,
      });
    }
  }, [editMode, editId, formName, formCode, formParentId, formDid, formLevel, createMut, updateMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '组织管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '创建组织', icon: <AddIcon />, onClick: openCreateDialog, variant: 'contained' },
    ],
    [openCreateDialog],
  );

  // ===== 父组织下拉选项（排除自身及其子节点） =====
  const parentOptions = useMemo(() => {
    if (editMode) {
      const getDescendantIds = (orgId: string): string[] => {
        const children = allOrgs.filter((o) => o.parent_id === orgId);
        return [orgId, ...children.flatMap((c) => getDescendantIds(c.id))];
      };
      const excludeIds = new Set(getDescendantIds(editId));
      return allOrgs.filter((o) => !excludeIds.has(o.id));
    }
    return allOrgs;
  }, [allOrgs, editMode, editId]);

  // ===== 角色标签映射 =====
  const roleLabel = (role: string): string => {
    const m: Record<string, string> = {
      Admin: '管理员',
      DataProvider: '数据提供方',
      DataConsumer: '数据消费方',
      Auditor: '审计员',
    };
    return m[role] ?? role;
  };

  return (
    <PageContainer>
      <PageHeader
        title="组织管理"
        subtitle="管理组织层级结构，查看组织详情与成员信息"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['organizations'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="flex items-center gap-4">
        <MetricsCard
          title="组织总数"
          value={allOrgs.length}
          icon={<FolderOpenIcon />}
          color="primary"
        />
        <MetricsCard
          title="成员总数"
          value={(stats.member_count as number) ?? 0}
          icon={<UsergroupIcon />}
          color="info"
        />
        <MetricsCard
          title="子组织数"
          value={(stats.children_count as number) ?? 0}
          icon={<UserBusinessFilledIcon />}
          color="success"
        />
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <div className="md:col-span-2"><ChartCard title="组织增长趋势" option={orgGrowthOption} height={300} /></div>
        <ChartCard title="组织层级分布" option={orgLevelOption} height={300} />
      </div>

      {/* 主体区域：左侧树 + 右侧详情 */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* 左侧组织树 */}
        <div className="w-80 flex-shrink-0 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
          {/* 筛选栏 */}
          <div className="p-3 border-b border-gray-200">
            <Select
              value={filterStatus}
              onChange={(val) => setFilterStatus(String(val))}
              options={STATUS_OPTIONS}
              style={{ width: '100%' }}
              clearable
            />
          </div>

          {/* 树列表 */}
          <div className="flex-1 overflow-auto py-2">
            {rootOrgs.length > 0 ? (
              <div>
                {rootOrgs.map((org) => (
                  <OrgTreeNode
                    key={org.id}
                    org={org}
                    allOrgs={allOrgs}
                    selectedId={selectedOrg?.id ?? null}
                    onSelect={setSelectedOrg}
                    depth={0}
                  />
                ))}
              </div>
            ) : (
              <div className="p-6 text-center">
                <span className="text-xs text-gray-500">暂无组织数据</span>
              </div>
            )}
          </div>
          <LoadingOverlay open={orgLoading} />
        </div>

        {/* 右侧详情区 */}
        <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
          {selectedOrg ? (
            <>
              {/* 组织基本信息 */}
              <div className="p-6 border-b border-gray-200">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center text-white">
                      <UserBusinessFilledIcon style={{ fontSize: '1.5rem' }} />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold">{selectedOrg.name}</h3>
                      <span className="text-xs text-gray-500">{selectedOrg.code}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" icon={<EditIcon />} onClick={() => openEditDialog(selectedOrg)}>编辑</Button>
                    <Button variant="outline" theme="danger" icon={<DeleteIcon />} onClick={() => setDeleteTarget(selectedOrg)}>删除</Button>
                  </div>
                </div>

                {/* 详情字段 */}
                <div className="flex gap-8 mt-4">
                  <div>
                    <span className="text-xs text-gray-400">DID</span>
                    <p className="text-sm font-medium">{selectedOrg.did ?? '—'}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">状态</span>
                    <div className="mt-0.5">
                      <StatusTag status={orgStatusLabel(selectedOrg.status)} />
                    </div>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">层级</span>
                    <p className="text-sm font-medium">第 {selectedOrg.level} 级</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">创建时间</span>
                    <p className="text-sm font-medium">
                      {new Date(selectedOrg.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">更新时间</span>
                    <p className="text-sm font-medium">
                      {new Date(selectedOrg.updated_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                </div>
              </div>

              {/* 成员列表 */}
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="px-6 py-3 border-b border-gray-200">
                  <div className="flex items-center gap-2">
                    <UsergroupIcon style={{ fontSize: '0.875rem' }} className="text-gray-400" />
                    <span className="text-sm font-semibold">成员列表</span>
                    <Tag variant="outline" size="small">{memberTotal}</Tag>
                  </div>
                </div>
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-bold">用户名</th>
                        <th className="px-4 py-3 text-left font-bold">邮箱</th>
                        <th className="px-4 py-3 text-left font-bold">角色</th>
                        <th className="px-4 py-3 text-left font-bold">状态</th>
                        <th className="px-4 py-3 text-left font-bold">最后登录</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((m) => (
                        <tr key={m.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 font-medium">{m.username}</td>
                          <td className="px-4 py-3">{m.email ?? '—'}</td>
                          <td className="px-4 py-3">
                            <Tag variant="outline">{roleLabel(m.role)}</Tag>
                          </td>
                          <td className="px-4 py-3"><StatusTag status={orgStatusLabel(m.status)} /></td>
                          <td className="px-4 py-3">
                            {m.last_login_at ? new Date(m.last_login_at).toLocaleString('zh-CN') : '—'}
                          </td>
                        </tr>
                      ))}
                      {members.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-gray-400">暂无成员</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="flex justify-end p-3 border-t border-gray-100">
                  <Pagination
                    total={memberTotal}
                    current={memberPage + 1}
                    pageSize={memberPageSize}
                    onChange={(pageInfo) => {
                      setMemberPage(pageInfo.current - 1);
                      setMemberPageSize(pageInfo.pageSize);
                    }}
                  />
                </div>
                <LoadingOverlay open={memberLoading} />
              </div>
            </>
          ) : (
            /* 空状态 */
            <div className="flex-1 flex flex-col items-center justify-center">
              <InfoCircleIcon style={{ fontSize: '4rem' }} className="text-gray-300 mb-4" />
              <h3 className="text-base text-gray-400 mb-1">请选择一个组织</h3>
              <span className="text-xs text-gray-300">点击左侧组织树中的节点查看详情</span>
            </div>
          )}
        </div>
      </div>

      {/* 创建/编辑弹窗 */}
      <Dialog visible={editOpen} onClose={closeEditDialog} header={editMode ? '编辑组织' : '创建组织'} width="480px">
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">组织名称</label><Input value={formName} onChange={(val) => setFormName(String(val))} /></div>
          <div><label className="block text-sm text-gray-600 mb-1">组织编码</label><Input value={formCode} onChange={(val) => setFormCode(String(val))} /></div>
          <Select
            label="上级组织"
            value={formParentId}
            onChange={(val) => setFormParentId(String(val))}
            options={[{ label: '无（顶级组织）', value: '' }, ...parentOptions.map((o) => ({ label: o.name, value: o.id }))]}
            style={{ width: '100%' }}
          />
          <Select
            label="层级"
            value={formLevel}
            onChange={(val) => setFormLevel(Number(val))}
            options={LEVEL_OPTIONS}
            style={{ width: '100%' }}
          />
          <Input label="DID（可选）" value={formDid} onChange={(val) => setFormDid(String(val))} placeholder="did:example:..." />
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button onClick={closeEditDialog}>取消</Button>
          <Button
            theme="primary"
            disabled={!formName.trim() || !formCode.trim()}
            onClick={handleSubmit}
          >
            {editMode ? '保存' : '创建'}
          </Button>
        </div>
      </Dialog>

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除组织"
        message={`确定要删除组织「${deleteTarget?.name ?? ''}」吗？此操作不可恢复。`}
        type="danger"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />
    </PageContainer>
  );
};

export default OpsOrgPage;
