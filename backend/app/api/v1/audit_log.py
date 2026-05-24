"""
操作日志审计 API
提供操作日志记录、查询、导出等功能
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

router = APIRouter()

# ===== 数据模型 =====

class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    username: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    status: str = "success"
    module: str

class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int

# ===== Mock数据 =====

MOCK_AUDIT_LOGS = [
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 20, 10, 30, 0),
        "user_id": "admin-001",
        "username": "系统管理员",
        "action": "login",
        "resource_type": "auth",
        "resource_id": None,
        "resource_name": None,
        "details": "管理员登录系统",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "认证模块"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 20, 10, 15, 0),
        "user_id": "user-001",
        "username": "张三",
        "action": "create",
        "resource_type": "data_source",
        "resource_id": "ds-001",
        "resource_name": "电网运行数据源",
        "details": "创建新的数据源连接",
        "ip_address": "192.168.1.101",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "数据中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 20, 9, 45, 0),
        "user_id": "user-002",
        "username": "李四",
        "action": "submit",
        "resource_type": "compute_task",
        "resource_id": "task-001",
        "resource_name": "新能源发电功率预测",
        "details": "提交计算任务",
        "ip_address": "192.168.1.102",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "计算中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 20, 9, 30, 0),
        "user_id": "admin-001",
        "username": "系统管理员",
        "action": "update",
        "resource_type": "security_policy",
        "resource_id": "policy-001",
        "resource_name": "访问控制策略",
        "details": "更新安全策略配置",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "安全中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 20, 9, 0, 0),
        "user_id": "user-003",
        "username": "王五",
        "action": "download",
        "resource_type": "data_asset",
        "resource_id": "asset-001",
        "resource_name": "电力负荷数据集",
        "details": "下载数据资产",
        "ip_address": "192.168.1.103",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "数据中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 19, 17, 30, 0),
        "user_id": "user-001",
        "username": "张三",
        "action": "apply",
        "resource_type": "data_access",
        "resource_id": "access-001",
        "resource_name": "电网运行数据集2026Q1",
        "details": "申请数据访问权限",
        "ip_address": "192.168.1.101",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "pending",
        "module": "数据中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 19, 16, 0, 0),
        "user_id": "admin-001",
        "username": "系统管理员",
        "action": "approve",
        "resource_type": "data_access",
        "resource_id": "access-001",
        "resource_name": "电网运行数据集2026Q1",
        "details": "审批通过数据访问申请",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "数据中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 19, 14, 0, 0),
        "user_id": "user-002",
        "username": "李四",
        "action": "query",
        "resource_type": "blockchain",
        "resource_id": "tx-001",
        "resource_name": "区块链存证记录",
        "details": "查询区块链存证",
        "ip_address": "192.168.1.102",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "区块链中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 19, 11, 0, 0),
        "user_id": "operator-001",
        "username": "运维工程师",
        "action": "deploy",
        "resource_type": "service",
        "resource_id": "svc-001",
        "resource_name": "数据查询服务",
        "details": "部署服务新版本 v2.1.0",
        "ip_address": "192.168.1.104",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "运营中心"
    },
    {
        "id": str(uuid.uuid4()),
        "timestamp": datetime(2026, 5, 19, 10, 0, 0),
        "user_id": "user-003",
        "username": "王五",
        "action": "export",
        "resource_type": "report",
        "resource_id": "report-001",
        "resource_name": "月度运营报告",
        "details": "导出运营报告",
        "ip_address": "192.168.1.103",
        "user_agent": "Mozilla/5.0 Windows NT 10.0; Win64; x64",
        "status": "success",
        "module": "运营中心"
    },
]

# ===== API端点 =====

@router.get("/", summary="获取操作日志列表")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    resource_type: Optional[str] = Query(None, description="资源类型筛选"),
    module: Optional[str] = Query(None, description="模块筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
):
    """获取操作日志列表，支持分页和多条件筛选"""
    filtered = MOCK_AUDIT_LOGS.copy()
    
    if user_id:
        filtered = [log for log in filtered if log["user_id"] == user_id]
    if action:
        filtered = [log for log in filtered if log["action"] == action]
    if resource_type:
        filtered = [log for log in filtered if log["resource_type"] == resource_type]
    if module:
        filtered = [log for log in filtered if log["module"] == module]
    if status:
        filtered = [log for log in filtered if log["status"] == status]
    if keyword:
        keyword_lower = keyword.lower()
        filtered = [log for log in filtered if 
                   keyword_lower in log.get("details", "").lower() or 
                   keyword_lower in log.get("resource_name", "").lower() or
                   keyword_lower in log.get("username", "").lower()]
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }

@router.get("/actions", summary="获取操作类型列表")
async def get_action_types():
    """获取所有操作类型"""
    actions = [
        {"value": "login", "label": "登录"},
        {"value": "logout", "label": "登出"},
        {"value": "create", "label": "创建"},
        {"value": "update", "label": "更新"},
        {"value": "delete", "label": "删除"},
        {"value": "query", "label": "查询"},
        {"value": "download", "label": "下载"},
        {"value": "upload", "label": "上传"},
        {"value": "submit", "label": "提交"},
        {"value": "approve", "label": "审批"},
        {"value": "reject", "label": "拒绝"},
        {"value": "export", "label": "导出"},
        {"value": "deploy", "label": "部署"},
        {"value": "apply", "label": "申请"},
    ]
    return {"code": 0, "message": "success", "data": actions}

@router.get("/resource-types", summary="获取资源类型列表")
async def get_resource_types():
    """获取所有资源类型"""
    types = [
        {"value": "auth", "label": "认证"},
        {"value": "data_source", "label": "数据源"},
        {"value": "data_asset", "label": "数据资产"},
        {"value": "data_access", "label": "数据访问"},
        {"value": "compute_task", "label": "计算任务"},
        {"value": "blockchain", "label": "区块链"},
        {"value": "security_policy", "label": "安全策略"},
        {"value": "service", "label": "服务"},
        {"value": "report", "label": "报告"},
        {"value": "user", "label": "用户"},
        {"value": "config", "label": "配置"},
    ]
    return {"code": 0, "message": "success", "data": types}

@router.get("/modules", summary="获取模块列表")
async def get_modules():
    """获取所有模块"""
    modules = [
        {"value": "认证模块", "label": "认证模块"},
        {"value": "数据中心", "label": "数据中心"},
        {"value": "计算中心", "label": "计算中心"},
        {"value": "区块链中心", "label": "区块链中心"},
        {"value": "运营中心", "label": "运营中心"},
        {"value": "安全中心", "label": "安全中心"},
        {"value": "门户", "label": "门户"},
    ]
    return {"code": 0, "message": "success", "data": modules}

@router.get("/statistics", summary="获取日志统计")
async def get_log_statistics():
    """获取操作日志统计数据"""
    # 按操作类型统计
    action_stats = {}
    for log in MOCK_AUDIT_LOGS:
        action = log["action"]
        action_stats[action] = action_stats.get(action, 0) + 1
    
    # 按模块统计
    module_stats = {}
    for log in MOCK_AUDIT_LOGS:
        module = log["module"]
        module_stats[module] = module_stats.get(module, 0) + 1
    
    # 按状态统计
    status_stats = {}
    for log in MOCK_AUDIT_LOGS:
        status = log["status"]
        status_stats[status] = status_stats.get(status, 0) + 1
    
    # 今日操作数
    today = datetime.now().date()
    today_count = len([log for log in MOCK_AUDIT_LOGS if log["timestamp"].date() == today])
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_logs": len(MOCK_AUDIT_LOGS),
            "today_count": today_count,
            "action_stats": action_stats,
            "module_stats": module_stats,
            "status_stats": status_stats
        }
    }

@router.get("/{log_id}", summary="获取日志详情")
async def get_audit_log(log_id: str):
    """获取单条操作日志详情"""
    for log in MOCK_AUDIT_LOGS:
        if log["id"] == log_id:
            return {"code": 0, "message": "success", "data": log}
    raise HTTPException(status_code=404, detail="日志不存在")

@router.post("/export", summary="导出操作日志")
async def export_audit_logs(
    format: str = Query("csv", description="导出格式: csv/json"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    module: Optional[str] = Query(None, description="模块筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
):
    """导出操作日志"""
    filtered = MOCK_AUDIT_LOGS.copy()
    
    if user_id:
        filtered = [log for log in filtered if log["user_id"] == user_id]
    if action:
        filtered = [log for log in filtered if log["action"] == action]
    if module:
        filtered = [log for log in filtered if log["module"] == module]
    
    # 模拟导出
    return {
        "code": 0,
        "message": f"导出成功，共 {len(filtered)} 条记录",
        "data": {
            "format": format,
            "count": len(filtered),
            "download_url": f"/api/v1/audit-logs/download/{uuid.uuid4()}.{format}"
        }
    }
