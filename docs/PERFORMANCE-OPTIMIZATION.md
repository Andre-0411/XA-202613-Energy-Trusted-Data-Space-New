# 能源可信数据空间 - 性能优化与监控指南

## 概述

本文档提供系统性能优化策略和监控配置指南，确保系统在高并发场景下的稳定运行。

## 1. 性能优化策略

### 1.1 数据库优化

#### PostgreSQL 优化
```sql
-- 创建索引
CREATE INDEX idx_data_assets_category ON data_assets(category);
CREATE INDEX idx_data_assets_status ON data_assets(status);
CREATE INDEX idx_data_assets_owner_id ON data_assets(owner_id);
CREATE INDEX idx_data_assets_created_at ON data_assets(created_at);

-- 复合索引
CREATE INDEX idx_data_assets_status_category ON data_assets(status, category);

-- 分区表（大数据量场景）
CREATE TABLE data_assets_2024 PARTITION OF data_assets
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### 查询优化
```python
# 使用 SQLAlchemy 的 selectinload 避免 N+1 查询
from sqlalchemy.orm import selectinload

query = select(DataAsset).options(
    selectinload(DataAsset.source),
    selectinload(DataAsset.owner)
).where(DataAsset.status == "published")
```

#### 连接池配置
```python
# database.py 中的连接池配置
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # 连接池大小
    max_overflow=10,       # 最大溢出连接数
    pool_timeout=30,       # 获取连接超时时间
    pool_recycle=1800,     # 连接回收时间（秒）
    pool_pre_ping=True,    # 使用前检查连接健康
)
```

### 1.2 Redis 缓存优化

#### 缓存策略
```python
# 热点数据缓存
import redis.asyncio as redis

redis_client = redis.from_url(REDIS_URL)

# 缓存数据资产列表
async def get_cached_assets(page: int, page_size: int):
    cache_key = f"assets:list:{page}:{page_size}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # 查询数据库
    assets = await db.execute(select(DataAsset).offset((page-1)*page_size).limit(page_size))

    # 缓存结果（5分钟过期）
    await redis_client.setex(cache_key, 300, json.dumps(assets))
    return assets
```

#### 缓存失效策略
```python
# 数据更新时清除相关缓存
async def invalidate_asset_cache(asset_id: str):
    # 删除单个资产缓存
    await redis_client.delete(f"asset:{asset_id}")
    # 删除列表缓存（可能包含此资产）
    keys = await redis_client.keys("assets:list:*")
    if keys:
        await redis_client.delete(*keys)
```

### 1.3 API 响应优化

#### 分页优化
```python
# 使用游标分页（大数据量场景）
async def get_assets_cursor(cursor: Optional[str] = None, limit: int = 20):
    query = select(DataAsset).order_by(DataAsset.id)

    if cursor:
        query = query.where(DataAsset.id > cursor)

    query = query.limit(limit + 1)  # 多取一条判断是否有下一页
    result = await db.execute(query)
    assets = result.scalars().all()

    has_next = len(assets) > limit
    if has_next:
        assets = assets[:limit]

    return {
        "items": assets,
        "next_cursor": str(assets[-1].id) if has_next else None,
        "has_next": has_next
    }
```

#### 响应压缩
```python
# 启用 Gzip 压缩
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 1.4 异步任务优化

#### 后台任务
```python
from fastapi import BackgroundTasks

async def create_asset_with_background_tasks(
    request: DataAssetCreate,
    background_tasks: BackgroundTasks
):
    # 创建资产
    asset = await create_asset(request)

    # 异步执行分类分级
    background_tasks.add_task(classify_asset, asset.id)

    # 异步执行存证
    background_tasks.add_task(create_evidence, asset.id)

    return asset
```

#### 并发控制
```python
import asyncio

# 限制并发任务数
semaphore = asyncio.Semaphore(10)

async def limited_task(task_func):
    async with semaphore:
        return await task_func()
```

### 1.5 WebSocket 优化

#### 连接池管理
```python
class OptimizedWebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.channels: Dict[str, Set[str]] = defaultdict(set)
        self.message_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    async def broadcast_optimized(self, channel: str, message: dict):
        """批量发送消息"""
        if channel not in self.channels:
            return

        # 准备消息
        ws_message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            channel=channel,
            data=message
        )

        # 批量发送
        tasks = []
        for conn_id in self.channels[channel]:
            if conn_id in self.connections:
                tasks.append(self._send_safe(conn_id, ws_message))

        # 并发执行，忽略失败
        await asyncio.gather(*tasks, return_exceptions=True)
```

## 2. 监控配置

### 2.1 Prometheus 指标

#### 应用指标
```python
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 活跃连接数
ACTIVE_CONNECTIONS = Gauge(
    'websocket_active_connections',
    'Number of active WebSocket connections'
)

# 数据库查询延迟
DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['operation']
)
```

#### 中间件集成
```python
from starlette.middleware.base import BaseHTTPMiddleware
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        # 记录指标
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(time.time() - start_time)

        return response

app.add_middleware(MetricsMiddleware)
```

### 2.2 Grafana 仪表板

#### 系统概览仪表板
```json
{
  "dashboard": {
    "title": "能源可信数据空间 - 系统概览",
    "panels": [
      {
        "title": "请求速率",
        "targets": [{"expr": "rate(http_requests_total[5m])"}]
      },
      {
        "title": "响应时间 P95",
        "targets": [{"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"}]
      },
      {
        "title": "错误率",
        "targets": [{"expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])"}]
      },
      {
        "title": "活跃 WebSocket 连接",
        "targets": [{"expr": "websocket_active_connections"}]
      }
    ]
  }
}
```

### 2.3 日志监控

#### 结构化日志
```python
import structlog

logger = structlog.get_logger()

# 记录请求
logger.info(
    "api_request",
    method=request.method,
    path=request.url.path,
    status=response.status_code,
    duration=duration,
    user_id=user_id
)

# 记录错误
logger.error(
    "api_error",
    error=str(e),
    traceback=traceback.format_exc(),
    request_id=request_id
)
```

#### 日志级别配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## 3. 性能基准

### 3.1 响应时间目标

| 端点 | 目标响应时间 (P95) | 当前响应时间 |
|------|-------------------|-------------|
| GET /api/v1/data/assets | < 200ms | - |
| POST /api/v1/compute/tasks | < 500ms | - |
| GET /api/v1/blockchain/evidence | < 300ms | - |
| WebSocket 消息推送 | < 100ms | - |

### 3.2 并发目标

| 场景 | 目标并发数 | 当前并发数 |
|------|-----------|-----------|
| API 请求 | 1000 QPS | - |
| WebSocket 连接 | 5000 | - |
| 数据库连接 | 100 | - |

## 4. 性能测试

### 4.1 负载测试脚本

```python
# locustfile.py
from locust import HttpUser, task, between

class EnergyTDSUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 登录获取 token
        response = self.client.post("/api/v1/auth/login", json={
            "auth_type": "password",
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_assets(self):
        self.client.get(
            "/api/v1/data/assets?page=1&page_size=20",
            headers=self.headers
        )

    @task(2)
    def get_asset_detail(self):
        self.client.get(
            "/api/v1/data/assets/1",
            headers=self.headers
        )

    @task(1)
    def create_task(self):
        self.client.post(
            "/api/v1/compute/tasks",
            json={
                "name": "性能测试任务",
                "type": "federated_learning",
                "algorithm": "horizontal_fl"
            },
            headers=self.headers
        )
```

### 4.2 运行负载测试

```bash
# 安装 locust
pip install locust

# 运行测试
locust -f locustfile.py --host=http://localhost:8000

# Web 界面
http://localhost:8089
```

## 5. 优化清单

### 5.1 数据库优化 ✅

- [x] 创建必要索引
- [x] 配置连接池
- [ ] 实施读写分离
- [ ] 配置查询缓存

### 5.2 缓存优化 ✅

- [x] 配置 Redis 缓存
- [ ] 实施缓存预热
- [ ] 配置缓存失效策略

### 5.3 API 优化 ✅

- [x] 启用响应压缩
- [x] 实施分页优化
- [ ] 配置 CDN

### 5.4 监控配置 ✅

- [x] 配置 Prometheus 指标
- [ ] 创建 Grafana 仪表板
- [ ] 配置告警规则

### 5.5 负载测试

- [ ] 创建负载测试脚本
- [ ] 运行性能基准测试
- [ ] 识别性能瓶颈

## 6. 故障排查

### 6.1 常见性能问题

#### 数据库连接池耗尽
```python
# 检查连接池状态
print(engine.pool.status())

# 增加连接池大小
engine = create_async_engine(DATABASE_URL, pool_size=30)
```

#### Redis 内存溢出
```bash
# 检查 Redis 内存使用
redis-cli info memory

# 配置内存限制
redis-cli config set maxmemory 1gb
redis-cli config set maxmemory-policy allkeys-lru
```

#### WebSocket 连接泄漏
```python
# 定期清理断开的连接
async def cleanup_connections():
    while True:
        await asyncio.sleep(60)
        manager.cleanup_stale_connections()
```

### 6.2 性能分析工具

```python
# 使用 cProfile 分析
import cProfile

profiler = cProfile.Profile()
profiler.enable()

# 执行代码

profiler.disable()
profiler.print_stats(sort='cumulative')
```

## 7. 扩展性建议

### 7.1 水平扩展

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      replicas: 3
    environment:
      - WORKER_CONNECTIONS=1000
```

### 7.2 负载均衡

```nginx
# nginx.conf
upstream api_servers {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    location /api/ {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 8. 性能优化路线图

### Phase 1: 基础优化 (Week 1-2)
- 数据库索引优化
- Redis 缓存配置
- API 响应压缩

### Phase 2: 高级优化 (Week 3-4)
- 读写分离配置
- CDN 集成
- WebSocket 连接池优化

### Phase 3: 监控与测试 (Week 5-6)
- Grafana 仪表板创建
- 负载测试执行
- 性能瓶颈识别与修复

---

**文档版本**: v1.0.0
**最后更新**: 2026-05-21
**维护者**: 性能优化团队
