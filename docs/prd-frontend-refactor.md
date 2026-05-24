# 前端重构 PRD — tdesign-react 迁移 + 后端模拟数据清理

## 一、项目信息

| 字段 | 值 |
|------|-----|
| **Language** | 中文 |
| **Programming Language** | Vite + React 18 + TypeScript + tdesign-react + Tailwind CSS |
| **Project Name** | energy_trusted_data_space_frontend_refactor |
| **原始需求** | 1. 引入 tdesign-react 组件库替换 MUI，参照 TDesign React Starter 设计风格重构后台界面<br>2. 清理后端模拟数据，将所有仍使用 random/mock 的后端端点替换为真实 DB 查询 |

---

## 二、产品定义

### 1. 产品目标

| # | 目标 | 衡量标准 |
|---|------|----------|
| G1 | **UI 组件库统一迁移** — 将全部 MUI 组件平滑替换为 tdesign-react，保持现有功能完整性 | 89 个 TSX 文件 100% 完成迁移；0 个 MUI 残留引用；全部页面可正常访问 |
| G2 | **设计风格标准化** — 统一采用 TDesign React Starter 的设计语言，提升后台专业感 | 色彩/间距/圆角/阴影等视觉规范 100% 对齐；侧边栏/顶栏/表格/卡片等核心组件风格一致 |
| G3 | **后端数据真实性** — 消除所有后端模拟数据，确保每个 API 返回真实数据库查询结果 | 33 个 API service 文件 100% 调用真实后端；0 个 random/mock 残留；数据一致性校验通过 |

### 2. 用户故事

| # | 角色 | 用户故事 |
|---|------|----------|
| US1 | 前端开发工程师 | 作为前端开发工程师，我想使用统一的 tdesign-react 组件库，以便减少样式冲突、提高开发效率和代码一致性 |
| US2 | 后端开发工程师 | 作为后端开发工程师，我想清理所有模拟数据端点，以便前端能接收到真实可靠的业务数据 |
| US3 | UI/UX 设计师 | 作为 UI/UX 设计师，我想让后台界面采用 TDesign 标准设计风格，以便提升产品的专业感和用户体验一致性 |
| US4 | 产品经理 | 作为产品经理，我想确保重构过程中功能不丢失、性能不下降，以便业务用户无感知地完成技术升级 |
| US5 | 测试工程师 | 作为测试工程师，我想有清晰的迁移验收标准和回归测试清单，以便高效验证重构质量 |

---

## 三、技术规范

### 1. 需求池

#### P0 — 必须完成

| ID | 需求 | 说明 |
|----|------|------|
| P0-01 | tdesign-react 核心依赖安装与配置 | 安装 `tdesign-react`、`tdesign-icons-react`，配置按需加载（babel-plugin-import 或 tdesign-react-plugin） |
| P0-02 | 主题定制 — TDesign 风格 Token | 配置 CSS Variables：主色 `#0052D9`、侧边栏背景 `#18181D`、卡片阴影 `0 2px 8px rgba(0,0,0,0.08)`、圆角 `8px` |
| P0-03 | 布局组件迁移 (MainLayout) | 侧边栏 `Menu` + 顶栏 `Layout.Header` + 面包屑 `Breadcrumb` + 页签 `Tabs`，参照 TDesign React Starter |
| P0-04 | 表格组件迁移 | 替换 MUI `DataGrid/Table` 为 tdesign-react `Table`，保留排序/筛选/分页功能 |
| P0-05 | 表单组件迁移 | Input/Select/DatePicker/Form 等表单组件全部替换 |
| P0-06 | 弹窗/抽屉组件迁移 | Dialog/Drawer/Notification/Message 替换 |
| P0-07 | 后端 data_asset.py 清理 | 移除 `random.uniform`，接入真实电力/用电/电网/电力市场数据库查询 |
| P0-08 | 后端 quality.py 清理 | 移除模拟数据，接入真实数据质量评估结果 |
| P0-09 | 后端 security_hsm.py 清理 | 移除模拟 HSM 数据，对接真实密钥管理服务或数据库 |

#### P1 — 应该完成

| ID | 需求 | 说明 |
|----|------|------|
| P1-01 | 按钮/图标/标签组件迁移 | Button/Icon/Tag/Badge 等基础组件替换 |
| P1-02 | 图表容器组件迁移 | ECharts 容器包装组件使用 tdesign-react Card/Panel |
| P1-03 | 流程图容器迁移 | ReactFlow 容器使用 tdesign-react 布局组件包裹 |
| P1-04 | 后端 compute_benchmark.py 清理 | 移除计算基准模拟数据，接入真实计算任务数据库 |
| P1-05 | 后端 compute_enhanced.py 清理 | 移除增强计算模拟数据 |
| P1-06 | 后端 data_enhanced.py 清理 | 移除增强数据模拟数据 |
| P1-07 | 通知/消息中心组件迁移 | Notification/Message/Alert 组件替换 |
| P1-08 | 状态管理适配 | 确保 Zustand stores 与 tdesign-react 组件的受控模式兼容 |

#### P2 — 可以完成

| ID | 需求 | 说明 |
|----|------|------|
| P2-01 | 暗色主题支持 | 利用 tdesign-react 主题能力实现暗色模式切换 |
| P2-02 | 后端 sharing_center 清理 | 隐私计算模块模拟数据清理（依赖隐私计算引擎对接） |
| P2-03 | 动画/过渡效果优化 | 使用 tdesign-react 内置动画提升交互体验 |
| P2-04 | 响应式适配增强 | 移动端/平板端布局适配 |

---

### 2. MUI → tdesign-react 组件映射表

| MUI 组件 | tdesign-react 替代 | 迁移难度 | 备注 |
|----------|-------------------|----------|------|
| `Box` / `Stack` | `Row` / `Col` / 自定义 div | 低 | 布局组件，可用 Grid 系统替代 |
| `Typography` | 自定义 Typography 或原生标签 | 低 | 需配置 Tailwind 字体类 |
| `Button` | `Button` | 低 | API 基本一致 |
| `TextField` | `Input` / `Textarea` | 中 | 属性名有差异，需逐个调整 |
| `Select` | `Select` | 中 | 选项结构不同 |
| `MenuItem` | `Option` (Select 子组件) | 低 | 配合 Select 使用 |
| `Table` / `DataGrid` | `Table` | 高 | DataGrid 功能丰富，需重点适配 |
| `Dialog` | `Dialog` | 低 | API 相似 |
| `Drawer` | `Drawer` | 低 | API 相似 |
| `Snackbar` | `Message` | 低 | 调用方式不同 |
| `Alert` | `Alert` / `Notification` | 低 | 需区分场景 |
| `Tabs` | `Tabs` | 低 | API 相似 |
| `Card` | `Card` | 低 | API 相似 |
| `Chip` / `Tag` | `Tag` | 低 | 属性名调整 |
| `IconButton` | `Button` + `Icon` | 低 | 组合使用 |
| `Tooltip` | `Tooltip` | 低 | API 相似 |
| `Progress` | `Progress` | 低 | API 相似 |
| `Skeleton` | `Skeleton` | 低 | API 相似 |
| `Menu` (侧边栏) | `Menu` | 中 | 需要适配嵌套结构 |
| `AppBar` | `Layout.Header` | 低 | 布局组件 |
| `Breadcrumbs` | `Breadcrumb` | 低 | API 简化 |
| `Avatar` | `Avatar` | 低 | API 相似 |
| `Badge` | `Badge` | 低 | API 相似 |
| `Switch` | `Switch` | 低 | API 相似 |
| `Checkbox` | `Checkbox` | 低 | API 相似 |
| `Radio` | `Radio` | 低 | API 相似 |
| `Pagination` | `Pagination` | 低 | API 相似 |
| `Stepper` | `Steps` | 中 | 属性名调整 |

---

### 3. 分批次实施策略

```
Phase 1 — 基础搭建 (Week 1)
├── 安装 tdesign-react 依赖
├── 配置主题 Token 和全局样式
├── 迁移 MainLayout.tsx（侧边栏+顶栏+面包屑+页签）
└── 迁移基础组件：Button, Icon, Tag, Avatar

Phase 2 — 核心页面 (Week 2-3)
├── 迁移数据资源中心页面（表格重）
├── 迁移运营管理中心页面（表单重）
├── 迁移安全管控中心页面（弹窗重）
└── 同步清理 P0 后端模拟数据（data_asset, quality, security_hsm）

Phase 3 — 复杂组件 (Week 4)
├── 迁移图表相关页面（ECharts 容器）
├── 迁移流程图相关页面（ReactFlow 容器）
├── 迁移隐私计算中心页面
└── 清理 P1 后端模拟数据（compute_benchmark, compute_enhanced, data_enhanced）

Phase 4 — 收尾优化 (Week 5)
├── 全量回归测试
├── 性能对比测试
├── 清理残留 MUI 依赖
└── 更新开发文档
```

---

### 4. 需要新增的 tdesign-react 依赖包

```json
{
  "dependencies": {
    "tdesign-react": "^1.x.x",
    "tdesign-icons-react": "^0.x.x"
  },
  "devDependencies": {
    "babel-plugin-import": "^1.13.x",
    "tdesign-react-plugin": "^0.x.x"
  }
}
```

> 注：具体版本号需根据 tdesign-react 最新稳定版确定。

---

### 5. UI 设计规范 — TDesign React Starter 风格

| 规范项 | 值 | 说明 |
|--------|-----|------|
| **主色调** | `#0052D9` | TDesign 蓝色，用于主按钮、链接、选中态 |
| **侧边栏背景** | `#18181D` | 深色背景，白色文字 |
| **侧边栏宽度** | 展开 `232px` / 收起 `64px` | 可折叠设计 |
| **卡片圆角** | `8px` | 统一使用 |
| **卡片阴影** | `0 2px 8px rgba(0,0,0,0.08)` | 轻盈阴影 |
| **表格表头** | 浅灰色背景 `#F5F5F5` | 行间细线分隔 `#E8E8E8` |
| **间距系统** | 4px 基础单位，常用 `8/12/16/24/32px` | 遵循 TDesign 间距规范 |
| **字体** | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei'` | 系统字体栈 |
| **正文字号** | `14px` | TDesign 默认正文 |
| **标题字号** | H1: `20px`, H2: `16px`, H3: `14px` 加粗 | 遵循 TDesign 字号规范 |

---

### 6. 后端模拟数据清理优先级

| 优先级 | 文件 | 模拟数据类型 | 清理策略 |
|--------|------|-------------|----------|
| **P0** | `api/v1/data_asset.py` | `random.uniform` 生成电力/用电/电网/电力市场数据 | 对接 PostgreSQL `data_assets` 表，使用 SQLAlchemy 查询 |
| **P0** | `api/v1/quality.py` | 数据质量评估模拟值 | 对接 `data_quality_metrics` 表或实时计算 |
| **P0** | `api/v1/security_hsm.py` | HSM 密钥管理模拟 | 对接真实 HSM 服务或 `key_management` 表 |
| **P1** | `api/v1/compute_benchmark.py` | 计算基准模拟数据 | 对接 `compute_tasks` 表 |
| **P1** | `api/v1/compute_enhanced.py` | 增强计算模拟 | 对接 `compute_results` 表 |
| **P1** | `api/v1/data_enhanced.py` | 增强数据模拟 | 对接 `data_enhanced_metrics` 表 |
| **P2** | `modules/sharing_center/` | 隐私计算模块模拟 | 依赖 FATE/MPC 引擎对接，可暂保留 mock 接口 |

---

## 四、待确认问题

| # | 问题 | 影响范围 | 建议 |
|---|------|----------|------|
| Q1 | tdesign-react 是否支持与 Tailwind CSS 共存？是否需要关闭 TDesign 的内置样式？ | 全局样式 | 需验证 CSS 优先级，可能需要配置 `important` 或使用 CSS Modules 隔离 |
| Q2 | 现有 MUI `DataGrid` 高级功能（列拖拽、行分组、导出）在 tdesign-react `Table` 中如何实现？ | 数据密集型页面 | 需要调研 tdesign-react Table 的扩展能力，可能需要自定义插件 |
| Q3 | 后端模拟数据清理后，数据库表结构是否已就绪？是否需要先执行 Alembic 迁移？ | 后端全部文件 | 需要与后端开发确认数据库 schema 版本 |
| Q4 | ECharts 和 ReactFlow 的容器组件迁移是否会影响图表/流程图的渲染和交互？ | 可视化页面 | 需要重点测试，确保 ref 和事件绑定正常 |
| Q5 | 是否需要保持向后兼容（即迁移过程中是否允许 MUI 和 tdesign-react 共存）？ | 迁移策略 | 建议允许短期共存（Phase 1-2），Phase 3 后完全移除 MUI |
| Q6 | 国密 SSL 环境下 tdesign-react 的 CDN 字体/图标是否可用？ | 离线部署 | 可能需要将字体和图标打包到本地 |

---

## 五、验收标准

1. **功能完整性**：所有现有页面功能正常，无回归 Bug
2. **组件覆盖率**：89 个 TSX 文件中 MUI 引用数为 0
3. **后端数据真实性**：33 个 API service 文件中 `random`/`mock` 引用数为 0
4. **视觉一致性**：TDesign 风格规范 100% 落地
5. **性能不退化**：页面首屏加载时间 ≤ 2 秒，API P99 ≤ 500ms