/**
 * 登录页面 - TDesign Starter 左右排版
 * 左侧：品牌展示区（BackgroundEffects 背景动效）
 * 右侧：登录表单（LoginForm 含 SSOButtons）
 *
 * 重构后：主组件仅负责布局编排
 */
import React from 'react';
import BackgroundEffects from './components/BackgroundEffects';
import LoginForm from './components/LoginForm';

/* ============================================================
 * 主登录页面
 * ============================================================ */
const LoginPage: React.FC = () => {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-white">
      {/* 左侧品牌面板 */}
      <BackgroundEffects />

      {/* 右侧登录表单 */}
      <div className="flex flex-1 items-center justify-center bg-white">
        <LoginForm />
      </div>
    </div>
  );
};

export default LoginPage;
