#!/bin/bash
# =============================================================================
# Energy Trusted Data Space - Auto Restart Script
# Generated: 2024-01-15T00:00:00+00:00
# Description: 检查服务状态并在必要时重启
#
# 使用方式:
#   chmod +x scripts/auto_restart.sh
#   ./scripts/auto_restart.sh
#
# 部署到 crontab:
#   */5 * * * * /path/to/scripts/auto_restart.sh >> /var/log/energy-tds/auto_restart.log 2>&1
# =============================================================================

set -euo pipefail

# ==================== 配置 ====================

LOG_FILE="${LOG_FILE:-/var/log/energy-tds/auto_restart.log}"
MAX_RETRIES=3
RETRY_INTERVAL=10
HEALTH_CHECK_TIMEOUT=5

# 服务配置
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
BACKEND_HEALTH_URL="${BACKEND_URL}/health"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# ==================== 工具函数 ====================

log() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    echo "${timestamp} [RESTART] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "${timestamp} [RESTART] $1"
}

log_error() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    echo "${timestamp} [ERROR] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "${timestamp} [ERROR] $1"
}

log_success() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    echo "${timestamp} [SUCCESS] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "${timestamp} [SUCCESS] $1"
}

# ==================== 健康检查函数 ====================

check_service() {
    local service_name="$1"
    local check_url="$2"

    response=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$HEALTH_CHECK_TIMEOUT" "$check_url" 2>/dev/null || echo "000")
    if [ "$response" = "200" ]; then
        log_success "$service_name health check passed (HTTP $response)"
        return 0
    else
        log_error "$service_name health check failed (HTTP $response)"
        return 1
    fi
}

check_postgresql() {
    if command -v pg_isready &>/dev/null; then
        if pg_isready -h "$PG_HOST" -p "$PG_PORT" -q 2>/dev/null; then
            log_success "PostgreSQL health check passed"
            return 0
        else
            log_error "PostgreSQL health check failed"
            return 1
        fi
    else
        log "pg_isready not found, skipping PostgreSQL check"
        return 0
    fi
}

check_redis() {
    if command -v redis-cli &>/dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q "PONG"; then
            log_success "Redis health check passed"
            return 0
        else
            log_error "Redis health check failed"
            return 1
        fi
    else
        log "redis-cli not found, skipping Redis check"
        return 0
    fi
}

# ==================== 重启函数 ====================

restart_service() {
    local service_name="$1"
    local restart_cmd="$2"

    log "Attempting to restart $service_name..."
    for i in $(seq 1 $MAX_RETRIES); do
        log "Restart attempt $i/$MAX_RETRIES for $service_name"
        if eval "$restart_cmd" 2>&1; then
            log_success "$service_name restarted successfully (attempt $i)"
            return 0
        else
            log_error "Restart attempt $i failed for $service_name"
            if [ "$i" -lt "$MAX_RETRIES" ]; then
                log "Waiting ${RETRY_INTERVAL}s before next attempt..."
                sleep "$RETRY_INTERVAL"
            fi
        fi
    done
    log_error "Failed to restart $service_name after $MAX_RETRIES attempts"
    return 1
}

restart_backend() {
    local restart_cmd=""

    # 尝试多种重启方式
    if command -v systemctl &>/dev/null && systemctl is-active --quiet energy-tds 2>/dev/null; then
        restart_cmd="systemctl restart energy-tds"
    elif command -v supervisorctl &>/dev/null && supervisorctl status energy-tds 2>/dev/null; then
        restart_cmd="supervisorctl restart energy-tds"
    elif command -v docker &>/dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "energy-tds"; then
        restart_cmd="docker restart energy-tds-backend"
    else
        # 直接启动 uvicorn
        restart_cmd="cd /app && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
    fi

    restart_service "backend" "$restart_cmd"
}

restart_postgresql() {
    local restart_cmd=""

    if command -v systemctl &>/dev/null; then
        restart_cmd="systemctl restart postgresql"
    elif command -v pg_ctl &>/dev/null; then
        restart_cmd="pg_ctl restart -D /var/lib/postgresql/data"
    elif command -v docker &>/dev/null; then
        restart_cmd="docker restart energy-tds-postgres"
    else
        log_error "No PostgreSQL restart method found"
        return 1
    fi

    restart_service "postgresql" "$restart_cmd"
}

restart_redis() {
    local restart_cmd=""

    if command -v systemctl &>/dev/null; then
        restart_cmd="systemctl restart redis"
    elif command -v redis-server &>/dev/null; then
        restart_cmd="redis-server --daemonize yes"
    elif command -v docker &>/dev/null; then
        restart_cmd="docker restart energy-tds-redis"
    else
        log_error "No Redis restart method found"
        return 1
    fi

    restart_service "redis" "$restart_cmd"
}

# ==================== 主程序 ====================

main() {
    log "=========================================="
    log "Starting health check cycle"
    log "=========================================="

    local exit_code=0
    local services_checked=0
    local services_failed=0

    # 1. 检查主应用
    services_checked=$((services_checked + 1))
    if ! check_service "backend" "$BACKEND_HEALTH_URL"; then
        services_failed=$((services_failed + 1))
        log "Backend health check failed, initiating restart..."
        restart_backend || exit_code=1
    fi

    # 2. 检查 PostgreSQL
    services_checked=$((services_checked + 1))
    if ! check_postgresql; then
        services_failed=$((services_failed + 1))
        log "PostgreSQL health check failed, initiating restart..."
        restart_postgresql || exit_code=1
    fi

    # 3. 检查 Redis
    services_checked=$((services_checked + 1))
    if ! check_redis; then
        services_failed=$((services_failed + 1))
        log "Redis health check failed, initiating restart..."
        restart_redis || exit_code=1
    fi

    # 4. 二次验证（如果有服务重启）
    if [ "$services_failed" -gt 0 ]; then
        log "Waiting 15s for services to stabilize..."
        sleep 15

        log "Performing secondary verification..."
        if check_service "backend" "$BACKEND_HEALTH_URL"; then
            log_success "Backend is now healthy after restart"
        else
            log_error "Backend is still unhealthy after restart"
            exit_code=1
        fi
    fi

    log "=========================================="
    log "Health check cycle completed"
    log "Services checked: $services_checked"
    log "Services failed: $services_failed"
    log "Exit code: $exit_code"
    log "=========================================="

    return $exit_code
}

# ==================== 错误处理 ====================

trap 'log_error "Script interrupted"; exit 1' INT TERM

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# 执行主程序
main "$@"
