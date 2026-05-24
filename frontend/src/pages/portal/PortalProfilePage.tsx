/**
 * 个人中心页面
 * 个人信息展示/编辑 + 修改密码 + API安全设置（MFA）
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Tag, Avatar, Input, Switch, Dialog, Divider, MessagePlugin,
} from 'tdesign-react';
import {
  EditIcon, LockOnIcon, UserIcon, MailIcon, CallIcon, BuildingIcon,
  FingerprintIcon, SecuredIcon, ServerIcon, DashboardIcon, SaveIcon, CloseIcon,
  BrowseIcon, BrowseOffIcon, CopyIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { changePassword, getMfaStatus, mfaSetup, mfaEnable, mfaDisable } from '@/api/auth';
import type { MfaSetupResponse } from '@/api/auth';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/** 信息项组件 */
interface InfoItemProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const InfoItem: React.FC<InfoItemProps> = ({ icon, label, value }) => (
  <div className="flex items-center gap-3 py-3">
    <div className="flex items-center text-gray-500">{icon}</div>
    <div className="min-w-[100px]">
      <span className="text-xs text-gray-500">{label}</span>
    </div>
    <span className="text-sm font-medium text-gray-900">{value}</span>
  </div>
);

const PortalProfilePage: React.FC = () => {
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  // ===== MFA 状态查询 =====
  const { data: mfaStatus, isLoading: mfaLoading } = useQuery({
    queryKey: ['mfa-status', user?.user_id],
    queryFn: async () => {
      const res = await getMfaStatus(user!.user_id);
      return res.data;
    },
    enabled: !!user?.user_id,
  });

  // ===== 用户活动统计 =====
  const activityStats = useMemo(() => ({
    totalLogins: 156,
    dataAccess: 89,
    computeTasks: 23,
    lastActive: '2026-05-18',
  }), []);

  // ===== ECharts 配置 =====
  const loginTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['登录次数', '数据访问'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '次数' },
    series: [
      { name: '登录次数', type: 'line', smooth: true, data: [18, 22, 25, 20, 28, 32, 35], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#667eea' } },
      { name: '数据访问', type: 'line', smooth: true, data: [12, 15, 18, 14, 20, 25, 28], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#43e97b' } },
    ],
  }), []);

  const activityDistributionOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '活动类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 56, name: '数据查询', itemStyle: { color: '#667eea' } },
          { value: 23, name: '计算任务', itemStyle: { color: '#43e97b' } },
          { value: 18, name: '文件下载', itemStyle: { color: '#f093fb' } },
          { value: 12, name: 'API调用', itemStyle: { color: '#4facfe' } },
        ],
      },
    ],
  }), []);

  // ===== 编辑状态 =====
  const [editing, setEditing] = useState<boolean>(false);
  const [formEmail, setFormEmail] = useState<string>(user?.email ?? '');
  const [formPhone, setFormPhone] = useState<string>(user?.phone ?? '');

  // ===== 密码修改弹窗 =====
  const [pwdOpen, setPwdOpen] = useState<boolean>(false);
  const [oldPassword, setOldPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showOldPwd, setShowOldPwd] = useState<boolean>(false);
  const [showNewPwd, setShowNewPwd] = useState<boolean>(false);
  const [pwdError, setPwdError] = useState<string>('');

  // ===== MFA 设置弹窗 =====
  const [mfaSetupOpen, setMfaSetupOpen] = useState<boolean>(false);
  const [mfaSetupData, setMfaSetupData] = useState<MfaSetupResponse | null>(null);
  const [mfaTotpCode, setMfaTotpCode] = useState<string>('');
  const [mfaSetupStep, setMfaSetupStep] = useState<'scan' | 'verify'>('scan');
  const [mfaSetupError, setMfaSetupError] = useState<string>('');
  const [showMfaSecret, setShowMfaSecret] = useState<boolean>(false);

  // ===== MFA 禁用弹窗 =====
  const [mfaDisableOpen, setMfaDisableOpen] = useState<boolean>(false);
  const [mfaDisablePassword, setMfaDisablePassword] = useState<string>('');
  const [mfaDisableError, setMfaDisableError] = useState<string>('');
  const [showDisablePwd, setShowDisablePwd] = useState<boolean>(false);

  // ===== 密码修改 Mutation =====
  const changePwdMut = useMutation({
    mutationFn: () => changePassword(oldPassword, newPassword),
    onSuccess: () => {
      MessagePlugin.success('密码修改成功');
      setPwdOpen(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPwdError('');
    },
    onError: (err: Error) => {
      setPwdError(err.message || '密码修改失败，请重试');
      MessagePlugin.error(err.message || '密码修改失败，请重试');
    },
  });

  // ===== MFA Setup Mutation =====
  const mfaSetupMut = useMutation({
    mutationFn: () => mfaSetup(user!.user_id),
    onSuccess: (res) => {
      setMfaSetupData(res.data);
      setMfaSetupStep('scan');
      setMfaTotpCode('');
      setMfaSetupError('');
      setShowMfaSecret(false);
      setMfaSetupOpen(true);
    },
    onError: (err: Error) => {
      MessagePlugin.error(err.message || 'MFA 初始化失败，请重试');
    },
  });

  // ===== MFA Enable Mutation =====
  const mfaEnableMut = useMutation({
    mutationFn: () => mfaEnable(user!.user_id, mfaTotpCode),
    onSuccess: (res) => {
      if (res.data?.success) {
        MessagePlugin.success('MFA 已成功启用');
        setMfaSetupOpen(false);
        setMfaTotpCode('');
        queryClient.invalidateQueries({ queryKey: ['mfa-status'] });
      } else {
        setMfaSetupError('验证码无效，请重新输入');
      }
    },
    onError: (err: any) => {
      setMfaSetupError(err?.response?.data?.detail || err.message || '验证码无效，请重新输入');
    },
  });

  // ===== MFA Disable Mutation =====
  const mfaDisableMut = useMutation({
    mutationFn: () => mfaDisable(user!.user_id, mfaDisablePassword),
    onSuccess: (res) => {
      if (res.data?.success) {
        MessagePlugin.success('MFA 已禁用');
        setMfaDisableOpen(false);
        setMfaDisablePassword('');
        setMfaDisableError('');
        queryClient.invalidateQueries({ queryKey: ['mfa-status'] });
      } else {
        setMfaDisableError('禁用失败，请检查密码');
      }
    },
    onError: (err: any) => {
      setMfaDisableError(err?.response?.data?.detail || err.message || '禁用失败，请检查密码');
    },
  });

  // ===== MFA Switch 切换 =====
  const handleMfaToggle = useCallback((val: boolean) => {
    if (val) {
      mfaSetupMut.mutate();
    } else {
      setMfaDisablePassword('');
      setMfaDisableError('');
      setShowDisablePwd(false);
      setMfaDisableOpen(true);
    }
  }, [mfaSetupMut]);

  // ===== MFA 启用确认 =====
  const handleMfaEnableConfirm = useCallback(() => {
    if (mfaTotpCode.length !== 6) {
      setMfaSetupError('请输入6位验证码');
      return;
    }
    setMfaSetupError('');
    mfaEnableMut.mutate();
  }, [mfaTotpCode, mfaEnableMut]);

  // ===== MFA 禁用确认 =====
  const handleMfaDisableConfirm = useCallback(() => {
    if (!mfaDisablePassword.trim()) {
      setMfaDisableError('请输入密码确认');
      return;
    }
    setMfaDisableError('');
    mfaDisableMut.mutate();
  }, [mfaDisablePassword, mfaDisableMut]);

  // ===== 复制到剪贴板 =====
  const handleCopy = useCallback((text: string) => {
    navigator.clipboard.writeText(text).then(
      () => MessagePlugin.success('已复制到剪贴板'),
      () => MessagePlugin.error('复制失败'),
    );
  }, []);

  // ===== 辅助方法 =====
  const handleStartEdit = useCallback(() => {
    setFormEmail(user?.email ?? '');
    setFormPhone(user?.phone ?? '');
    setEditing(true);
  }, [user]);

  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    setFormEmail(user?.email ?? '');
    setFormPhone(user?.phone ?? '');
  }, [user]);

  const handleSaveEdit = useCallback(() => {
    setEditing(false);
  }, []);

  const handleOpenPwdDialog = useCallback(() => {
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setPwdError('');
    setShowOldPwd(false);
    setShowNewPwd(false);
    setPwdOpen(true);
  }, []);

  const handleClosePwdDialog = useCallback(() => {
    setPwdOpen(false);
    setPwdError('');
  }, []);

  const handleSubmitPwd = useCallback(() => {
    if (!oldPassword.trim()) {
      setPwdError('请输入旧密码');
      return;
    }
    if (newPassword.length < 8) {
      setPwdError('新密码长度至少8位');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwdError('两次输入的新密码不一致');
      return;
    }
    setPwdError('');
    changePwdMut.mutate();
  }, [oldPassword, newPassword, confirmPassword, changePwdMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '门户功能' }, { label: '个人中心' }],
    [],
  );

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

  if (!user) {
    return (
      <div className="flex h-full flex-col gap-4">
        <PageHeader title="个人中心" subtitle="查看和管理您的个人信息" breadcrumbs={breadcrumbs} />
        <div className="rounded-xl bg-white p-8 text-center">
          <p className="text-gray-500">请先登录</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <PageHeader
        title="个人中心"
        subtitle="查看和管理您的个人信息、密码和安全设置"
        breadcrumbs={breadcrumbs}
      />

      {/* 活动统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总登录次数" value={activityStats.totalLogins} unit="次" icon={<UserIcon />} gradient="purple" />
        <StatCard title="数据访问次数" value={activityStats.dataAccess} unit="次" icon={<ServerIcon />} gradient="green" />
        <StatCard title="计算任务数" value={activityStats.computeTasks} unit="个" icon={<DashboardIcon />} gradient="orange" />
        <StatCard title="最后活跃" value={0} unit={activityStats.lastActive} icon={<SecuredIcon />} gradient="red" />
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="登录与数据访问趋势" option={loginTrendOption} className="lg:col-span-2" />
        <ChartCard title="活动类型分布" option={activityDistributionOption} />
      </div>

      {/* 个人信息卡片 */}
      <div className="rounded-xl bg-white p-6" style={{ border: '1px solid #e5e7eb' }}>
        <div className="flex items-start gap-6">
          {/* 头像 */}
          <Avatar size="80px" className="bg-blue-600 text-2xl font-bold">
            {user.username.charAt(0).toUpperCase()}
          </Avatar>

          {/* 基本信息 */}
          <div className="flex-1">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h5 className="text-xl font-bold text-gray-900">{user.username}</h5>
                <Tag variant="outline" theme="primary">{roleLabel(user.role)}</Tag>
                <StatusTag status={user.status === 'ACTIVE' ? '活跃' : (user.status ?? '未知')} />
              </div>
              {!editing && (
                <Button variant="outline" icon={<EditIcon />} onClick={handleStartEdit}>
                  编辑信息
                </Button>
              )}
            </div>

            <Divider className="mb-4" />

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <InfoItem
                icon={<UserIcon className="text-sm" />}
                label="用户ID"
                value={user.user_id}
              />
              {editing ? (
                <div className="flex items-center gap-2">
                  <MailIcon className="text-sm text-gray-400" />
                  <Input
                    label="邮箱"
                    value={formEmail}
                    onChange={(val) => setFormEmail(val as string)}
                    className="flex-1"
                  />
                </div>
              ) : (
                <InfoItem
                  icon={<MailIcon className="text-sm" />}
                  label="邮箱"
                  value={user.email ?? '未设置'}
                />
              )}
              {editing ? (
                <div className="flex items-center gap-2">
                  <CallIcon className="text-sm text-gray-400" />
                  <Input
                    label="手机号"
                    value={formPhone}
                    onChange={(val) => setFormPhone(val as string)}
                    className="flex-1"
                  />
                </div>
              ) : (
                <InfoItem
                  icon={<CallIcon className="text-sm" />}
                  label="手机号"
                  value={user.phone ?? '未设置'}
                />
              )}
              <InfoItem
                icon={<FingerprintIcon className="text-sm" />}
                label="DID"
                value={user.did ?? '未绑定'}
              />
              <InfoItem
                icon={<BuildingIcon className="text-sm" />}
                label="组织ID"
                value={user.organization_id}
              />
              <InfoItem
                icon={<SecuredIcon className="text-sm" />}
                label="部门ID"
                value={user.department_id ?? '未分配'}
              />
            </div>

            {/* 编辑操作栏 */}
            {editing && (
              <div className="mt-4 flex gap-2">
                <Button theme="primary" icon={<SaveIcon />} onClick={handleSaveEdit}>
                  保存
                </Button>
                <Button variant="outline" icon={<CloseIcon />} onClick={handleCancelEdit}>
                  取消
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 安全设置 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 修改密码 */}
        <div className="rounded-xl bg-white h-full" style={{ border: '1px solid #e5e7eb' }}>
          <div className="p-6">
            <div className="mb-4 flex items-center gap-3">
              <LockOnIcon className="text-blue-600" />
              <h6 className="text-base font-semibold">修改密码</h6>
            </div>
            <p className="mb-4 text-sm text-gray-500">
              定期更换密码可以提高账户安全性。密码长度至少8位，建议包含大小写字母、数字和特殊字符。
            </p>
            <Button variant="outline" icon={<LockOnIcon />} onClick={handleOpenPwdDialog}>
              修改密码
            </Button>
          </div>
        </div>

        {/* API 安全设置 / MFA */}
        <div className="rounded-xl bg-white h-full" style={{ border: '1px solid #e5e7eb' }}>
          <div className="p-6">
            <div className="mb-4 flex items-center gap-3">
              <SecuredIcon className="text-blue-600" />
              <h6 className="text-base font-semibold">API 安全设置</h6>
            </div>
            <p className="mb-4 text-sm text-gray-500">
              开启多因素认证（MFA）后，登录时需要额外的验证码验证，提升账户安全性。
            </p>
            <div className="flex items-center gap-3">
              <Switch
                value={mfaStatus?.enabled ?? false}
                onChange={handleMfaToggle}
                disabled={mfaLoading || mfaSetupMut.isPending || mfaEnableMut.isPending || mfaDisableMut.isPending}
                loading={mfaSetupMut.isPending || mfaEnableMut.isPending || mfaDisableMut.isPending}
              />
              <span className="text-sm">MFA 多因素认证</span>
              {mfaLoading ? (
                <Tag variant="outline">加载中...</Tag>
              ) : mfaStatus?.enabled ? (
                <Tag theme="success" variant="outline">已开启</Tag>
              ) : (
                <Tag variant="outline">未开启</Tag>
              )}
            </div>
            {mfaStatus?.enabled && mfaStatus.backup_codes_remaining > 0 && (
              <p className="mt-2 text-xs text-gray-400">
                剩余备份码: {mfaStatus.backup_codes_remaining} 个
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 修改密码弹窗 */}
      <Dialog
        header="修改密码"
        visible={pwdOpen}
        onClose={handleClosePwdDialog}
        width="480px"
        footer={
          <div className="flex justify-end gap-2 px-6 pb-4">
            <Button onClick={handleClosePwdDialog}>取消</Button>
            <Button
              theme="primary"
              disabled={!oldPassword.trim() || !newPassword.trim() || !confirmPassword.trim() || newPassword !== confirmPassword}
              onClick={handleSubmitPwd}
            >
              确认修改
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-5 px-6 pt-2">
          {pwdError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3">
              <p className="text-sm text-red-600">{pwdError}</p>
            </div>
          )}
          <Input
            label="旧密码"
            type={showOldPwd ? 'text' : 'password'}
            value={oldPassword}
            onChange={(val) => setOldPassword(val as string)}
            suffixIcon={
              <span className="cursor-pointer" onClick={() => setShowOldPwd(!showOldPwd)}>
                {showOldPwd ? <BrowseOffIcon className="text-sm" /> : <BrowseIcon className="text-sm" />}
              </span>
            }
          />
          <Input
            label="新密码"
            type={showNewPwd ? 'text' : 'password'}
            value={newPassword}
            onChange={(val) => setNewPassword(val as string)}
            tips="密码长度至少8位"
            suffixIcon={
              <span className="cursor-pointer" onClick={() => setShowNewPwd(!showNewPwd)}>
                {showNewPwd ? <BrowseOffIcon className="text-sm" /> : <BrowseIcon className="text-sm" />}
              </span>
            }
          />
          <Input
            label="确认新密码"
            type="password"
            value={confirmPassword}
            onChange={(val) => setConfirmPassword(val as string)}
            status={confirmPassword.length > 0 && newPassword !== confirmPassword ? 'error' : undefined}
            tips={confirmPassword.length > 0 && newPassword !== confirmPassword ? '两次输入的密码不一致' : ''}
          />
        </div>
      </Dialog>

      {/* MFA 设置弹窗 */}
      <Dialog
        header="设置多因素认证 (MFA)"
        visible={mfaSetupOpen}
        onClose={() => setMfaSetupOpen(false)}
        width="560px"
        footer={
          <div className="flex justify-end gap-2 px-6 pb-4">
            <Button onClick={() => setMfaSetupOpen(false)}>取消</Button>
            {mfaSetupStep === 'scan' ? (
              <Button theme="primary" onClick={() => setMfaSetupStep('verify')}>
                下一步
              </Button>
            ) : (
              <Button
                theme="primary"
                disabled={mfaTotpCode.length !== 6}
                loading={mfaEnableMut.isPending}
                onClick={handleMfaEnableConfirm}
              >
                确认启用
              </Button>
            )}
          </div>
        }
      >
        <div className="flex flex-col gap-4 px-6 pt-2">
          {mfaSetupError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3">
              <p className="text-sm text-red-600">{mfaSetupError}</p>
            </div>
          )}

          {mfaSetupStep === 'scan' && mfaSetupData && (
            <>
              <p className="text-sm text-gray-600">
                使用 Google Authenticator、Microsoft Authenticator 或其他 TOTP 应用扫描下方二维码：
              </p>

              {/* 二维码 */}
              <div className="flex justify-center">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mfaSetupData.qr_code_url)}`}
                  alt="MFA QR Code"
                  width={200}
                  height={200}
                  className="rounded-lg border border-gray-200"
                />
              </div>

              {/* 密钥手动输入 */}
              <div>
                <p className="mb-1 text-xs text-gray-500">无法扫码？手动输入密钥：</p>
                <div className="flex items-center gap-2 rounded-md bg-gray-50 p-3">
                  <code className="flex-1 font-mono text-sm tracking-wider">
                    {showMfaSecret
                      ? mfaSetupData.secret
                      : mfaSetupData.secret.substring(0, 4) + '****' + mfaSetupData.secret.substring(mfaSetupData.secret.length - 4)
                    }
                  </code>
                  <Button
                    variant="text"
                    size="small"
                    icon={showMfaSecret ? <BrowseOffIcon /> : <BrowseIcon />}
                    onClick={() => setShowMfaSecret(!showMfaSecret)}
                  />
                  <Button
                    variant="text"
                    size="small"
                    icon={<CopyIcon />}
                    onClick={() => handleCopy(mfaSetupData.secret)}
                  />
                </div>
              </div>

              {/* 备份码 */}
              <div>
                <p className="mb-2 text-xs text-gray-500">
                  请保存以下备份码（用于无法获取验证码时的备用登录）：
                </p>
                <div className="grid grid-cols-2 gap-1 rounded-md bg-gray-50 p-3">
                  {mfaSetupData.backup_codes.map((code, i) => (
                    <code key={i} className="font-mono text-xs text-gray-700">{code}</code>
                  ))}
                </div>
                <Button
                  variant="text"
                  size="small"
                  className="mt-1"
                  icon={<CopyIcon />}
                  onClick={() => handleCopy(mfaSetupData.backup_codes.join('\n'))}
                >
                  复制全部备份码
                </Button>
              </div>
            </>
          )}

          {mfaSetupStep === 'verify' && (
            <>
              <p className="text-sm text-gray-600">
                请输入身份验证器应用中显示的 6 位验证码，以确认设置成功：
              </p>
              <Input
                label="验证码"
                placeholder="000000"
                value={mfaTotpCode}
                onChange={(val) => setMfaTotpCode((val as string).replace(/\D/g, '').slice(0, 6))}
                maxlength={6}
                align="center"
                className="text-center"
              />
              <p className="text-xs text-gray-400">
                验证码每 30 秒更新一次，请确保在有效期内输入
              </p>
            </>
          )}
        </div>
      </Dialog>

      {/* MFA 禁用确认弹窗 */}
      <Dialog
        header="禁用多因素认证 (MFA)"
        visible={mfaDisableOpen}
        onClose={() => setMfaDisableOpen(false)}
        width="440px"
        footer={
          <div className="flex justify-end gap-2 px-6 pb-4">
            <Button onClick={() => setMfaDisableOpen(false)}>取消</Button>
            <Button
              theme="danger"
              disabled={!mfaDisablePassword.trim()}
              loading={mfaDisableMut.isPending}
              onClick={handleMfaDisableConfirm}
            >
              确认禁用
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4 px-6 pt-2">
          {mfaDisableError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3">
              <p className="text-sm text-red-600">{mfaDisableError}</p>
            </div>
          )}
          <p className="text-sm text-gray-600">
            禁用 MFA 后，登录时将不再需要额外的验证码验证。请输入密码确认操作：
          </p>
          <Input
            label="密码确认"
            type={showDisablePwd ? 'text' : 'password'}
            value={mfaDisablePassword}
            onChange={(val) => setMfaDisablePassword(val as string)}
            suffixIcon={
              <span className="cursor-pointer" onClick={() => setShowDisablePwd(!showDisablePwd)}>
                {showDisablePwd ? <BrowseOffIcon className="text-sm" /> : <BrowseIcon className="text-sm" />}
              </span>
            }
          />
        </div>
      </Dialog>

      <LoadingOverlay open={changePwdMut.isPending || mfaSetupMut.isPending || mfaEnableMut.isPending || mfaDisableMut.isPending} />
    </div>
  );
};

export default PortalProfilePage;
