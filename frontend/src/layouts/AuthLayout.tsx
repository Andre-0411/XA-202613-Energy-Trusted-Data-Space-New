import React from 'react';

/**
 * 认证布局组件 - 透传
 * LoginPage 自己处理全屏背景和绝对定位布局，无需额外包装
 */
interface AuthLayoutProps {
  children: React.ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return <>{children}</>;
};

export default AuthLayout;
