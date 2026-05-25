/**
 * 用户管理页面
 * 用户 CRUD + 批量导入 + 重置密码 + 统计卡片 + ECharts图表
 */
import React, { useState, useCallback, useMemo, useRef } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, MessagePlugin, Pagination } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, RefreshIcon, UploadIcon,
  LockOnIcon, UsergroupIcon, UserAddIcon, CheckCircleFilledIcon,
  UserBlockedIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listUsers, createUser, updateUser, deleteUser, importUsers, resetPassword } from '@/api/ops';
import type { User } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';


const ROLE_OPTIONS = [
  { value: 'Admin', label: '管理员' },
  { value: 'DataProvider', label: '数据提供方' },
  { value: 'DataConsumer', label: '数据消费方' },
  { value: 'Auditor', label: '审计员' },
];

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'active', label: '活跃' },
  { value: 'inactive', label: '禁用' },
  { value: 'locked', label: '锁定' },
];

const userStatusLabel = (s: string): string => {
  const m: Record<string, string> = { active: '活跃', inactive: '禁用', locked: '锁定' };
  return m[s] ?? s;
};

const OpsUsersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ===== ECharts 配置 =====
  const userTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增用户', '活跃用户'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '用户数' },
    series: [
      { name: '新增用户', type: 'bar', data: [45, 52, 48, 65, 58, 72, 86], itemStyle: { color: '#2196f3' } },
      { name: '活跃用户', type: 'line', smooth: true, data: [820, 860, 890, 920, 950, 1020, 1080], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const roleDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '用户角色',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 420, name: '数据提供方', itemStyle: { color: '#2196f3' } },
          { value: 380, name: '数据消费方', itemStyle: { color: '#4caf50' } },
          { value: 320, name: '审计员', itemStyle: { color: '#ff9800' } },
          { value: 136, name: '管理员', itemStyle: { color: '#9c27b0' } },
        ],
      },
    ],
  }), []);

  // ===== 筛选 & 分页 =====
  const [filterKeyword, setFilterKeyword] = useState<string>('');
  const [filterRole, setFilterRole] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 创建/编辑弹窗 =====
  const [editOpen, setEditOpen] = useState<boolean>(false);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editId, setEditId] = useState<string>('');
  const [formUsername, setFormUsername] = useState<string>('');
  const [formPassword, setFormPassword] = useState<string>('');
  const [formEmail, setFormEmail] = useState<string>('');
  const [formPhone, setFormPhone] = useState<string>('');
  const [formRole, setFormRole] = useState<string>('DataProvider');
  const [formOrgId, setFormOrgId] = useState<string>('');

  // ===== 删除确认 =====
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  // ===== 重置密码确认 =====
  const [resetTarget, setResetTarget] = useState<User | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['users', page, pageSize, filterKeyword, filterRole, filterStatus],
    queryFn: () =>
      listUsers({
        page: page + 1,
        page_size: pageSize,
        keyword: filterKeyword || undefined,
        role: filterRole || undefined,
        status: filterStatus || undefined,
      }),
  });

  const items: User[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalUsers: total,
    activeUsers: items.filter(u => u.status === 'active').length,
    newThisMonth: items.filter(u => {
      const now = new Date();
      const created = new Date(u.created_at);
      return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear();
    }).length,
    disabledUsers: items.filter(u => u.status === 'disabled').length,
  }), [items, total]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<User> & { password: string }) => createUser(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      closeEditDialog();
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: Partial<User> }) => updateUser(id, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      closeEditDialog();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setDeleteTarget(null);
    },
  });

  const importMut = useMutation({
    mutationFn: (file: File) => importUsers(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const resetMut = useMutation({
    mutationFn: (id: string) => resetPassword(id),
    onSuccess: () => {
      setResetTarget(null);
    },
  });

  // ===== 辅助方法 =====
  const closeEditDialog = useCallback(() => {
    setEditOpen(false);
    setEditMode(false);
    setEditId('');
    setFormUsername('');
    setFormPassword('');
    setFormEmail('');
    setFormPhone('');
    setFormRole('DataProvider');
    setFormOrgId('');
  }, []);

  const openCreateDialog = useCallback(() => {
    setEditMode(false);
    setEditId('');
    setFormUsername('');
    setFormPassword('');
    setFormEmail('');
    setFormPhone('');
    setFormRole('DataProvider');
    setFormOrgId('');
    setEditOpen(true);
  }, []);

  const openEditDialog = useCallback((user: User) => {
    setEditMode(true);
    setEditId(user.id);
    setFormUsername(user.username);
    setFormPassword('');
    setFormEmail(user.email ?? '');
    setFormPhone(user.phone ?? '');
    setFormRole(user.role);
    setFormOrgId(user.organization_id);
    setEditOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (editMode) {
      updateMut.mutate({
        id: editId,
        data: {
          username: formUsername,
          email: formEmail || undefined,
          phone: formPhone || undefined,
          role: formRole,
          organization_id: formOrgId,
        },
      });
    } else {
      createMut.mutate({
        username: formUsername,
        password: formPassword,
        email: formEmail || undefined,
        phone: formPhone || undefined,
        role: formRole,
        organization_id: formOrgId,
      });
    }
  }, [editMode, editId, formUsername, formPassword, formEmail, formPhone, formRole, formOrgId, createMut, updateMut]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importMut.mutate(file);
      e.target.value = '';
    }
  }, [importMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '用户管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '新增用户', icon: <AddIcon />, onClick: openCreateDialog, variant: 'contained' },
      { label: '批量导入', icon: <UploadIcon />, onClick: () => fileInputRef.current?.click(), variant: 'outlined' },
    ],
    [openCreateDialog],
  );

  return (
    <PageContainer>
      <PageHeader
        title="用户管理"
        subtitle="管理系统用户，支持增删改查、批量导入与密码重置"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['users'] }), tooltip: '刷新' },
        ]}
      />
      <input ref={fileInputRef} type="file" accept=".csv,.xlsx" hidden onChange={handleFileChange} />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总用户数" value={stats.totalUsers} icon={<UsergroupIcon />} gradient="purple" unit="" />
        <MetricsCard title="活跃用户" value={stats.activeUsers} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="本月新增" value={stats.newThisMonth} icon={<UserAddIcon />} gradient="cyan" unit="" />
        <MetricsCard title="已禁用" value={stats.disabledUsers} icon={<UserBlockedIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <div className="md:col-span-2"><ChartCard title="用户增长趋势" option={userTrendOption} height={300} /></div>
        <ChartCard title="用户角色分布" option={roleDistOption} height={300} />
      </div>

      {/* 搜索过滤栏 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <Input
            value={filterKeyword}
            onChange={(val) => { setFilterKeyword(String(val)); setPage(0); }}
            placeholder="搜索用户名/邮箱"
            style={{ minWidth: 200 }}
          />
          <Select
            value={filterRole}
            onChange={(val) => { setFilterRole(String(val)); setPage(0); }}
            options={[{ label: '全部角色', value: '' }, ...ROLE_OPTIONS]}
            style={{ minWidth: 140 }}
            clearable
          />
          <Select
            value={filterStatus}
            onChange={(val) => { setFilterStatus(String(val)); setPage(0); }}
            options={STATUS_OPTIONS}
            style={{ minWidth: 140 }}
            clearable
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold">用户名</th>
                <th className="px-4 py-3 text-left font-bold">姓名</th>
                <th className="px-4 py-3 text-left font-bold">邮箱</th>
                <th className="px-4 py-3 text-left font-bold">角色</th>
                <th className="px-4 py-3 text-left font-bold">组织</th>
                <th className="px-4 py-3 text-left font-bold">状态</th>
                <th className="px-4 py-3 text-left font-bold">最后登录</th>
                <th className="px-4 py-3 text-center font-bold w-[200px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium">{row.username}</td>
                  <td className="px-4 py-3">{(row as any).full_name ?? (row as any).display_name ?? row.username}</td>
                  <td className="px-4 py-3">{row.email ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Tag variant="outline">{ROLE_OPTIONS.find((o) => o.value === row.role)?.label ?? row.role}</Tag>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-600 truncate max-w-[100px] inline-block">{row.organization_id}</span>
                  </td>
                  <td className="px-4 py-3"><StatusTag status={userStatusLabel(row.status)} /></td>
                  <td className="px-4 py-3">{row.last_login_at ? new Date(row.last_login_at).toLocaleString('zh-CN') : '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex gap-1 justify-center">
                      <Tooltip content="编辑">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => openEditDialog(row)}>
                          <EditIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content={row.status === 'active' ? '禁用' : '启用'}>
                        <span
                          className={`cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center ${row.status === 'active' ? 'text-orange-500' : 'text-green-500'}`}
                          onClick={() => {
                            updateMut.mutate({
                              id: row.id,
                              data: { status: row.status === 'active' ? 'inactive' : 'active' },
                            });
                          }}
                        >
                          {row.status === 'active' ? <UserBlockedIcon /> : <CheckCircleFilledIcon />}
                        </span>
                      </Tooltip>
                      <Tooltip content="重置密码">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-500" onClick={() => setResetTarget(row)}>
                          <LockOnIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="删除">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500" onClick={() => setDeleteTarget(row)}>
                          <DeleteIcon />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end p-3 border-t border-gray-100">
          <Pagination
            total={total}
            current={page + 1}
            pageSize={pageSize}
            onChange={(pageInfo) => {
              setPage(pageInfo.current - 1);
              setPageSize(pageInfo.pageSize);
            }}
          />
        </div>
      </div>

      {/* 创建/编辑弹窗 */}
      <Dialog visible={editOpen} onClose={closeEditDialog} header={editMode ? '编辑用户' : '新增用户'} width="480px">
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">用户名</label><Input value={formUsername} onChange={(val) => setFormUsername(String(val))} /></div>
          {!editMode && (
            <div><label className="block text-sm text-gray-600 mb-1">密码</label><Input type="password" value={formPassword} onChange={(val) => setFormPassword(String(val))} /></div>
          )}
          <Input label="邮箱" value={formEmail} onChange={(val) => setFormEmail(String(val))} />
          <Input label="手机" value={formPhone} onChange={(val) => setFormPhone(String(val))} />
          <Select
            label="角色"
            value={formRole}
            onChange={(val) => setFormRole(String(val))}
            options={ROLE_OPTIONS}
          />
          <div><label className="block text-sm text-gray-600 mb-1">组织 ID</label><Input value={formOrgId} onChange={(val) => setFormOrgId(String(val))} /></div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button onClick={closeEditDialog}>取消</Button>
          <Button theme="primary" disabled={!formUsername.trim() || (!editMode && !formPassword.trim())} onClick={handleSubmit}>
            {editMode ? '保存' : '创建'}
          </Button>
        </div>
      </Dialog>

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除用户"
        message={`确定要删除用户「${deleteTarget?.username ?? ''}」吗？此操作不可恢复。`}
        type="danger"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />

      {/* 重置密码确认 */}
      <ConfirmDialog
        open={!!resetTarget}
        title="重置密码"
        message={`确定要重置用户「${resetTarget?.username ?? ''}」的密码吗？`}
        type="warning"
        onConfirm={() => resetTarget && resetMut.mutate(resetTarget.id)}
        onCancel={() => setResetTarget(null)}
        loading={resetMut.isPending}
      />

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default OpsUsersPage;
