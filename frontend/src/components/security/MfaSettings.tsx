/**
 * MFA 多因素认证设置组件（独立组件）
 * 
 * 功能：
 * - 显示MFA当前状态
 * - 启用/禁用MFA
 * - TOTP扫码绑定
 * - 备份码管理
 * 
 * 所有功能均调用真实后端API，无模拟实现
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Button, Input, Tag, Dialog, MessagePlugin, Card, Steps, Divider, Alert, 
  Loading, Space, Tooltip 
} from 'tdesign-react';
import { 
  LockOnIcon, QrcodeIcon, CopyIcon, CheckCircleFilledIcon, 
  RefreshIcon, InfoCircleIcon 
} from 'tdesign-icons-react';
import request from '@/api/request';

// 类型定义
interface MfaStatus {
  enabled: boolean;
  method: string | null;
  backupCodesRemaining: number;
  lastVerifiedAt: string | null;
}

interface MfaSetupResult {
  secret: string;
  qrCodeUrl: string;
  backupCodes: string[];
  method: string;
}

interface MfaSettingsProps {
  /** 外部样式类 */
  className?: string;
  /** 状态变更回调 */
  onStatusChange?: (enabled: boolean) => void;
}

const MfaSettings: React.FC<MfaSettingsProps> = ({ className, onStatusChange }) => {
  // 状态
  const [mfaStatus, setMfaStatus] = useState<MfaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupStep, setSetupStep] = useState(0);
  const [setupResult, setSetupResult] = useState<MfaSetupResult | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [showDisableDialog, setShowDisableDialog] = useState(false);
  const [disableCode, setDisableCode] = useState('');
  const [isDisabling, setIsDisabling] = useState(false);

  // 获取MFA状态
  const fetchMfaStatus = useCallback(async () => {
    try {
      const res: any = await request.get('/auth/mfa/status');
      const data = res?.data || res;
      const status: MfaStatus = {
        enabled: data?.enabled ?? false,
        method: data?.method ?? null,
        backupCodesRemaining: data?.backup_codes_remaining ?? 0,
        lastVerifiedAt: data?.last_verified_at ?? null,
      };
      setMfaStatus(status);
      onStatusChange?.(status.enabled);
    } catch (error: any) {
      // API失败时显示错误状态，不使用模拟数据
      setMfaStatus({ 
        enabled: false, 
        method: null, 
        backupCodesRemaining: 0, 
        lastVerifiedAt: null 
      });
      MessagePlugin.error('获取MFA状态失败：' + (error?.message || '网络错误'));
    } finally {
      setLoading(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    fetchMfaStatus();
  }, [fetchMfaStatus]);

  // 开始设置MFA
  const handleStartSetup = async () => {
    setLoading(true);
    try {
      const res: any = await request.post('/auth/mfa/setup', {
        method: 'totp',
      });
      const data = res?.data || res;
      
      if (!data?.secret || !data?.qr_code_url) {
        throw new Error('服务器返回的MFA配置数据不完整');
      }

      const result: MfaSetupResult = {
        secret: data.secret,
        qrCodeUrl: data.qr_code_url,
        backupCodes: data.backup_codes || [],
        method: data.method || 'totp',
      };
      
      setSetupResult(result);
      setBackupCodes(result.backupCodes);
      setSetupStep(1);
    } catch (error: any) {
      MessagePlugin.error('初始化MFA失败：' + (error?.message || '请检查网络连接'));
    } finally {
      setLoading(false);
    }
  };

  // 验证TOTP码并启用MFA
  const handleVerifyAndEnable = async () => {
    if (verifyCode.length !== 6) {
      MessagePlugin.warning('请输入6位验证码');
      return;
    }
    
    setIsVerifying(true);
    try {
      await request.post('/auth/mfa/enable', {
        code: verifyCode,
      });
      
      // 更新状态
      await fetchMfaStatus();
      setSetupStep(3);
      MessagePlugin.success('MFA 已成功启用！');
    } catch (error: any) {
      const msg = error?.response?.data?.message || error?.message || '验证码错误';
      MessagePlugin.error('验证失败：' + msg);
    } finally {
      setIsVerifying(false);
    }
  };

  // 禁用MFA
  const handleDisableMfa = async () => {
    if (disableCode.length !== 6) {
      MessagePlugin.warning('请输入6位验证码以确认禁用');
      return;
    }
    
    setIsDisabling(true);
    try {
      await request.post('/auth/mfa/disable', {
        code: disableCode,
      });
      
      setShowDisableDialog(false);
      setDisableCode('');
      await fetchMfaStatus();
      setSetupStep(0);
      MessagePlugin.success('MFA 已禁用');
    } catch (error: any) {
      const msg = error?.response?.data?.message || error?.message || '验证码错误';
      MessagePlugin.error('禁用失败：' + msg);
    } finally {
      setIsDisabling(false);
    }
  };

  // 重新生成备份码
  const handleRegenerateBackupCodes = async () => {
    try {
      const res: any = await request.post('/auth/mfa/backup-codes/regenerate');
      const data = res?.data || res;
      
      if (data?.backup_codes) {
        setBackupCodes(data.backup_codes);
        setShowBackupCodes(true);
        await fetchMfaStatus();
        MessagePlugin.success('备份码已重新生成');
      } else {
        throw new Error('服务器未返回备份码');
      }
    } catch (error: any) {
      MessagePlugin.error('重新生成备份码失败：' + (error?.message || '请重试'));
    }
  };

  // 复制到剪贴板
  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      MessagePlugin.success('已复制到剪贴板');
    } catch {
      // 降级方案
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      MessagePlugin.success('已复制到剪贴板');
    }
  };

  // 加载状态
  if (loading && !mfaStatus) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-center py-12">
          <Loading size="medium" />
          <span className="ml-3 text-gray-500">加载MFA状态...</span>
        </div>
      </Card>
    );
  }

  return (
    <div className={className}>
      {/* 当前状态卡片 */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {mfaStatus?.enabled ? (
              <CheckCircleFilledIcon size="32px" className="text-green-500" />
            ) : (
              <LockOnIcon size="32px" className="text-gray-400" />
            )}
            <div>
              <h3 className="text-lg font-semibold">多因素认证 (MFA)</h3>
              <p className="text-gray-500 text-sm mt-1">
                {mfaStatus?.enabled 
                  ? `已启用 · ${mfaStatus.method === 'email' ? '邮件验证码' : 'TOTP认证器'} · 备份码剩余 ${mfaStatus.backupCodesRemaining} 个`
                  : '未启用 — 启用后可增强账户安全性'}
              </p>
            </div>
          </div>
          <Tag 
            theme={mfaStatus?.enabled ? 'success' : 'warning'} 
            variant="light"
            size="large"
          >
            {mfaStatus?.enabled ? '已启用' : '未启用'}
          </Tag>
        </div>
      </Card>

      {/* 未启用：设置流程 */}
      {!mfaStatus?.enabled && (
        <Card className="mt-4">
          <Steps current={setupStep} layout="vertical">
            <Steps.StepItem title="开始设置" content="初始化MFA配置" />
            <Steps.StepItem title="扫码绑定" content="使用认证器扫描二维码" />
            <Steps.StepItem title="验证确认" content="输入动态验证码" />
            <Steps.StepItem title="完成" content="保存备份码" />
          </Steps>

          <Divider />

          {/* 步骤0：开始 */}
          {setupStep === 0 && (
            <div className="text-center py-6">
              <LockOnIcon size="48px" className="text-blue-500 mb-4" />
              <h3 className="text-xl font-semibold mb-2">启用多因素认证</h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                启用MFA后，每次登录除了密码外还需要输入动态验证码，
                有效防止账户被盗用。支持 Google Authenticator、Microsoft Authenticator 等认证器应用。
              </p>
              <Button 
                theme="primary" 
                size="large" 
                onClick={handleStartSetup} 
                loading={loading}
              >
                开始设置
              </Button>
            </div>
          )}

          {/* 步骤1：扫码绑定 */}
          {setupStep === 1 && setupResult && (
            <div className="space-y-6">
              <Alert 
                theme="info" 
                message="使用认证器App扫描下方二维码，或手动输入密钥" 
                className="mb-4"
              />

              <div className="flex flex-col items-center gap-6">
                {/* QR码 */}
                <div className="p-4 bg-white rounded-xl border-2 border-gray-200 shadow-sm">
                  <img
                    src={"/api/v1/auth/mfa/qr-code?uri=" + encodeURIComponent(setupResult.qrCodeUrl)}
                    alt="MFA QR Code"
                    width={200}
                    height={200}
                    onError={(e) => {
                      MessagePlugin.error('QR码加载失败，请使用手动密钥绑定');
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>

                {/* 手动密钥 */}
                <div className="w-full max-w-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm text-gray-500">手动输入密钥：</span>
                    <Tooltip content={'在认证器App中选择"手动输入密钥"选项'}>
                      <InfoCircleIcon size="16px" className="text-gray-400" />
                    </Tooltip>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input 
                      value={setupResult.secret} 
                      readonly 
                      className="font-mono text-center tracking-wider" 
                    />
                    <Button 
                      variant="outline" 
                      icon={<CopyIcon />} 
                      onClick={() => handleCopy(setupResult.secret)}
                    >
                      复制
                    </Button>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    算法: SHA1 · 位数: 6 · 周期: 30秒
                  </p>
                </div>
              </div>

              {/* 验证码输入 */}
              <div className="max-w-sm mx-auto">
                <p className="text-sm font-medium mb-2">输入认证器显示的6位验证码：</p>
                <div className="flex items-center gap-2">
                  <Input
                    value={verifyCode}
                    onChange={(val) => setVerifyCode(val.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxlength={6}
                    className="text-center text-2xl tracking-[0.5em] font-mono"
                  />
                  <Button
                    theme="primary"
                    loading={isVerifying}
                    onClick={handleVerifyAndEnable}
                    disabled={verifyCode.length !== 6}
                  >
                    验证并启用
                  </Button>
                </div>
              </div>

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setSetupStep(0)}>上一步</Button>
                <Button 
                  variant="outline" 
                  onClick={() => { setBackupCodes(setupResult.backupCodes); setSetupStep(2); }}
                >
                  跳过验证查看备份码
                </Button>
              </div>
            </div>
          )}

          {/* 步骤2：备份码 */}
          {setupStep === 2 && (
            <div className="space-y-4">
              <Alert 
                theme="warning" 
                message="请妥善保管以下备份码。当您无法使用认证器时，可以使用备份码登录。每个备份码只能使用一次。" 
              />

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

              <Space>
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
              </Space>

              <div className="flex justify-between mt-4">
                <Button variant="outline" onClick={() => setSetupStep(1)}>上一步</Button>
                <Button theme="primary" onClick={() => setSetupStep(3)}>确认保存</Button>
              </div>
            </div>
          )}

          {/* 步骤3：完成 */}
          {setupStep === 3 && (
            <div className="text-center py-8">
              <CheckCircleFilledIcon size="64px" className="text-green-500 mb-4" />
              <h3 className="text-xl font-semibold mb-2">MFA 设置完成！</h3>
              <p className="text-gray-500 mb-6">
                您的账户已启用多因素认证，下次登录时需要输入动态验证码
              </p>
              <Space>
                <Button theme="primary" onClick={() => setShowBackupCodes(true)}>
                  查看备份码
                </Button>
                <Button variant="outline" onClick={() => setSetupStep(0)}>
                  返回
                </Button>
              </Space>
            </div>
          )}
        </Card>
      )}

      {/* 已启用：管理面板 */}
      {mfaStatus?.enabled && (
        <Card className="mt-4">
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
              <CheckCircleFilledIcon size="24px" className="text-green-500" />
              <div>
                <p className="font-medium text-green-800">MFA 保护已激活</p>
                <p className="text-sm text-green-600">
                  每次登录将需要{mfaStatus.method === 'email' ? '邮箱验证码' : '认证器动态验证码'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">认证方式</span>
                <p className="font-medium">{mfaStatus.method === 'email' ? '邮件验证码' : 'TOTP 认证器'}</p>
              </div>
              <div>
                <span className="text-gray-500">备份码剩余</span>
                <p className="font-medium">{mfaStatus.backupCodesRemaining} 个</p>
              </div>
              {mfaStatus.lastVerifiedAt && (
                <div className="col-span-2">
                  <span className="text-gray-500">最后验证时间</span>
                  <p className="font-medium">{new Date(mfaStatus.lastVerifiedAt).toLocaleString('zh-CN')}</p>
                </div>
              )}
            </div>

            <Divider />

            <Space>
              <Button variant="outline" onClick={() => setShowBackupCodes(true)}>
                查看备份码
              </Button>
              <Button variant="outline" onClick={handleRegenerateBackupCodes}>
                重新生成备份码
              </Button>
              <Button theme="danger" variant="outline" onClick={() => setShowDisableDialog(true)}>
                禁用 MFA
              </Button>
            </Space>
          </div>
        </Card>
      )}

      {/* 备份码弹窗 */}
      <Dialog
        header="备份码"
        visible={showBackupCodes}
        onClose={() => setShowBackupCodes(false)}
        footer={<Button onClick={() => setShowBackupCodes(false)}>关闭</Button>}
        width="480px"
      >
        <Alert 
          theme="warning" 
          message="请妥善保管以下备份码。每个备份码只能使用一次，用完即失效。" 
          className="mb-4"
        />
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
        <div className="mt-4 text-center">
          <Button 
            variant="outline" 
            icon={<CopyIcon />} 
            onClick={() => handleCopy(backupCodes.join('\n'))}
          >
            复制全部备份码
          </Button>
        </div>
      </Dialog>

      {/* 禁用MFA确认弹窗 */}
      <Dialog
        header="禁用多因素认证"
        visible={showDisableDialog}
        onClose={() => { setShowDisableDialog(false); setDisableCode(''); }}
        footer={
          <Space>
            <Button variant="outline" onClick={() => { setShowDisableDialog(false); setDisableCode(''); }}>
              取消
            </Button>
            <Button 
              theme="danger" 
              loading={isDisabling} 
              onClick={handleDisableMfa}
              disabled={disableCode.length !== 6}
            >
              确认禁用
            </Button>
          </Space>
        }
        width="400px"
      >
        <Alert 
          theme="error" 
          message="禁用MFA后，您的账户安全性将降低。请输入当前验证码以确认操作。" 
          className="mb-4"
        />
        <div>
          <p className="text-sm text-gray-600 mb-2">请输入认证器当前显示的6位验证码：</p>
          <Input
            value={disableCode}
            onChange={(val) => setDisableCode(val.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            maxlength={6}
            className="text-center text-xl tracking-[0.5em] font-mono"
          />
        </div>
      </Dialog>
    </div>
  );
};

export default MfaSettings;
