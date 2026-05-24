/**
 * 认证状态管理（Zustand）
 * token / user / isAuthenticated / permissions / mfaRequired
 * login / loginWithDID / logout / refreshToken / setMfaVerified / checkAuth
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserInfo } from '@/types/api';
import * as authApi from '@/api/auth';
import { setTokens, clearTokens } from '@/api/request';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  permissions: string[];
  mfaRequired: boolean;
  mfaVerified: boolean;
  mfaSessionId: string | null;

  login: (username: string, password: string) => Promise<{ mfaRequired: boolean }>;
  loginWithDID: (did: string, signature: string, challenge: string) => Promise<{ mfaRequired: boolean }>;
  setAuth: (data: { access_token: string; refresh_token?: string; user: UserInfo }) => void;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  setMfaVerified: (verified: boolean) => void;
  checkAuth: () => void;
  setPermissions: (perms: string[]) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      permissions: [],
      mfaRequired: false,
      mfaVerified: false,
      mfaSessionId: null,

      login: async (username: string, password: string) => {
        const res = await authApi.login({ username, password });
        const { access_token, refresh_token, user, mfa_required, mfa_session_id } = res.data as any;

        // 如果需要 MFA 验证，暂存状态并返回
        if (mfa_required) {
          set({
            token: access_token,
            refreshToken: refresh_token,
            user,
            mfaRequired: true,
            mfaVerified: false,
            mfaSessionId: mfa_session_id || null,
            isAuthenticated: false,
          });
          return { mfaRequired: true };
        }

        setTokens(access_token, refresh_token);
        set({
          token: access_token,
          refreshToken: refresh_token,
          user,
          isAuthenticated: true,
          permissions: user.permissions || [],
          mfaRequired: false,
          mfaVerified: true,
          mfaSessionId: null,
        });
        return { mfaRequired: false };
      },

      loginWithDID: async (did: string, signature: string, challenge: string) => {
        const res = await authApi.loginWithDID({ did, signature, challenge });
        const { access_token, refresh_token, user, mfa_required, mfa_session_id } = res.data as any;

        if (mfa_required) {
          set({
            token: access_token,
            refreshToken: refresh_token,
            user,
            mfaRequired: true,
            mfaVerified: false,
            mfaSessionId: mfa_session_id || null,
            isAuthenticated: false,
          });
          return { mfaRequired: true };
        }

        setTokens(access_token, refresh_token);
        set({
          token: access_token,
          refreshToken: refresh_token,
          user,
          isAuthenticated: true,
          permissions: user.permissions || [],
          mfaRequired: false,
          mfaVerified: true,
          mfaSessionId: null,
        });
        return { mfaRequired: false };
      },

      setAuth: (data: { access_token: string; refresh_token?: string; user: UserInfo }) => {
        const { access_token, refresh_token, user } = data;
        setTokens(access_token, refresh_token);
        set({
          token: access_token,
          refreshToken: refresh_token || null,
          user,
          isAuthenticated: true,
          permissions: user.permissions || [],
          mfaRequired: false,
          mfaVerified: true,
          mfaSessionId: null,
        });
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // 忽略登出请求错误
        }
        clearTokens();
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          permissions: [],
          mfaRequired: false,
          mfaVerified: false,
          mfaSessionId: null,
        });
      },

      refreshAccessToken: async () => {
        const currentRefreshToken = get().refreshToken;
        if (!currentRefreshToken) return;
        try {
          const res = await authApi.refreshToken(currentRefreshToken);
          const { access_token, refresh_token } = res.data;
          setTokens(access_token, refresh_token);
          set({ token: access_token, refreshToken: refresh_token });
        } catch {
          get().logout();
        }
      },

      setMfaVerified: (verified: boolean) => {
        set({ mfaVerified: verified, mfaRequired: !verified });
      },

      checkAuth: () => {
        const storedToken = localStorage.getItem('eds_token');
        if (storedToken && !get().token) {
          set({ token: storedToken, isAuthenticated: true });
        } else if (!storedToken) {
          set({
            token: null,
            user: null,
            isAuthenticated: false,
            permissions: [],
          });
        }
      },

      setPermissions: (perms: string[]) => {
        set({ permissions: perms });
      },
    }),
    {
      name: 'eds-auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        permissions: state.permissions,
      }),
    },
  ),
);
