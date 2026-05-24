# ============================================================
# 面向能源可信数据空间 - Makefile
# ============================================================

.PHONY: dev build up down migrate seed test health clean lint

# 默认目标
.DEFAULT_GOAL := dev

# 开发环境启动（前端热更新 + 后端热重载）
dev:
	@echo "🚀 Starting development environment..."
	docker compose up -d postgres redis mongo minio emqx
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@echo "🔧 Starting backend..."
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
	@echo "🎨 Starting frontend..."
	cd frontend && npm run dev &
	@echo "✅ Development environment ready!"

# 构建所有镜像
build:
	@echo "🔨 Building Docker images..."
	docker compose build
	@echo "✅ Build complete!"

# 启动所有服务
up:
	@echo "🚀 Starting all services..."
	docker compose up -d
	@echo "✅ All services started!"
	@echo "   Frontend: http://localhost"
	@echo "   Backend:  http://localhost:8000/docs"
	@echo "   Grafana:  http://localhost:3000"

# 停止所有服务
down:
	@echo "🛑 Stopping all services..."
	docker compose down
	@echo "✅ All services stopped!"

# 运行数据库迁移
migrate:
	@echo "📦 Running database migrations..."
	cd backend && alembic upgrade head
	@echo "✅ Migrations complete!"

# 填充种子数据
seed:
	@echo "🌱 Seeding database..."
	cd backend && python -m app.scripts.seed
	@echo "✅ Seed data complete!"

# 运行测试
test:
	@echo "🧪 Running tests..."
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing
	cd frontend && npm test
	@echo "✅ Tests complete!"

# 健康检查
health:
	@echo "🏥 Checking service health..."
	@curl -sf http://localhost:8000/health | python -m json.tool || echo "❌ Backend unhealthy"
	@curl -sf http://localhost:80/ > /dev/null && echo "✅ Frontend OK" || echo "❌ Frontend unhealthy"
	@curl -sf http://localhost:3000/api/health > /dev/null && echo "✅ Grafana OK" || echo "❌ Grafana unhealthy"
	@echo "✅ Health check complete!"

# 代码检查
lint:
	@echo "🔍 Linting code..."
	cd backend && python -m ruff check app/
	cd frontend && npm run lint
	@echo "✅ Lint complete!"

# 清理
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v --remove-orphans
	rm -rf frontend/dist frontend/node_modules
	rm -rf backend/__pycache__ backend/.pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete!"
