/**
 * DID 身份管理页面
 * DID 创建/解析/更新/停用 + 统计卡片 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Tooltip, Dialog, Pagination } from 'tdesign-react';
import {
  AddIcon, BrowseIcon, EditIcon, CloseIcon, RefreshIcon,
  KeyIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon,
} from 'tdesign-icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createDid, resolveDid, updateDidDocument, deactivateDid } from '@/api/security';
import { listOrganizations } from '@/api/ops';
import type { DidDocument, Organization } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';


const didStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '活跃', DEACTIVATED: '已停用' };
  return m[s] ?? s;
};

const SecurityDidPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 获取组织数据（含 DID） =====
  const { data: orgsData, isLoading: orgsLoading } = useQuery({
    queryKey: ['organizations-for-did'],
    queryFn: () => listOrganizations({ page: 1, page_size: 200 }),
  });
  const allOrgs: Organization[] = orgsData?.data?.items ?? [];
  const didOrgs = allOrgs.filter((o) => !!o.did);

  // ===== 从真实数据计算统计 =====
  const stats = useMemo(() => {
    const totalCreated = didOrgs.length;
    const active = didOrgs.filter((o) => o.status === 'active').length;
    const deactivated = didOrgs.filter((o) => o.status !== 'active').length;
    return { totalCreated, active, deactivated, orgCount: allOrgs.length };
  }, [didOrgs, allOrgs]);

  // ===== DID 列表（从组织推导） =====
  const didItems = useMemo(
    () => didOrgs.map((o) => ({
      did: o.did!,
      method: o.did!.split(':')[1] ?? 'unknown',
      status: o.status === 'active' ? 'ACTIVE' : 'DEACTIVATED',
      controller: o.name,
      orgId: o.id,
    })),
    [didOrgs],
  );

  // ===== 创建 DID 弹窗 =====
  const [createOpen, setCreateOpen] = useState<boolean>(false);
  const [createPublicKey, setCreatePublicKey] = useState<string>('');
  const [createMethod, setCreateMethod] = useState<string>('');
  const [createController, setCreateController] = useState<string>('');

  // ===== 解析 DID 弹窗 =====
  const [resolveOpen, setResolveOpen] = useState<boolean>(false);
  const [resolveInput, setResolveInput] = useState<string>('');
  const [resolveResult, setResolveResult] = useState<DidDocument | null>(null);

  // ===== 更新 DID 弹窗 =====
  const [updateOpen, setUpdateOpen] = useState<boolean>(false);
  const [updateDid, setUpdateDid] = useState<string>('');
  const [updateEndpoints, setUpdateEndpoints] = useState<string>('[]');
  const [updateAddAuth, setUpdateAddAuth] = useState<string>('[]');
  const [updateRemoveAuth, setUpdateRemoveAuth] = useState<string>('[]');

  // ===== 停用确认 =====
  const [deactivateTarget, setDeactivateTarget] = useState<DidDocument | null>(null);

  // ===== 分页状态（用于 DID 列表） =====
  const [listPage, setListPage] = useState<number>(0);
  const [listPageSize, setListPageSize] = useState<number>(10);
  const pagedDidItems = useMemo(
    () => didItems.slice(listPage * listPageSize, (listPage + 1) * listPageSize),
    [didItems, listPage, listPageSize],
  );

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: { method?: string; public_key: string; controller?: string }) => createDid(d),
    onSuccess: () => {
      setCreateOpen(false);
      setCreatePublicKey(''); setCreateMethod(''); setCreateController('');
    },
  });

  const resolveMut = useMutation({
    mutationFn: (did: string) => resolveDid(did),
    onSuccess: (res) => {
      setResolveResult(res.data ?? null);
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ did, data }: { did: string; data: { service_endpoints?: Record<string, unknown>[]; add_authentication?: Record<string, unknown>[]; remove_authentication?: string[] } }) =>
      updateDidDocument(did, data),
    onSuccess: () => {
      setUpdateOpen(false);
      setUpdateDid(''); setUpdateEndpoints('[]'); setUpdateAddAuth('[]'); setUpdateRemoveAuth('[]');
    },
  });

  const deactivateMut = useMutation({
    mutationFn: (did: string) => deactivateDid(did),
    onSuccess: () => { setDeactivateTarget(null); },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: 'DID 管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '创建 DID', icon: <AddIcon />, onClick: () => setCreateOpen(true), variant: 'contained' },
      { label: '解析 DID', icon: <BrowseIcon />, onClick: () => { setResolveInput(''); setResolveResult(null); setResolveOpen(true); }, variant: 'outlined' },
    ],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="DID 身份管理"
        subtitle="管理去中心化身份，支持创建、解析、更新与停用"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => {}, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      {orgsLoading ? (
        <div className="flex justify-center py-4">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : (
        <StatGrid columns={4}>
          <MetricsCard title="已绑定DID的组织" value={stats.totalCreated} icon={<KeyIcon />} gradient="purple" unit="" />
          <MetricsCard title="活跃DID" value={stats.active} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
          <MetricsCard title="非活跃DID" value={stats.deactivated} icon={<ErrorCircleFilledIcon />} gradient="red" unit="" />
          <MetricsCard title="组织总数" value={stats.orgCount} icon={<CheckCircleFilledIcon />} gradient="cyan" unit="" />
        </StatGrid>
      )}

      {/* DID 方法分布 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">DID 方法分布</h3>
        {orgsLoading ? (
          <div className="flex justify-center py-4">
            <div className="w-7 h-7 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : didOrgs.length === 0 ? (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg text-sm">
            暂无已绑定 DID 的组织数据。
          </div>
        ) : (
          <div className="flex flex-wrap gap-3 mt-1">
            {Object.entries(
              didOrgs.reduce<Record<string, number>>((acc, o) => {
                const method = o.did!.split(':')[1] ?? 'unknown';
                acc[method] = (acc[method] ?? 0) + 1;
                return acc;
              }, {}),
            ).map(([method, count]) => (
              <div key={method} className="rounded-lg border border-gray-200 p-3 min-w-[120px] text-center">
                <h2 className="text-xl font-bold text-blue-600">{count}</h2>
                <span className="text-xs text-gray-500">did:{method}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 操作指引 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <span className="text-xs text-gray-600">
          DID（去中心化标识符）用于在可信数据空间中标识实体身份。可通过上方按钮创建新 DID 或解析已有 DID。
        </span>
      </div>

      {/* DID 列表（从组织推导） */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          已绑定 DID 的组织 ({didItems.length})
        </h3>
        {orgsLoading ? (
          <div className="flex justify-center py-4">
            <div className="w-7 h-7 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : didItems.length === 0 ? (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg text-sm">
            暂无组织绑定 DID，请先在运营中心为组织创建 DID。
          </div>
        ) : (
          <>
            <div className="overflow-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">DID</th>
                    <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">方法</th>
                    <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">所属组织</th>
                    <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">状态</th>
                    <th className="text-center font-bold px-4 py-3 text-sm text-gray-600 w-36">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedDidItems.map((item) => (
                    <tr key={item.did} className="hover:bg-gray-50 border-b border-gray-100">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs whitespace-nowrap overflow-hidden text-ellipsis block max-w-xs">
                          {item.did}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{item.method}</td>
                      <td className="px-4 py-3 text-sm">{item.controller}</td>
                      <td className="px-4 py-3">
                        <StatusTag status={didStatusLabel(item.status)} color={item.status === 'ACTIVE' ? 'success' : 'error'} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <Tooltip content="解析">
                            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => { setResolveInput(item.did); setResolveOpen(true); }}>
                              <BrowseIcon />
                            </span>
                          </Tooltip>
                          <Tooltip content="更新">
                            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => { setUpdateDid(item.did); setUpdateOpen(true); }}>
                              <EditIcon />
                            </span>
                          </Tooltip>
                          <Tooltip content="停用">
                            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500" onClick={() => setDeactivateTarget({ did: item.did, status: item.status } as DidDocument)}>
                              <CloseIcon />
                            </span>
                          </Tooltip>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex justify-end mt-3">
              <Pagination
                total={didItems.length}
                current={listPage + 1}
                pageSize={listPageSize}
                onChange={(pageInfo) => {
                  setListPage(pageInfo.current - 1);
                  setListPageSize(pageInfo.pageSize);
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* 已解析的 DID 列表 */}
      {resolveResult && (
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">最近解析结果</h3>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">DID</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">方法</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">状态</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">控制者</th>
                <th className="text-center font-bold px-4 py-3 text-sm text-gray-600 w-36">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr className="hover:bg-gray-50 border-b border-gray-100">
                <td className="px-4 py-3">
                  <span className="font-mono text-xs whitespace-nowrap overflow-hidden text-ellipsis block max-w-xs">{resolveResult.did}</span>
                </td>
                <td className="px-4 py-3 text-sm">{resolveResult.method}</td>
                <td className="px-4 py-3">
                  <StatusTag status={didStatusLabel(resolveResult.status)} color={resolveResult.status === 'ACTIVE' ? 'success' : 'error'} />
                </td>
                <td className="px-4 py-3 text-sm whitespace-nowrap overflow-hidden text-ellipsis">{resolveResult.controller ?? '—'}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <Tooltip content="更新">
                      <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => { setUpdateDid(resolveResult.did); setUpdateOpen(true); }}>
                        <EditIcon />
                      </span>
                    </Tooltip>
                    <Tooltip content="停用">
                      <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500" onClick={() => setDeactivateTarget(resolveResult)}>
                        <CloseIcon />
                      </span>
                    </Tooltip>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div className="mt-2">
            <span className="text-xs text-gray-500">DID Document:</span>
            <div className="p-2 bg-gray-50 rounded-lg mt-1">
              <pre className="whitespace-pre-wrap font-mono text-xs max-h-48 overflow-auto">
                {JSON.stringify(resolveResult.document, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* 创建 DID 弹窗 */}
      <Dialog
        visible={createOpen}
        onClose={() => setCreateOpen(false)}
        header="创建 DID"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateOpen(false)}>取消</Button>
            <Button theme="primary" disabled={!createPublicKey.trim()} onClick={() => createMut.mutate({ public_key: createPublicKey, method: createMethod || undefined, controller: createController || undefined })}>创建</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">公钥 <span className="text-red-500">*</span></label>
            <Input value={createPublicKey} onChange={(val) => setCreatePublicKey(String(val))} placeholder="Base64 编码公钥" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">方法（可选）</label>
            <Input value={createMethod} onChange={(val) => setCreateMethod(String(val))} placeholder="例: web, key" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">控制者（可选）</label>
            <Input value={createController} onChange={(val) => setCreateController(String(val))} />
          </div>
        </div>
      </Dialog>

      {/* 解析 DID 弹窗 */}
      <Dialog
        visible={resolveOpen}
        onClose={() => { setResolveOpen(false); setResolveResult(null); }}
        header="解析 DID"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => { setResolveOpen(false); setResolveResult(null); }}>关闭</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input value={resolveInput} onChange={(val) => setResolveInput(String(val))} placeholder="did:web:example.com" className="flex-1" />
            <Button theme="primary" onClick={() => resolveInput.trim() && resolveMut.mutate(resolveInput)} disabled={!resolveInput.trim()}>解析</Button>
          </div>
          {resolveMut.isPending && <span className="text-sm text-gray-500">解析中...</span>}
          {resolveResult && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-800 mb-2">解析结果</h4>
              <pre className="whitespace-pre-wrap font-mono text-xs">
                {JSON.stringify(resolveResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Dialog>

      {/* 更新 DID 弹窗 */}
      <Dialog
        visible={updateOpen}
        onClose={() => setUpdateOpen(false)}
        header="更新 DID Document"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setUpdateOpen(false)}>取消</Button>
            <Button theme="primary" onClick={() => {
              let endpoints: Record<string, unknown>[] | undefined;
              let addAuth: Record<string, unknown>[] | undefined;
              let removeAuth: string[] | undefined;
              try { endpoints = JSON.parse(updateEndpoints || '[]'); } catch { endpoints = undefined; }
              try { addAuth = JSON.parse(updateAddAuth || '[]'); } catch { addAuth = undefined; }
              try { removeAuth = JSON.parse(updateRemoveAuth || '[]'); } catch { removeAuth = undefined; }
              updateMut.mutate({ did: updateDid, data: { service_endpoints: endpoints, add_authentication: addAuth, remove_authentication: removeAuth } });
            }}>更新</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">DID</label>
            <Input value={updateDid} disabled />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">服务端点 (JSON Array)</label>
            <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={updateEndpoints} onChange={(e) => setUpdateEndpoints(e.target.value)} rows={2} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">添加认证方式 (JSON Array)</label>
            <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={updateAddAuth} onChange={(e) => setUpdateAddAuth(e.target.value)} rows={2} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">移除认证方式 (JSON Array of IDs)</label>
            <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={updateRemoveAuth} onChange={(e) => setUpdateRemoveAuth(e.target.value)} rows={2} />
          </div>
        </div>
      </Dialog>

      {/* 停用确认 */}
      <ConfirmDialog
        open={!!deactivateTarget}
        title="停用 DID"
        message={`确定要停用 DID「${deactivateTarget?.did ?? ''}」吗？此操作不可恢复。`}
        type="danger"
        onConfirm={() => deactivateTarget && deactivateMut.mutate(deactivateTarget.did)}
        onCancel={() => setDeactivateTarget(null)}
        loading={deactivateMut.isPending}
      />

      <LoadingOverlay open={resolveMut.isPending || createMut.isPending} />
    </PageContainer>
  );
};

export default SecurityDidPage;
