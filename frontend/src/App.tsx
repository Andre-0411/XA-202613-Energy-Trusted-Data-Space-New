import { useRoutes } from 'react-router-dom';
import { routes } from './routes';

/**
 * 根组件 - 路由挂载点
 * 使用 useRoutes 渲染路由配置
 */
const App = () => {
  const element = useRoutes(routes);
  return element;
};

export default App;
