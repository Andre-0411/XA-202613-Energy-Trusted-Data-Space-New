/**
 * MFA 多因素认证设置页面
 * 支持 TOTP 扫码绑定、备份码管理
 */
import React, { useState, useEffect } from 'react';
import { Button, Input, Tag, Dialog, MessagePlugin, Card, Steps, Divider, Alert } from 'tdesign-react';
import { LockOnIcon, QrcodeIcon, CopyIcon, CheckCircleFilledIcon, RefreshIcon } from 'tdesign-icons-react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';

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
    { label: '安全设置', href: '/dashboard/security' },
    { label: 'MFA 设置' },
  ];

  // 状态
  const [mfaStatus, setMfaStatus] = useState<MfaStatus>({
    enabled: false,
    method: null,
    backupCodesRemaining: 0,
    lastVerifiedAt: null,
  });
  const [setupStep, setSetupStep] = useState(0);
  const [setupResult, setSetupResult] = useState<MfaSetupResult | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  // 模拟获取 MFA 状态
  useEffect(() => {
    setMfaStatus({
      enabled: false,
      method: null,
      backupCodesRemaining: 0,
      lastVerifiedAt: null,
    });
  }, []);

  // 开始设置 MFA
  const handleStartSetup = () => {
    // 模拟 API 调用
    const mockResult: MfaSetupResult = {
      secret: 'JBSWY3DPEHPK3PXP',
      qrCodeUrl: 'otpauth://totp/EnergyDataSpace:admin?secret=JBSWY3DPEHPK3PXP&issuer=EnergyDataSpace',
      backupCodes: [
        'A1B2-C3D4', 'E5F6-G7H8', 'I9J0-K1L2', 'M3N4-O5P6',
        'Q7R8-S9T0', 'U1V2-W3X4', 'Y5Z6-A7B8', 'C9D0-E1F2',
      ],
      method: 'totp',
    };
    setSetupResult(mockResult);
    setBackupCodes(mockResult.backupCodes);
    setSetupStep(1);
  };

  // 验证 TOTP 码
  const handleVerify = () => {
    if (verifyCode.length !== 6) {
      MessagePlugin.warning('请输入6位验证码');
      return;
    }
    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
      setMfaStatus({
        enabled: true,
        method: 'totp',
        backupCodesRemaining: 8,
        lastVerifiedAt: new Date().toISOString(),
      });
      setSetupStep(3);
      MessagePlugin.success('MFA 绑定成功！');
    }, 1500);
  };

  // 复制到剪贴板
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      MessagePlugin.success('已复制到剪贴板');
    });
  };

  // 重新生成备份码
  const handleRegenerateBackupCodes = () => {
    const newCodes = [
      'X1Y2-Z3A4', 'B5C6-D7E8', 'F9G0-H1I2', 'J3K4-L5M6',
      'N7O8-P9Q0', 'R1S2-T3U4', 'V5W6-X7Y8', 'Z9A0-B1C2',
    ];
    setBackupCodes(newCodes);
    setShowBackupCodes(true);
    MessagePlugin.success('备份码已重新生成');
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
                {mfaStatus.enabled
                  ? `已启用 (${mfaStatus.method?.toUpperCase()})，备份码剩余 ${mfaStatus.backupCodesRemaining} 个`
                  : '未启用'}
              </p>
            </div>
            <Tag theme={mfaStatus.enabled ? 'success' : 'warning'} variant="light">
              {mfaStatus.enabled ? '已启用' : '未启用'}
            </Tag>
          </div>
        </Card>

        {/* 设置步骤 */}
        {!mfaStatus.enabled && (
          <Card>
            <Steps current={setupStep} layout="vertical">
              <Steps.StepItem title="选择认证方式" content="使用 TOTP 认证器应用" />
              <Steps.StepItem title="扫码绑定" content="使用手机扫描二维码" />
              <Steps.StepItem title="验证绑定" content="输入6位验证码确认" />
              <Steps.StepItem title="保存备份码" content="妥善保管备份码" />
            </Steps>

            <Divider />

            {/* 步骤0：开始 */}
            {setupStep === 0 && (
              <div className="text-center py-8">
                <LockOnIcon size="48px" className="text-blue-500 mb-4" />
                <h3 className="text-xl font-semibold mb-2">启用多因素认证</h3>
                <p className="text-gray-500 mb-6">
                  使用 Google Authenticator、Microsoft Authenticator 或其他 TOTP 应用增强账户安全
                </p>
                <Button theme="primary" size="large" onClick={handleStartSetup}>
                  开始设置
                </Button>
              </div>
            )}

            {/* 步骤1：扫码 */}
            {setupStep === 1 && setupResult && (
              <div className="space-y-6">
                <Alert theme="info" message="请使用手机认证器应用扫描下方二维码" />

                {/* QR 码区域 */}
                <div className="flex flex-col items-center gap-6">
                  <div className="w-64 h-64 bg-gray-100 rounded-xl flex items-center justify-center border-2 border-dashed border-gray-300">
                    <div className="text-center">
                      <QrcodeIcon size="64px" className="text-blue-500 mb-2" />
                      <p className="text-sm text-gray-500">TOTP 二维码</p>
                      <p className="text-xs text-gray-400 mt-1">(演示模式)</p>
                    </div>
                  </div>

                  {/* 手动输入密钥 */}
                  <div className="w-full max-w-md">
                    <p className="text-sm text-gray-500 mb-2">无法扫码？手动输入密钥：</p>
                    <div className="flex items-center gap-2">
                      <Input
                        value={setupResult.secret}
                        readonly
                        className="font-mono"
                      />
                      <Button
                        variant="outline"
                        icon={<CopyIcon />}
                        onClick={() => handleCopy(setupResult.secret)}
                      >
                        复制
                      </Button>
                    </div>
                  </div>

                  {/* 验证码输入 */}
                  <div className="w-full max-w-md">
                    <p className="text-sm font-medium mb-2">输入认证器显示的6位验证码：</p>
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
                        onClick={handleVerify}
                        disabled={verifyCode.length !== 6}
                      >
                        验证
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between mt-6">
                  <Button variant="outline" onClick={() => setSetupStep(0)}>上一步</Button>
                  <Button theme="primary" onClick={() => setSetupStep(2)}>跳过验证查看备份码</Button>
                </div>
              </div>
            )}

            {/* 步骤2：备份码 */}
            {setupStep === 2 && (
              <div className="space-y-4">
                <Alert theme="warning" message="请妥善保管备份码，每个备份码只能使用一次" />

                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, i) => (
                    <div key={i} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                      <code className="font-mono text-sm">{code}</code>
                      <Button
                        variant="text"
                        size="small"
                        icon={<CopyIcon />}
                        onClick={() => handleCopy(code)}
                      />
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 mt-4">
                  <Button
                    variant="outline"
                    icon={<CopyIcon />}
                    onClick={() => handleCopy(backupCodes.join('\n'))}
                  >
                    复制全部
                  </Button>
                  <Button
                    variant="outline"
                    icon={<RefreshIcon />}
                    onClick={handleRegenerateBackupCodes}
                  >
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
                <p className="text-gray-500 mb-6">
                  您的账户已启用多因素认证，下次登录需要输入验证码
                </p>
                <Button theme="primary" onClick={() => window.history.back()}>
                  返回
                </Button>
              </div>
            )}
          </Card>
        )}

        {/* 已启用状态 */}
        {mfaStatus.enabled && (
          <Card>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <CheckCircleFilledIcon size="24px" className="text-green-500" />
                <div>
                  <h3 className="font-semibold">MFA 已启用</h3>
                  <p className="text-sm text-gray-500">
                    认证方式：TOTP | 备份码剩余：{mfaStatus.backupCodesRemaining} 个
                  </p>
                </div>
              </div>

              <Divider />

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowBackupCodes(true)}>
                  查看备份码
                </Button>
                <Button variant="outline" onClick={handleRegenerateBackupCodes}>
                  重新生成备份码
                </Button>
                <Button theme="danger" variant="outline" onClick={() => {
                  setMfaStatus({ enabled: false, method: null, backupCodesRemaining: 0, lastVerifiedAt: null });
                  setSetupStep(0);
                  MessagePlugin.success('MFA 已禁用');
                }}>
                  禁用 MFA
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* 备份码弹窗 */}
        <Dialog
          header="备份码"
          visible={showBackupCodes}
          onClose={() => setShowBackupCodes(false)}
          footer={
            <Button onClick={() => setShowBackupCodes(false)}>关闭</Button>
          }
        >
          <Alert theme="warning" message="每个备份码只能使用一次，请妥善保管" className="mb-4" />
          <div className="grid grid-cols-2 gap-2">
            {backupCodes.map((code, i) => (
              <code key={i} className="font-mono text-sm bg-gray-50 px-3 py-2 rounded text-center">
                {code}
              </code>
            ))}
          </div>
        </Dialog>
      </div>
    </PageContainer>
  );
};

export default MfaSetupPage;
