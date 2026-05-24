/**
 * SSO 回调处理页面
 * 接收 OAuth2 Provider (Keycloak) 回传的 token 参数，
 * 自动存储 token 到 localStorage 并跳转到 dashboard。
 * 含 loading 状态和错误处理。
 */
import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Loading } from 'tdesign-react';
import { CheckCircleIcon, ErrorCircleIcon, FlashlightIcon } from 'tdesign-icons-react';
import { useAuthStore } from '@/stores/authStore';

/** SSO 回调状态 */
type CallbackStatus = 'loading' | 'success' | 'error';

/** 错误码到中文消息的映射 */
const ERROR_MESSAGES: Record<string, string> = {
  invalid_token: '无效的认证令牌，请重新登录。',
  expired_token: '认证令牌已过期，请重新登录。',
  missing_token: '缺少认证参数，请检查 SSO 配置。',
  unauthorized_client: '未授权的客户端，请联系管理员。',
  access_denied: '访问被拒绝，请确认权限。',
  server_error: '服务器内部错误，请稍后重试。',
  network_error: '网络连接失败，请检查网络。',
};

/** 解析 token 参数的 key 名称 */
const TOKEN_KEYS = ['access_token', 'token', 'code'] as const;
const REFRESH_TOKEN_KEYS = ['refresh_token'] as const;
const USER_KEYS = ['user', 'user_info'] as const;
const ERROR_KEYS = ['error', 'error_description'] as const;

/**
 * 从 URL 参数中提取 SSO 回调数据
 */
function extractCallbackParams(searchParams: URLSearchParams): {
  token: string | null;
  refreshToken: string | null;
  user: Record<string, unknown> | null;
  error: string | null;
  errorDescription: string | null;
} {
  let token: string | null = null;
  let refreshToken: string | null = null;
  let user: Record<string, unknown> | null = null;
  let error: string | null = null;
  let errorDescription: string | null = null;

  // 提取 token
  for (const key of TOKEN_KEYS) {
    const val = searchParams.get(key);
    if (val) {
      token = val;
      break;
    }
  }

  // 提取 refresh_token
  for (const key of REFRESH_TOKEN_KEYS) {
    const val = searchParams.get(key);
    if (val) {
      refreshToken = val;
      break;
    }
  }

  // 提取 user 信息
  for (const key of USER_KEYS) {
    const val = searchParams.get(key);
    if (val) {
      try {
        user = JSON.parse(decodeURIComponent(val));
      } catch {
        // user 参数解析失败，尝试 base64 解码
        try {
          user = JSON.parse(atob(val));
        } catch {
          // 无法解析 user，忽略
        }
      }
      break;
    }
  }

  // 提取错误信息
  for (const key of ERROR_KEYS) {
    const val = searchParams.get(key);
    if (val) {
      if (key === 'error') error = val;
      else errorDescription = val;
    }
  }

  return { token, refreshToken, user, error, errorDescription };
}

/**
 * SSO 回调页面组件
 */
const SSOCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<CallbackStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const processedRef = useRef(false);
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    // 防止在 StrictMode 下重复处理
    if (processedRef.current) return;
    processedRef.current = true;

    const { token, refreshToken, user, error, errorDescription } = extractCallbackParams(searchParams);

    // 如果 URL 中有错误参数
    if (error) {
      setStatus('error');
      setErrorMessage(ERROR_MESSAGES[error] || errorDescription || `认证失败: ${error}`);
      return;
    }

    // 如果没有 token
    if (!token) {
      // 也检查 hash fragment（某些 OAuth2 流程会把 token 放在 hash 里）
      const hash = window.location.hash.substring(1);
      const hashParams = new URLSearchParams(hash);
      const hashToken = hashParams.get('access_token') || hashParams.get('token');
      const hashRefresh = hashParams.get('refresh_token');

      if (hashToken) {
        processToken(hashToken, hashRefresh, null);
        return;
      }

      setStatus('error');
      setErrorMessage(ERROR_MESSAGES.missing_token);
      return;
    }

    processToken(token, refreshToken, user);

    function processToken(accessToken: string, refToken: string | null, userData: Record<string, unknown> | null) {
      try {
        // 存储 token 到 localStorage
        localStorage.setItem('eds_token', accessToken);
        if (refToken) {
          localStorage.setItem('eds_refresh_token', refToken);
        }

        // 如果有 user 信息，设置 auth store
        if (userData) {
          setAuth({
            access_token: accessToken,
            refresh_token: refToken || undefined,
            user: userData as unknown as import('@/types/api').UserInfo,
          });
        } else {
          // 即使没有 user 信息，也设置 token
          setAuth({
            access_token: accessToken,
            refresh_token: refToken || undefined,
            user: {
              user_id: '',
              username: '',
              email: '',
              role: 'user',
              organization_id: '',
            },
          });
        }

        setStatus('success');

        // 1.5 秒后跳转到 dashboard
        const redirectTimer = setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 1500);

        return () => clearTimeout(redirectTimer);
      } catch (err) {
        setStatus('error');
        setErrorMessage(ERROR_MESSAGES.server_error);
      }
    }
  }, [searchParams, navigate, setAuth]);

  /** 手动跳转到登录页 */
  const handleGoToLogin = () => {
    navigate('/login', { replace: true });
  };

  /** 手动跳转到首页 */
  const handleGoHome = () => {
    navigate('/', { replace: true });
  };

  const topBorderColor = status === 'loading'
    ? 'linear-gradient(90deg, #1976d2, #42a5f5)'
    : status === 'success'
      ? 'linear-gradient(90deg, #2e7d32, #66bb6a)'
      : 'linear-gradient(90deg, #d32f2f, #ef5350)';

  return (
    <div
      role="main"
      aria-label="SSO 登录回调处理"
      className="flex min-h-screen items-center justify-center p-2"
      style={{ background: 'linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0d47a1 100%)' }}
    >
      <div
        className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white p-10 text-center shadow-2xl"
      >
        {/* Top color bar */}
        <div
          className="absolute left-0 right-0 top-0 h-1"
          style={{ background: topBorderColor }}
        />

        {/* Logo */}
        <div className="mb-8 flex items-center justify-center gap-2">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl shadow-lg"
            style={{ background: 'linear-gradient(135deg, #1976d2, #0d47a1)', boxShadow: '0 4px 12px rgba(25,118,210,0.3)' }}
          >
            <FlashlightIcon className="text-xl text-white" />
          </div>
          <h6 className="text-lg font-bold text-blue-600">能源可信数据空间</h6>
        </div>

        {/* 加载状态 */}
        {status === 'loading' && (
          <div className="flex flex-col items-center gap-6">
            <Loading size="large" />
            <h6 className="text-lg font-semibold text-gray-900">正在处理 SSO 登录...</h6>
            <p className="text-sm text-gray-500">验证认证信息中，请稍候</p>
          </div>
        )}

        {/* 成功状态 */}
        {status === 'success' && (
          <div className="flex flex-col items-center gap-6">
            <CheckCircleIcon
              className="text-7xl text-green-600"
              style={{ animation: 'successPulse 0.6s ease-out' }}
            />
            <h5 className="text-xl font-bold text-green-600">登录成功</h5>
            <p className="text-base text-gray-500">认证信息已验证，正在跳转到控制台...</p>
            <Loading />
          </div>
        )}

        {/* 错误状态 */}
        {status === 'error' && (
          <div className="flex flex-col items-center gap-6">
            <ErrorCircleIcon className="text-7xl text-red-600" />
            <h5 className="text-xl font-bold text-red-600">登录失败</h5>
            <div
              className="w-full rounded-md border border-red-200 p-4"
              style={{ backgroundColor: 'rgba(211, 47, 47, 0.08)' }}
            >
              <p className="text-sm text-red-600">{errorMessage}</p>
            </div>
            <div className="mt-2 flex gap-4">
              <Button theme="primary" onClick={handleGoToLogin} aria-label="重新登录">
                重新登录
              </Button>
              <Button variant="outline" onClick={handleGoHome} aria-label="返回首页">
                返回首页
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Keyframe animation for success pulse */}
      <style>{`
        @keyframes successPulse {
          0% { transform: scale(0); opacity: 0; }
          50% { transform: scale(1.2); opacity: 1; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default SSOCallbackPage;
