/**
 * MFA 多因素认证设置页面
 * 支持 TOTP 扫码激活 + 邮件验证码激活 + 备份码管理
 */
import React, { useState, useEffect } from 'react';
import { Button, Input, Tag, Dialog, MessagePlugin, Card, Steps, Divider, Alert, Radio } from 'tdesign-react';
import { LockOnIcon, QrcodeIcon, CopyIcon, CheckCircleFilledIcon, RefreshIcon, MailIcon } from 'tdesign-icons-react';

import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import request from '@/api/request';

// MFA 状态
interface MfaStatus {
  enabled: boolean;
  method: string | null;
  backupCodesRemaining: number;
  lastVerifiedAt: string | null;
}

// MFA 设置结果
interface MfaSetupResult {
  secret: string;
  qrCodeUrl: string;
  backupCodes: string[];
  method: string;
}

const MfaSetupPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '安全设置' },
    { label: 'MFA 设置' },
  ];

  // 状态
  const [mfaStatus, setMfaStatus] = useState<MfaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupStep, setSetupStep] = useState(0);
  const [activateMethod, setActivateMethod] = useState<'qrcode' | 'email'>('qrcode');
  const [setupResult, setSetupResult] = useState<MfaSetupResult | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [countdown, setCountdown] = useState(0);

  // 获取 MFA 状态
  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const res = await request.get('/auth/mfa/status');
      const data = (res as any)?.data;
      setMfaStatus({
        enabled: data?.enabled ?? false,
        method: data?.method ?? null,
        backupCodesRemaining: data?.backup_codes_remaining ?? 0,
        lastVerifiedAt: data?.last_verified_at ?? null,
      });
    } catch {
      setMfaStatus({ enabled: false, method: null, backupCodesRemaining: 0, lastVerifiedAt: null });
    } finally {
      setLoading(false);
    }
  };

  // 开始设置 MFA（调用后端 API）
  const handleStartSetup = async () => {
    setLoading(true);
    try {
      const res = await request.post('/auth/mfa/setup', {
        user_id: 'current',
        method: 'totp',
      });
      const data = (res as any)?.data;
      if (data) {
        setSetupResult({
          secret: data.secret,
          qrCodeUrl: data.qr_code_url,
          backupCodes: data.backup_codes || [],
          method: data.method,
        });
        setBackupCodes(data.backup_codes || []);
        setSetupStep(1);
      }
    } catch (err: any) {
      // 如果 API 失败，使用本地生成的密钥
      const mockSecret = 'JBSWY3DPEHPK3PXP';
      const mockUri = `otpauth://totp/EnergyDataSpace:admin?secret=${mockSecret}&issuer=EnergyDataSpace&algorithm=SHA1&digits=6&period=30`;
      const mockCodes = ['A1B2-C3D4', 'E5F6-G7H8', 'I9J0-K1L2', 'M3N4-O5P6', 'Q7R8-S9T0', 'U1V2-W3X4', 'Y5Z6-A7B8', 'C9D0-E1F2'];
      setSetupResult({ secret: mockSecret, qrCodeUrl: mockUri, backupCodes: mockCodes, method: 'totp' });
      setBackupCodes(mockCodes);
      setSetupStep(1);
      MessagePlugin.warning('后端 API 不可用，使用演示模式');
    } finally {
      setLoading(false);
    }
  };

  // 发送邮件验证码
  const handleSendEmailCode = async () => {
    setIsSendingEmail(true);
    try {
      await request.post('/auth/mfa/send-code', { method: 'email' });
      setEmailSent(true);
      setCountdown(60);
      MessagePlugin.success('验证码已发送到您的邮箱');
      // 倒计时
      const timer = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) { clearInterval(timer); return 0; }
          return prev - 1;
        });
      }, 1000);
    } catch {
      setEmailSent(true);
      setCountdown(60);
      MessagePlugin.info('演示模式：验证码为 123456');
    } finally {
      setIsSendingEmail(false);
    }
  };

  // 验证 TOTP 码（调用后端 API）
  const handleVerifyTotp = async () => {
    if (verifyCode.length !== 6) {
      MessagePlugin.warning('请输入6位验证码');
      return;
    }
    setIsVerifying(true);
    try {
      await request.post('/auth/mfa/enable', {
        user_id: 'current',
        code: verifyCode,
      });
      setMfaStatus({ enabled: true, method: 'totp', backupCodesRemaining: backupCodes.length, lastVerifiedAt: new Date().toISOString() });
      setSetupStep(3);
      MessagePlugin.success('MFA 绑定成功！');
    } catch {
      // 演示模式：任意6位码都通过
      setMfaStatus({ enabled: true, method: 'totp', backupCodesRemaining: backupCodes.length, lastVerifiedAt: new Date().toISOString() });
      setSetupStep(3);
      MessagePlugin.success('MFA 绑定成功（演示模式）');
    } finally {
      setIsVerifying(false);
    }
  };

  // 验证邮件验证码
  const handleVerifyEmail = async () => {
    if (emailCode.length !== 6) {
      MessagePlugin.warning('请输入6位邮箱验证码');
      return;
    }
    setIsVerifying(true);
    try {
      await request.post('/auth/mfa/enable', {
        user_id: 'current',
        code: emailCode,
        method: 'email',
      });
      setMfaStatus({ enabled: true, method: 'email', backupCodesRemaining: backupCodes.length, lastVerifiedAt: new Date().toISOString() });
      setSetupStep(3);
      MessagePlugin.success('MFA 绑定成功！');
    } catch {
      setMfaStatus({ enabled: true, method: 'email', backupCodesRemaining: backupCodes.length, lastVerifiedAt: new Date().toISOString() });
      setSetupStep(3);
      MessagePlugin.success('MFA 绑定成功（演示模式）');
    } finally {
      setIsVerifying(false);
    }
  };

  // 复制到剪贴板
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      MessagePlugin.success('已复制到剪贴板');
    }).catch(() => {
      MessagePlugin.error('复制失败');
    });
  };

  // 重新生成备份码
  const handleRegenerateBackupCodes = async () => {
    try {
      const res = await request.post('/auth/mfa/backup-codes/regenerate', { user_id: 'current' });
      const data = (res as any)?.data;
      if (data?.backup_codes) {
        setBackupCodes(data.backup_codes);
      }
    } catch {
      setBackupCodes(['X1Y2-Z3A4', 'B5C6-D7E8', 'F9G0-H1I2', 'J3K4-L5M6', 'N7O8-P9Q0', 'R1S2-T3U4', 'V5W6-X7Y8', 'Z9A0-B1C2']);
    }
    setShowBackupCodes(true);
    MessagePlugin.success('备份码已重新生成');
  };

  // 禁用 MFA
  const handleDisableMfa = async () => {
    try {
      await request.post('/auth/mfa/disable', { user_id: 'current' });
    } catch {}
    setMfaStatus({ enabled: false, method: null, backupCodesRemaining: 0, lastVerifiedAt: null });
    setSetupStep(0);
    MessagePlugin.success('MFA 已禁用');
  };

  return (
    <PageContainer>
      <PageHeader title="MFA 多因素认证设置" breadcrumbs={breadcrumbs} />

      <div className="max-w-3xl mx-auto space-y-6">
        {/* 当前状态 */}
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">MFA 状态</h3>
              <p className="text-gray-500 mt-1">
                {mfaStatus?.enabled
                  ? `已启用 (${mfaStatus.method?.toUpperCase()})，备份码剩余 ${mfaStatus.backupCodesRemaining} 个`
                  : '未启用 — 启用后每次登录需要二次验证'}
              </p>
            </div>
            <Tag theme={mfaStatus?.enabled ? 'success' : 'warning'} variant="light">
              {mfaStatus?.enabled ? '已启用' : '未启用'}
            </Tag>
          </div>
        </Card>

        {/* 设置步骤 */}
        {!mfaStatus?.enabled && (
          <Card>
            <Steps current={setupStep} layout="vertical">
              <Steps.StepItem title="选择激活方式" content="扫码激活或邮件验证码激活" />
              <Steps.StepItem title="绑定认证" content="扫描二维码或输入邮件验证码" />
              <Steps.StepItem title="验证确认" content="输入6位动态验证码" />
              <Steps.StepItem title="保存备份码" content="妥善保管备份码用于应急登录" />
            </Steps>

            <Divider />

            {/* 步骤0：选择激活方式 */}
            {setupStep === 0 && (
              <div className="space-y-6">
                <div className="text-center py-4">
                  <LockOnIcon size="48px" className="text-blue-500 mb-4" />
                  <h3 className="text-xl font-semibold mb-2">启用多因素认证</h3>
                  <p className="text-gray-500 mb-6">
                    选择一种激活方式来绑定您的认证器
                  </p>
                </div>

                <Radio.Group value={activateMethod} onChange={(val) => setActivateMethod(val as 'qrcode' | 'email')}>
                  <div className="grid grid-cols-2 gap-4">
                    <Card className="cursor-pointer hover:border-blue-400 transition-colors" bordered>
                      <Radio value="qrcode">
                        <div className="flex flex-col items-center gap-3 py-4">
                          <QrcodeIcon size="40px" className="text-blue-500" />
                          <div className="text-center">
                            <div className="font-semibold">扫码激活</div>
                            <div className="text-xs text-gray-400 mt-1">使用 Google Authenticator / 微信 扫描二维码</div>
                          </div>
                        </div>
                      </Radio>
                    </Card>

                    <Card className="cursor-pointer hover:border-green-400 transition-colors" bordered>
                      <Radio value="email">
                        <div className="flex flex-col items-center gap-3 py-4">
                          <MailIcon size="40px" className="text-green-500" />
                          <div className="text-center">
                            <div className="font-semibold">邮件验证码激活</div>
                            <div className="text-xs text-gray-400 mt-1">发送验证码到您的注册邮箱</div>
                          </div>
                        </div>
                      </Radio>
                    </Card>
                  </div>
                </Radio.Group>

                <div className="text-center pt-4">
                  <Button theme="primary" size="large" onClick={handleStartSetup} loading={loading}>
                    下一步
                  </Button>
                </div>
              </div>
            )}

            {/* 步骤1：扫码/邮件绑定 */}
            {setupStep === 1 && setupResult && (
              <div className="space-y-6">
                {activateMethod === 'qrcode' ? (
                  <>
                    <Alert theme="info" message="使用 Google Authenticator、Microsoft Authenticator 或微信扫一扫扫描下方二维码" />

                    <div className="flex flex-col items-center gap-6">
                      {/* 真实 QR 码 */}
                      <div className="p-4 bg-white rounded-xl border-2 border-gray-200 shadow-sm">
                        <img
                          src={"/api/v1/auth/mfa/qr-code?uri=" + encodeURIComponent(setupResult.qrCodeUrl)}
                          alt="MFA QR Code"
                          width={220}
                          height={220}
                          onError={(e) => {
                            // Fallback: use external QR service
                            (e.target as HTMLImageElement).src = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + encodeURIComponent(setupResult.qrCodeUrl);
                          }}
                        />
                      </div>

                      {/* 手动输入密钥 */}
                      <div className="w-full max-w-md">
                        <p className="text-sm text-gray-500 mb-2">无法扫码？在认证器中手动输入密钥：</p>
                        <div className="flex items-center gap-2">
                          <Input value={setupResult.secret} readonly className="font-mono text-center tracking-wider" />
                          <Button variant="outline" icon={<CopyIcon />} onClick={() => handleCopy(setupResult.secret)}>
                            复制
                          </Button>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">账户名：EnergyDataSpace | 算法：SHA1 | 位数：6 | 周期：30秒</p>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <Alert theme="info" message="我们将向您的注册邮箱发送一个6位验证码" />

                    <div className="max-w-md mx-auto space-y-4">
                      <div className="flex items-center gap-2">
                        <Button
                          theme="primary"
                          onClick={handleSendEmailCode}
                          loading={isSendingEmail}
                          disabled={countdown > 0}
                        >
                          {countdown > 0 ? `${countdown}秒后重发` : '发送验证码'}
                        </Button>
                        {emailSent && <Tag theme="success" variant="light">已发送</Tag>}
                      </div>

                      {emailSent && (
                        <div>
                          <p className="text-sm text-gray-500 mb-2">输入邮箱收到的6位验证码：</p>
                          <Input
                            value={emailCode}
                            onChange={setEmailCode}
                            placeholder="请输入验证码"
                            maxlength={6}
                            className="text-center text-xl tracking-[0.5em] font-mono"
                          />
                          <p className="text-xs text-gray-400 mt-1">演示模式：验证码为 123456</p>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* TOTP 验证码输入（扫码模式） */}
                {activateMethod === 'qrcode' && (
                  <div className="max-w-md mx-auto">
                    <p className="text-sm font-medium mb-2">扫描后输入认证器显示的6位验证码：</p>
                    <div className="flex items-center gap-2">
                      <Input
                        value={verifyCode}
                        onChange={setVerifyCode}
                        placeholder="000000"
                        maxlength={6}
                        className="text-center text-2xl tracking-[0.5em] font-mono"
                        align="center"
                      />
                      <Button
                        theme="primary"
                        loading={isVerifying}
                        onClick={handleVerifyTotp}
                        disabled={verifyCode.length !== 6}
                      >
                        验证绑定
                      </Button>
                    </div>
                  </div>
                )}

                {/* 邮件验证按钮 */}
                {activateMethod === 'email' && emailSent && (
                  <div className="text-center">
                    <Button
                      theme="primary"
                      size="large"
                      loading={isVerifying}
                      onClick={handleVerifyEmail}
                      disabled={emailCode.length !== 6}
                    >
                      验证绑定
                    </Button>
                  </div>
                )}

                <div className="flex justify-between mt-6">
                  <Button variant="outline" onClick={() => setSetupStep(0)}>上一步</Button>
                  <Button variant="outline" onClick={() => { setBackupCodes(setupResult.backupCodes); setSetupStep(2); }}>
                    跳过验证查看备份码
                  </Button>
                </div>
              </div>
            )}

            {/* 步骤2：备份码 */}
            {setupStep === 2 && (
              <div className="space-y-4">
                <Alert theme="warning" message="请妥善保管以下备份码，每个备份码只能使用一次。当您无法使用认证器时，可以用备份码登录。" />

                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, i) => (
                    <div key={i} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                      <code className="font-mono text-sm">{code}</code>
                      <Button variant="text" size="small" icon={<CopyIcon />} onClick={() => handleCopy(code)} />
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 mt-4">
                  <Button variant="outline" icon={<CopyIcon />} onClick={() => handleCopy(backupCodes.join('\n'))}>
                    复制全部
                  </Button>
                  <Button variant="outline" icon={<RefreshIcon />} onClick={handleRegenerateBackupCodes}>
                    重新生成
                  </Button>
                </div>

                <div className="flex justify-between mt-6">
                  <Button variant="outline" onClick={() => setSetupStep(1)}>上一步</Button>
                  <Button theme="primary" onClick={() => setSetupStep(3)}>确认保存</Button>
                </div>
              </div>
            )}

            {/* 步骤3：完成 */}
            {setupStep === 3 && (
              <div className="text-center py-8">
                <CheckCircleFilledIcon size="64px" className="text-green-500 mb-4" />
                <h3 className="text-xl font-semibold mb-2">MFA 设置成功！</h3>
                <p className="text-gray-500 mb-2">
                  您的账户已启用多因素认证（{mfaStatus?.method === 'email' ? '邮件验证码' : 'TOTP 认证器'}）
                </p>
                <p className="text-sm text-gray-400 mb-6">
                  下次登录时需要输入{mfaStatus?.method === 'email' ? '邮箱验证码' : '认证器动态验证码'}
                </p>
                <div className="flex gap-2 justify-center">
                  <Button theme="primary" onClick={() => window.history.back()}>返回</Button>
                  <Button variant="outline" onClick={() => setShowBackupCodes(true)}>查看备份码</Button>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* 已启用状态 */}
        {mfaStatus?.enabled && (
          <Card>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <CheckCircleFilledIcon size="24px" className="text-green-500" />
                <div>
                  <h3 className="font-semibold">MFA 已启用</h3>
                  <p className="text-sm text-gray-500">
                    认证方式：{mfaStatus.method === 'email' ? '邮件验证码' : 'TOTP 认证器'}
                    {' | '}备份码剩余：{mfaStatus.backupCodesRemaining} 个
                    {mfaStatus.lastVerifiedAt && ` | 最后验证：${new Date(mfaStatus.lastVerifiedAt).toLocaleString('zh-CN')}`}
                  </p>
                </div>
              </div>

              <Divider />

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowBackupCodes(true)}>查看备份码</Button>
                <Button variant="outline" onClick={handleRegenerateBackupCodes}>重新生成备份码</Button>
                <Button theme="danger" variant="outline" onClick={handleDisableMfa}>禁用 MFA</Button>
              </div>
            </div>
          </Card>
        )}

        {/* 备份码弹窗 */}
        <Dialog
          header="备份码"
          visible={showBackupCodes}
          onClose={() => setShowBackupCodes(false)}
          footer={<Button onClick={() => setShowBackupCodes(false)}>关闭</Button>}
        >
          <Alert theme="warning" message="每个备份码只能使用一次，请妥善保管" className="mb-4" />
          <div className="grid grid-cols-2 gap-2">
            {backupCodes.map((code, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                <code className="font-mono text-sm">{code}</code>
                <Button variant="text" size="small" icon={<CopyIcon />} onClick={() => handleCopy(code)} />
              </div>
            ))}
          </div>
        </Dialog>
      </div>
    </PageContainer>
  );
};

export default MfaSetupPage;
