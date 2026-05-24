# 能源可信数据空间系统 (Energy Trusted Data Space)

挑战杯“揭榜挂帅” XA-202613国网山东省电力公司经济技术研究院-面向能源可信数据空间的多方安全协同与隐私保护技术创新解决方案比赛方案

## 项目简介

基于可信数据空间（Trusted Data Space）理念，构建面向能源行业的去中心化数据流通与协作平台。系统采用"一门户五中心"架构，融合区块链存证、隐私计算、AI 智能体等前沿技术。

## 系统架构

```
能源可信数据空间系统
├── 统一门户 (Portal)
├── 身份认证管理中心 (Auth Center)
├── 存证中心 (Evidence Center)
├── 数据共享中心 (Sharing Center)
├── 监控中心 (Monitor Center)
└── 分析中心 (Analytics Center)
```

## 技术栈

### 后端
- Python 3.13 + FastAPI
- SQLAlchemy 2.0 + PostgreSQL
- Redis (缓存 + 消息队列)
- Pydantic v2 (数据校验)
- Alembic (数据库迁移)

### 前端
- Vue 3 (Composition API + TypeScript)
- Element Plus (UI 组件库)
- Pinia (状态管理)
- ECharts (数据可视化)
- Vite (构建工具)

### 基础设施
- Docker + Docker Compose
- Nginx (反向代理)
- PostgreSQL 16
- Redis 7

## 快速启动

### 前置条件
- Docker Desktop
- Node.js 22+
- Python 3.13+

### 使用 Docker Compose 启动（推荐）

```bash
# 克隆仓库
git clone https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git
cd XA-202613-Energy-Trusted-Data-Space-New

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend
```

访问：
- 前端：`http://localhost`
- 后端 API 文档：`http://localhost:8000/docs`

### 本地开发启动

**后端：**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

## 默认账号

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | admin | admin123 | 全部权限 |
| 数据提供方 | provider1 | provider123 | 数据管理、共享审批 |
| 数据使用方 | consumer1 | consumer123 | 数据查询、申请使用 |
| 审计员 | auditor1 | auditor123 | 审计日志、合规检查 |
| 运营员 | operator1 | operator123 | 系统监控、告警管理 |

## 核心功能

### 1. 身份认证管理中心
- 分布式身份认证 (DID)
- 基于属性的访问控制 (ABAC)
- JWT 令牌管理
- 国密算法支持 (SM2/SM3/SM4)

### 2. 存证中心
- 区块链存证 (模拟 FISCO BCOS)
- 哈希上链 + 原文本地存储
- 存证验证与追溯
- 合规审计日志

### 3. 数据共享中心
- 数据资产目录管理
- 隐私计算任务调度 (模拟 FATE)
- 联邦学习 / 多方安全计算 / 可信执行环境
- 数据使用计费

### 4. 监控中心
- 实时系统状态监控
- 异常检测与告警
- 审计日志查询
- 性能指标可视化

### 5. 分析中心
- 数据流通分析
- 用户行为分析
- AI 智能助手 (模拟大语言模型)
- 自定义报表

## 项目结构

```
energy-trusted-data-space/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic 模式
│   │   ├── utils/              # 工具函数
│   │   └── modules/            # 业务模块
│   │       ├── portal/          # 门户模块
│   │       ├── auth_center/    # 认证模块
│   │       ├── evidence_center/# 存证模块
│   │       ├── sharing_center/ # 共享模块
│   │       ├── monitor_center/ # 监控模块
│   │       └── analytics_center/# 分析模块
│   ├── alembic/                # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                # API 接口
│   │   ├── assets/             # 静态资源
│   │   ├── components/         # 组件
│   │   ├── layouts/            # 布局
│   │   ├── router/             # 路由
│   │   ├── stores/             # Pinia 状态
│   │   ├── utils/              # 工具
│   │   └── views/              # 页面
│   └── package.json
├── docker-compose.yml
└── README.md
```

## API 文档

启动后端后访问 `http://localhost:8000/docs` 查看完整 API 文档。

主要 API 端点：
- `/api/auth/login` - 用户登录
- `/api/auth/register` - 用户注册
- `/api/auth/did/create` - 创建 DID
- `/api/evidence/records` - 存证记录
- `/api/evidence/verify` - 验证存证
- `/api/sharing/assets` - 数据资产
- `/api/sharing/tasks` - 计算任务
- `/api/monitor/overview` - 监控概览
- `/api/analytics/dashboard` - 分析仪表盘

## 开发指南

### 数据库迁移
```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

### 添加新模块
1. 在 `backend/app/modules/` 下创建新模块目录
2. 实现 `router.py`、`service.py`
3. 在 `backend/app/main.py` 中注册路由
4. 在 `frontend/src/router/index.ts` 中添加前端路由
5. 创建对应的 Vue 视图组件

## 许可证

MIT License

## 联系方式

- 作者：Andre
- GitHub：https://github.com/Andre-0411
- 项目地址：https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New
