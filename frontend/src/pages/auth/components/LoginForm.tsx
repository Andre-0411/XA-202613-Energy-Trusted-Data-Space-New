/**
 * LoginForm - 登录表单（含MFA二次验证）
 * 管理所有登录状态、API调用、表单渲染
 */
import React, { useState, useCallback, useEffect } from 'react';
import { Button, Input, MessagePlugin, Loading } from 'tdesign-react';
import {
  SecuredIcon, RefreshIcon, ChevronLeftIcon,
} from 'tdesign-icons-react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { loginWithCertificate, mfaVerify } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import SSOButtons, { type LoginType } from './SSOButtons';

/* ============================================================
 * LoginForm 主组件
 * ============================================================ */
const LoginForm: React.FC = () => {
  const navigate = useNavigate();
  const {
    mfaRequired, mfaSessionId, mfaVerified,
    setMfaVerified,
  } = useAuthStore();

  // ===== 状态 =====
  const [loginType, setLoginType] = useState<LoginType>('password');
  const [showMfa, setShowMfa] = useState(false);

  // 密码
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // DID
  const [did, setDid] = useState('');
  const [didSignature, setDidSignature] = useState('');
  const [didChallenge, setDidChallenge] = useState('');

  // 证书
  const [certificate, setCertificate] = useState('');
  const [certSignature, setCertSignature] = useState('');

  // MFA
  const [totpCode, setTotpCode] = useState('');
  const [mfaMethod, setMfaMethod] = useState<'totp' | 'backup'>('totp');
  const [backupCode, setBackupCode] = useState('');

  // 锁定
  const [lockoutMessage, setLockoutMessage] = useState<string | null>(null);
  const [lockoutRemaining, setLockoutRemaining] = useState(0);

  // 动画
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { setLoaded(true); }, []);

  const toast = useCallback((msg: string, type: 'error' | 'success' | 'info' = 'error') => {
    if (type === 'success') MessagePlugin.success(msg);
    else if (type === 'info') MessagePlugin.info(msg);
    else MessagePlugin.error(msg);
  }, []);

  // 切换登录方式
  const switchType = useCallback((type: LoginType) => {
    setLoginType(type);
    setShowMfa(false);
    setUsername(''); setPassword('');
    setDid(''); setDidSignature(''); setDidChallenge('');
    setCertificate(''); setCertSignature('');
    setTotpCode(''); setBackupCode('');
  }, []);

  // 进入 MFA 验证
  useEffect(() => {
    if (mfaRequired && !mfaVerified && !showMfa) {
      setShowMfa(true);
    }
  }, [mfaRequired, mfaVerified, showMfa]);

  // ===== 密码登录 =====
  const passwordMut = useMutation({
    mutationFn: (data: { username: string; password: string }) =>
      useAuthStore.getState().login(data.username, data.password),
    onSuccess: (result) => {
      setLockoutMessage(null);
      setLockoutRemaining(0);
      if (result.mfaRequired) {
        setShowMfa(true);
      } else {
        navigate('/dashboard', { replace: true });
      }
    },
    onError: (err: Error) => {
      const msg = err.message || '登录失败';
      const lockMatch = msg.match(/账户已锁定.*?(\d+)\s*分钟/);
      if (lockMatch) {
        setLockoutMessage(msg);
        setLockoutRemaining(parseInt(lockMatch[1], 10));
      } else {
        setLockoutMessage(null);
        setLockoutRemaining(0);
      }
      toast(msg);
    },
  });

  // ===== DID 登录 =====
  const didMut = useMutation({
    mutationFn: (data: { did: string; signature: string; challenge: string }) =>
      useAuthStore.getState().loginWithDID(data.did, data.signature, data.challenge),
    onSuccess: (result) => {
      if (result.mfaRequired) {
        setShowMfa(true);
      } else {
        navigate('/dashboard', { replace: true });
      }
    },
    onError: () => toast('DID 签名登录失败'),
  });

  // ===== 证书登录 =====
  const certMut = useMutation({
    mutationFn: (data: { certificate: string; signature: string }) =>
      loginWithCertificate({ ...data, password: '' }),
    onSuccess: (res) => {
      if (res.data?.access_token && res.data?.user) {
        navigate('/dashboard', { replace: true });
      } else {
        toast('证书登录响应异常');
      }
    },
    onError: () => toast('证书登录失败'),
  });

  // ===== MFA 验证 =====
  const mfaMut = useMutation({
    mutationFn: (data: { user_id: string; code: string; session_id?: string }) =>
      mfaVerify(data),
    onSuccess: (res) => {
      if (res.data?.access_token && res.data?.user) {
        setMfaVerified(true);
        setShowMfa(false);
        navigate('/dashboard', { replace: true });
      } else if ((res.data as any)?.verified) {
        toast('MFA 验证成功', 'success');
        setTimeout(() => {
          setShowMfa(false);
          navigate('/dashboard', { replace: true });
        }, 600);
      } else {
        toast((res.data as any)?.message || 'MFA 验证失败');
      }
    },
    onError: () => toast('MFA 验证失败，请检查验证码'),
  });

  // ===== 提交 =====
  const handleSubmit = useCallback(() => {
    if (showMfa) {
      const code = mfaMethod === 'backup' ? backupCode : totpCode;
      if (!code.trim()) { toast('请输入验证码'); return; }
      if (mfaMethod === 'totp' && code.length !== 6) { toast('请输入6位TOTP验证码'); return; }
      const user = useAuthStore.getState().user;
      mfaMut.mutate({
        user_id: user?.user_id || '',
        code,
        session_id: mfaSessionId ?? undefined,
      });
      return;
    }
    if (loginType === 'password') {
      if (!username.trim() || !password.trim()) { toast('请输入用户名和密码'); return; }
      passwordMut.mutate({ username, password });
    } else if (loginType === 'did') {
      if (!did.trim() || !didSignature.trim() || !didChallenge.trim()) { toast('请填写完整 DID 信息'); return; }
      didMut.mutate({ did, signature: didSignature, challenge: didChallenge });
    } else if (loginType === 'certificate') {
      if (!certificate.trim() || !certSignature.trim()) { toast('请填写证书和签名'); return; }
      certMut.mutate({ certificate, signature: certSignature });
    }
  }, [
    showMfa, mfaMethod, backupCode, totpCode, mfaSessionId,
    loginType, username, password, did, didSignature, didChallenge,
    certificate, certSignature, passwordMut, didMut, certMut, mfaMut, toast,
  ]);

  const handleKeyDown = useCallback((_val: string, ctx?: { e: React.KeyboardEvent }) => {
    if (ctx?.e.key === 'Enter') handleSubmit();
  }, [handleSubmit]);

  const isPending = passwordMut.isPending || didMut.isPending || certMut.isPending || mfaMut.isPending;

  return (
    <div
      className="flex h-full w-full flex-col items-center justify-center bg-white px-6 py-8 sm:px-10 sm:py-12"
      style={{
        opacity: loaded ? 1 : 0,
        transform: loaded ? 'translateY(0)' : 'translateY(12px)',
        transition: 'all 0.5s ease-out',
      }}
    >
      <div className="w-full max-w-[400px]">
        {/* ===== MFA 二次验证 ===== */}
        {showMfa ? (
          <div className="animate-[fadeIn_0.3s_ease-out]">
            <button
              onClick={() => { setShowMfa(false); setMfaVerified(false); }}
              className="mb-8 flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600"
            >
              <ChevronLeftIcon /> 返回登录
            </button>

            <div className="mb-8">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-orange-50">
                <SecuredIcon className="text-2xl text-orange-500" />
              </div>
              <h2 className="mb-1 text-2xl font-bold text-gray-900">二次验证</h2>
              <p className="text-sm text-gray-500">您的账户已启用多因素认证，请输入验证码继续</p>
            </div>

            <div className="mb-5 flex gap-2">
              {([
                { key: 'totp' as const, label: 'TOTP 验证码' },
                { key: 'backup' as const, label: '备份码' },
              ]).map((item) => (
                <button
                  key={item.key}
                  onClick={() => { setMfaMethod(item.key); setTotpCode(''); setBackupCode(''); }}
                  className="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
                  style={{
                    background: mfaMethod === item.key ? 'rgba(255,152,0,0.1)' : 'transparent',
                    color: mfaMethod === item.key ? '#e65100' : '#999',
                    border: mfaMethod === item.key ? '1px solid rgba(255,152,0,0.3)' : '1px solid transparent',
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {mfaMethod === 'totp' && (
              <div className="mb-6">
                <Input
                  size="large" value={totpCode}
                  onChange={(val) => setTotpCode((val as string).replace(/\D/g, '').slice(0, 6))}
                  onKeydown={handleKeyDown} autofocus placeholder="输入6位动态验证码"
                  maxlength={6} prefixIcon={<SecuredIcon />} className="login-dark-input"
                />
                <p className="mt-2 text-xs text-gray-400">请打开认证器应用 (Google Authenticator / Microsoft Authenticator) 获取验证码</p>
              </div>
            )}

            {mfaMethod === 'backup' && (
              <div className="mb-6">
                <Input
                  size="large" value={backupCode}
                  onChange={(val) => setBackupCode(val as string)}
                  onKeydown={handleKeyDown} autofocus placeholder="输入备用验证码"
                  prefixIcon={<RefreshIcon />} className="login-dark-input"
                />
                <p className="mt-2 text-xs text-gray-400">使用您保存的备用验证码进行验证</p>
              </div>
            )}

            <Button
              size="large" theme="primary" block onClick={handleSubmit} disabled={isPending}
              style={{ height: 48, borderRadius: 8, fontSize: 16, fontWeight: 600, background: 'linear-gradient(135deg, #f57c00, #ff9800)' }}
            >
              {mfaMut.isPending ? (
                <span className="flex items-center gap-2"><Loading size="small" /> 验证中...</span>
              ) : '验证并登录'}
            </Button>
          </div>
        ) : (
          /* ===== 标准登录 ===== */
          <>
            <div className="mb-2">
              <h1 className="text-[28px] font-bold leading-tight text-gray-900">欢迎回来</h1>
              <p className="mt-1.5 text-sm text-gray-500">登录能源可信数据空间平台</p>
            </div>

            <SSOButtons
              loginType={loginType}
              onSwitchType={switchType}
              username={username}
              onUsernameChange={setUsername}
              password={password}
              onPasswordChange={setPassword}
              showPassword={showPassword}
              onTogglePassword={() => setShowPassword((v) => !v)}
              rememberMe={rememberMe}
              onRememberMeChange={setRememberMe}
              did={did}
              onDidChange={setDid}
              didSignature={didSignature}
              onDidSignatureChange={setDidSignature}
              didChallenge={didChallenge}
              onDidChallengeChange={setDidChallenge}
              certificate={certificate}
              onCertificateChange={setCertificate}
              certSignature={certSignature}
              onCertSignatureChange={setCertSignature}
              onSubmit={handleSubmit}
              onKeyDown={handleKeyDown}
              isPending={isPending}
              passwordPending={passwordMut.isPending}
              didPending={didMut.isPending}
              certPending={certMut.isPending}
              lockoutMessage={lockoutMessage}
              lockoutRemaining={lockoutRemaining}
            />
          </>
        )}
      </div>

      {/* 暗色输入框样式 */}
      <style>{`.login-dark-input .t-input { border-radius: 8px !important; }`}</style>
    </div>
  );
};

export default LoginForm;
