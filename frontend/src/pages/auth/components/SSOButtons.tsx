/**
 * SSOButtons - 登录方式切换按钮组
 * 支持：密码登录 / DID登录 / 证书登录
 */
import React from 'react';
import { Input, Checkbox, Button, Loading } from 'tdesign-react';
import {
  BrowseIcon, BrowseOffIcon, UserIcon, LockOnIcon,
  FingerprintIcon, CertificateIcon, KeyIcon,
} from 'tdesign-icons-react';

/* ===== 类型 ===== */
export type LoginType = 'password' | 'did' | 'certificate';

/* ===== Props ===== */
interface SSOButtonsProps {
  loginType: LoginType;
  onSwitchType: (type: LoginType) => void;
  /* 密码登录 */
  username: string;
  onUsernameChange: (val: string) => void;
  password: string;
  onPasswordChange: (val: string) => void;
  showPassword: boolean;
  onTogglePassword: () => void;
  rememberMe: boolean;
  onRememberMeChange: (val: boolean) => void;
  /* DID 登录 */
  did: string;
  onDidChange: (val: string) => void;
  didSignature: string;
  onDidSignatureChange: (val: string) => void;
  didChallenge: string;
  onDidChallengeChange: (val: string) => void;
  /* 证书登录 */
  certificate: string;
  onCertificateChange: (val: string) => void;
  certSignature: string;
  onCertSignatureChange: (val: string) => void;
  /* 提交与事件 */
  onSubmit: () => void;
  onKeyDown: (val: string, ctx?: { e: React.KeyboardEvent }) => void;
  /* 加载状态 */
  isPending: boolean;
  passwordPending: boolean;
  didPending: boolean;
  certPending: boolean;
  /* 锁定提示 */
  lockoutMessage: string | null;
  lockoutRemaining: number;
}

/* ===== 按钮颜色配置 ===== */
const BTN_COLORS: Record<LoginType, string> = {
  password: '#0052d9',
  did: '#00bcd4',
  certificate: '#9c27b0',
};

/* ===== 输入框通用样式 ===== */
const INPUT_CLASSES = 'login-dark-input';

/* ============================================================
 * SSOButtons 主组件
 * ============================================================ */
const SSOButtons: React.FC<SSOButtonsProps> = ({
  loginType,
  onSwitchType,
  username,
  onUsernameChange,
  password,
  onPasswordChange,
  showPassword,
  onTogglePassword,
  rememberMe,
  onRememberMeChange,
  did,
  onDidChange,
  didSignature,
  onDidSignatureChange,
  didChallenge,
  onDidChallengeChange,
  certificate,
  onCertificateChange,
  certSignature,
  onCertSignatureChange,
  onSubmit,
  onKeyDown,
  isPending,
  passwordPending,
  didPending,
  certPending,
  lockoutMessage,
  lockoutRemaining,
}) => {
  const loginMethods: { key: LoginType; icon: React.ReactNode; label: string }[] = [
    { key: 'password', icon: <KeyIcon />, label: '密码登录' },
    { key: 'did', icon: <FingerprintIcon />, label: 'DID 登录' },
    { key: 'certificate', icon: <CertificateIcon />, label: '证书登录' },
  ];

  return (
    <>
      {/* 登录方式切换 */}
      <div className="mb-7 mt-6">
        <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-1">
          {loginMethods.map((m) => (
            <button
              key={m.key}
              onClick={() => onSwitchType(m.key)}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-all"
              style={{
                background: loginType === m.key ? '#fff' : 'transparent',
                color: loginType === m.key ? '#0052d9' : '#666',
                boxShadow: loginType === m.key ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              {m.icon}
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* 锁定提示 */}
      {lockoutMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
          <FingerprintIcon className="mt-0.5 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-700">账户已锁定</p>
            <p className="text-xs text-red-500">{lockoutMessage}</p>
            {lockoutRemaining > 0 && (
              <p className="mt-0.5 text-xs text-red-400">请等待 {lockoutRemaining} 分钟后重试</p>
            )}
          </div>
        </div>
      )}

      {/* ===== 密码登录 ===== */}
      {loginType === 'password' && (
        <div className="flex flex-col gap-4">
          <Input size="large" value={username} onChange={(val) => onUsernameChange(val as string)} onKeydown={onKeyDown} autofocus placeholder="用户名" prefixIcon={<UserIcon />} className={INPUT_CLASSES} />
          <Input
            size="large"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(val) => onPasswordChange(val as string)}
            onKeydown={onKeyDown}
            placeholder="密码"
            prefixIcon={<LockOnIcon />}
            suffixIcon={
              <span className="cursor-pointer" onClick={onTogglePassword}>
                {showPassword ? <BrowseOffIcon /> : <BrowseIcon />}
              </span>
            }
            className={INPUT_CLASSES}
          />
          <div className="flex items-center justify-between">
            <Checkbox checked={rememberMe} onChange={(v) => onRememberMeChange(v as boolean)}>
              <span className="text-sm text-gray-500">记住账号</span>
            </Checkbox>
            <span className="cursor-pointer text-sm text-blue-600 hover:text-blue-700">忘记密码？</span>
          </div>
          <Button
            size="large" theme="primary" block
            onClick={onSubmit}
            disabled={isPending || !!lockoutMessage}
            style={{ height: 48, borderRadius: 8, fontSize: 16, fontWeight: 600, marginTop: 4 }}
          >
            {passwordPending ? (
              <span className="flex items-center gap-2"><Loading size="small" /> 登录中...</span>
            ) : '登 录'}
          </Button>
        </div>
      )}

      {/* ===== DID 登录 ===== */}
      {loginType === 'did' && (
        <div className="flex flex-col gap-4">
          <Input size="large" value={did} onChange={(val) => onDidChange(val as string)} autofocus placeholder="did:web:example.com" prefixIcon={<FingerprintIcon />} className={INPUT_CLASSES} />
          <Input size="large" value={didSignature} onChange={(val) => onDidSignatureChange(val as string)} onKeydown={onKeyDown} placeholder="Base64 编码的签名值" className={INPUT_CLASSES} />
          <Input size="large" value={didChallenge} onChange={(val) => onDidChallengeChange(val as string)} onKeydown={onKeyDown} placeholder="挑战码" className={INPUT_CLASSES} />
          <Button
            size="large" theme="primary" block
            onClick={onSubmit}
            disabled={isPending}
            style={{ height: 48, borderRadius: 8, fontSize: 16, fontWeight: 600, background: BTN_COLORS.did, marginTop: 4 }}
          >
            {didPending ? (
              <span className="flex items-center gap-2"><Loading size="small" /> 验证中...</span>
            ) : 'DID 签名登录'}
          </Button>
        </div>
      )}

      {/* ===== 证书登录 ===== */}
      {loginType === 'certificate' && (
        <div className="flex flex-col gap-4">
          <Input size="large" value={certificate} onChange={(val) => onCertificateChange(val as string)} autofocus placeholder="PEM 格式证书内容" className={INPUT_CLASSES} />
          <Input size="large" value={certSignature} onChange={(val) => onCertSignatureChange(val as string)} onKeydown={onKeyDown} placeholder="Base64 签名值" className={INPUT_CLASSES} />
          <Button
            size="large" theme="primary" block
            onClick={onSubmit}
            disabled={isPending}
            style={{ height: 48, borderRadius: 8, fontSize: 16, fontWeight: 600, background: BTN_COLORS.certificate, marginTop: 4 }}
          >
            {certPending ? (
              <span className="flex items-center gap-2"><Loading size="small" /> 验证中...</span>
            ) : '证书登录'}
          </Button>
        </div>
      )}
    </>
  );
};

export default SSOButtons;
