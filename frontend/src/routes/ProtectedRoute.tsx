import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { Button } from 'tdesign-react';
import { hasRouteAccess, type UserRole } from '@/config/rolePermissions';

/**
 * 认证 + 权限守卫路由组件
 *
 * 功能:
 * 1. 检查用户是否已登录（从 localStorage 读取 eds_token）
 * 2. 未登录重定向到 /login
 * 3. 检查用户角色是否有权限访问当前路由
 * 4. 无权限显示 403 页面
 */
const ProtectedRoute: React.FC = () => {
  const location = useLocation();
  const token = localStorage.getItem('eds_token');

  // 未登录 - 重定向到登录页
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 解析用户信息（Zustand persist 存储格式）
  let user: { role?: string; permissions?: string[] } = {};
  try {
    const authStr = localStorage.getItem('eds-auth-storage');
    if (authStr) {
      const authData = JSON.parse(authStr);
      user = authData?.state?.user || {};
    }
  } catch {
    // JSON 解析失败，清除 token
    localStorage.removeItem('eds_token');
    localStorage.removeItem('eds_refresh_token');
    localStorage.removeItem('eds-auth-storage');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 检查角色路由权限
  const currentPath = location.pathname;
  const userRole = (user.role || 'user') as UserRole;

  if (!hasRouteAccess(userRole, currentPath)) {
    return <ForbiddenPage />;
  }

  return <Outlet />;
};

/** 403 无权限页面 */
const ForbiddenPage: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: 16,
      }}
    >
      <h1 style={{ fontSize: '6rem', color: '#D32F2F', fontWeight: 700, margin: 0 }}>
        403
      </h1>
      <p style={{ fontSize: '1.25rem', color: 'rgba(0,0,0,0.6)', margin: 0 }}>
        您没有权限访问此页面
      </p>
      <Button
        theme="primary"
        href="/"
        style={{ marginTop: 16 }}
      >
        返回首页
      </Button>
    </div>
  );
};

export default ProtectedRoute;
