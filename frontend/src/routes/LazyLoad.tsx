import React, { Suspense } from 'react';
import { Loading } from 'tdesign-react';

/**
 * 懒加载包装组件
 * 使用 React.lazy + Suspense 实现页面级代码分割
 * 显示居中加载 Spinner
 */
interface LazyLoadProps {
  children: React.ReactNode;
}

const LazyLoad: React.FC<LazyLoadProps> = ({ children }) => {
  return (
    <Suspense
      fallback={
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '50vh',
            width: '100%',
          }}
        >
          <Loading size="medium" />
        </div>
      }
    >
      {children}
    </Suspense>
  );
};

export default LazyLoad;
