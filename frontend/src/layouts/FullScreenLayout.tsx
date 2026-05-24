import React from 'react';

/**
 * 全屏布局组件
 * 无边距全屏，用于监管大屏
 */
interface FullScreenLayoutProps {
  children: React.ReactNode;
}

const FullScreenLayout: React.FC<FullScreenLayoutProps> = ({ children }) => {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {children}
    </div>
  );
};

export default FullScreenLayout;
