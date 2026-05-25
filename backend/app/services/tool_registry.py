"""
AI Agent 动态工具注册表
======================
自动扫描 FastAPI 路由，根据 API 端点的请求/响应模型自动生成 LangChain 工具。
生成的工具记录在注册表中，后续可直接调用。

功能：
1. 扫描所有 API 端点（POST/PUT/DELETE）
2. 从 Pydantic 模型提取参数 schema
3. 自动生成 LangChain @tool 函数
4. 按模块分组管理工具
5. 支持权限检查
"""
import json
import logging
import inspect
import importlib
from typing import Optional, Callable, Any
from functools import lru_cache

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ==================== 工具注册表 ====================

_tool_registry: dict[str, dict] = {}  # {tool_name: {func, module, path, method, description, params}}
_module_tools: dict[str, list] = {}   # {module_name: [tool_names]}
_initialized = False


# ==================== API 扫描 ====================

def _scan_api_routes(app=None) -> list[dict]:
    """扫描 FastAPI 应用的所有路由"""
    if app is None:
        try:
            from app.main import app
        except ImportError:
            logger.warning("Cannot import FastAPI app, skipping route scan")
            return []

    routes = []
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue

        for method in route.methods:
            if method not in ("POST", "PUT", "DELETE"):
                continue

            # 跳过通用端点
            path = route.path
            if any(skip in path for skip in ["/health", "/docs", "/openapi", "/redoc"]):
                continue

            # 提取模块名
            module = _extract_module(path)

            # 提取函数信息
            endpoint = route.endpoint
            func_name = endpoint.__name__ if hasattr(endpoint, "__name__") else str(endpoint)
            docstring = inspect.getdoc(endpoint) or ""

            # 提取请求体模型
            params = _extract_params(endpoint)

            routes.append({
                "path": path,
                "method": method,
                "module": module,
                "func_name": func_name,
                "docstring": docstring,
                "params": params,
                "endpoint": endpoint,
                "summary": getattr(route, "summary", "") or func_name.replace("_", " ").title(),
            })

    return routes


def _extract_module(path: str) -> str:
    """从路径提取模块名: /api/v1/data/assets → data"""
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return "other"


def _extract_params(endpoint: Callable) -> list[dict]:
    """从端点函数提取参数信息"""
    params = []
    sig = inspect.signature(endpoint)

    for name, param in sig.parameters.items():
        if name in ("db", "user", "request"):
            continue

        param_info = {
            "name": name,
            "type": _type_to_str(param.annotation),
            "required": param.default == inspect.Parameter.empty,
            "default": None if param.default == inspect.Parameter.empty else param.default,
        }

        # 尝试从 Pydantic 模型提取字段
        if hasattr(param.annotation, "model_fields"):
            param_info["fields"] = _extract_pydantic_fields(param.annotation)
            param_info["is_model"] = True
        else:
            param_info["is_model"] = False

        params.append(param_info)

    return params


def _extract_pydantic_fields(model_class) -> list[dict]:
    """从 Pydantic 模型提取字段"""
    fields = []
    for name, field in model_class.model_fields.items():
        fields.append({
            "name": name,
            "type": _type_to_str(field.annotation),
            "required": field.is_required(),
            "default": field.default if not field.is_required() else None,
            "description": field.description or "",
        })
    return fields


def _type_to_str(type_hint) -> str:
    """将类型注解转为字符串"""
    if type_hint == inspect.Parameter.empty:
        return "any"
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__
    return str(type_hint)


# ==================== 工具生成 ====================

def _sanitize_name(name: str) -> str:
    """清理名称，将连字符替换为下划线（Python函数名不能含连字符）"""
    return name.replace("-", "_")


def _generate_tool_name(module: str, func_name: str, method: str) -> str:
    """生成工具名称: create_data_asset, update_contract 等"""
    # 清理模块名中的连字符
    module = _sanitize_name(module)
    func_name = _sanitize_name(func_name)

    # 提取动词
    verb_map = {"POST": "create", "PUT": "update", "DELETE": "delete"}
    verb = verb_map.get(method, method.lower())

    # 清理函数名
    clean_name = func_name
    for prefix in ["create_", "update_", "delete_", "add_", "submit_", "list_", "get_"]:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break

    # 如果函数名已有动词，直接使用
    if any(func_name.startswith(v) for v in ["create", "update", "delete", "add", "submit"]):
        return f"{module}_{func_name}"

    return f"{verb}_{module}_{clean_name}"


def _generate_tool_description(route_info: dict) -> str:
    """生成工具描述"""
    doc = route_info["docstring"]
    summary = route_info["summary"]
    method = route_info["method"]
    path = route_info["path"]

    desc = doc.split("\n")[0] if doc else summary
    desc = desc.strip()

    if not desc:
        method_verb = {"POST": "创建", "PUT": "更新", "DELETE": "删除"}.get(method, method)
        desc = f"{method_verb} {route_info['module']} 资源"

    return f"{desc}。API: {method} {path}"


def _create_dynamic_tool(route_info: dict) -> Callable:
    """动态创建 LangChain 工具函数"""
    tool_name = _generate_tool_name(route_info["module"], route_info["func_name"], route_info["method"])
    tool_desc = _generate_tool_description(route_info)
    params = route_info["params"]

    # 构建参数字符串 — 将所有非基础类型统一降级为 str，避免 exec namespace 中缺少类型引用
    _SAFE_TYPES = {"str", "int", "float", "bool", "list", "dict", "any"}
    param_parts = []
    for p in params:
        if p.get("is_model"):
            # Pydantic 模型参数 → 转为 JSON 字符串
            param_parts.append(f'{p["name"]}: str = "{{}}"')
        else:
            # 将未知/复杂类型注解降级为 str，避免 NameError
            raw_type = p["type"].split("[")[0].split("|")[0].strip()  # 取主类型
            type_str = raw_type if raw_type in _SAFE_TYPES else "str"
            if p["required"]:
                param_parts.append(f'{p["name"]}: {type_str}')
            else:
                default = '""' if type_str == "str" else "None"
                param_parts.append(f'{p["name"]}: {type_str} = {default}')

    # 生成工具函数代码
    func_code = f'''
@tool
async def {tool_name}({", ".join(param_parts)}) -> str:
    """{tool_desc}"""
    import json as _json
    from app.database import AsyncSessionLocal

    # 构建请求数据
    request_data = {{}}
'''

    # 添加参数处理
    for p in params:
        if p.get("is_model"):
            func_code += f'''
    try:
        request_data["{p["name"]}"] = _json.loads({p["name"]})
    except Exception:
        request_data["{p["name"]}"] = {{}}
'''
        else:
            func_code += f'''
    if {p["name"]} is not None:
        request_data["{p["name"]}"] = {p["name"]}
'''

    # 添加 API 调用 — 清理模块名中的连字符
    safe_module = _sanitize_name(route_info["module"])
    func_code += f'''
    # 调用内部服务
    try:
        async with AsyncSessionLocal() as session:
            from app.services import {safe_module}_service
            service_func = getattr({safe_module}_service, "{route_info["func_name"]}", None)
            if service_func:
                result = await service_func(db=session, **request_data)
                return _json.dumps({{"success": True, "result": result}}, ensure_ascii=False, default=str)
            else:
                return _json.dumps({{"success": False, "error": "服务函数未找到"}}, ensure_ascii=False)
    except Exception as e:
        return _json.dumps({{"success": False, "error": str(e)}}, ensure_ascii=False)
'''

    # 执行代码创建函数 — 提供完整的 exec namespace 以避免 NameError
    from langchain_core.tools import tool as _tool_decorator
    from typing import Optional, List, Dict, Any, Union
    from fastapi import BackgroundTasks
    namespace = {
        "tool": _tool_decorator,
        "Optional": Optional,
        "List": List,
        "Dict": Dict,
        "Any": Any,
        "Union": Union,
        "BackgroundTasks": BackgroundTasks,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    try:
        exec(func_code, namespace)
    except SyntaxError as e:
        logger.error(f"Syntax error generating tool '{tool_name}': {e}\nCode:\n{func_code}")
        raise
    return namespace[tool_name]


# ==================== 注册表管理 ====================

def register_tool(name: str, func: Callable, module: str, route_info: dict):
    """注册工具到注册表"""
    _tool_registry[name] = {
        "func": func,
        "module": module,
        "path": route_info["path"],
        "method": route_info["method"],
        "description": _generate_tool_description(route_info),
        "params": route_info["params"],
        "auto_generated": True,
    }

    if module not in _module_tools:
        _module_tools[module] = []
    _module_tools[module].append(name)

    logger.info(f"Registered tool: {name} ({route_info['method']} {route_info['path']})")


def get_tool(name: str) -> Optional[Callable]:
    """获取注册的工具"""
    entry = _tool_registry.get(name)
    return entry["func"] if entry else None


def get_all_tools() -> dict[str, dict]:
    """获取所有注册的工具"""
    return _tool_registry.copy()


def get_module_tools(module: str) -> list[dict]:
    """获取指定模块的所有工具"""
    names = _module_tools.get(module, [])
    return [{"name": n, **_tool_registry[n]} for n in names if n in _tool_registry]


def list_modules() -> list[str]:
    """列出所有模块"""
    return list(_module_tools.keys())


def get_tools_for_agent(agent_type: str, user_permissions: list[str] = None) -> list[Callable]:
    """根据 Agent 类型和用户权限获取可用工具"""
    # Agent 类型与模块映射
    agent_modules = {
        "query": ["data", "catalog", "metadata", "quality", "market", "system", "org", "product", "revenue"],
        "trade": ["product", "contract", "demand", "subscription", "market", "blockchain", "system", "revenue"],
        "security": ["security", "evidence", "audit", "policy", "blockchain", "system", "compute"],
        "dispatch": ["compute", "dag", "sandbox", "cluster", "data", "system", "org", "quality"],
    }

    modules = agent_modules.get(agent_type, [])
    tools = []

    for module in modules:
        for name, entry in _tool_registry.items():
            if entry["module"] == module:
                tools.append(entry["func"])

    return tools


# ==================== 手动查询工具注册 ====================

def _register_manual_query_tools():
    """注册手动查询工具 — Agent 需要这些工具来读取数据（支持 GET 查询类）"""
    from langchain_core.tools import tool as _tool_decorator

    # 跳过已注册的手动工具
    manual_names = {"list_data_assets", "list_data_sources", "list_compute_tasks",
                    "list_products", "get_system_stats", "query_blockchain_evidence",
                    "query_security_threats", "list_catalog_registrations", "list_organizations"}
    if any(n in _tool_registry for n in manual_names):
        return

    @tool
    async def list_data_assets(category: str = "", status: str = "", limit: int = 10) -> str:
        """查询数据资产列表。可按分类(category: 发电/用电/调度/市场/设备状态/地理信息)和状态(status: active/inactive)筛选。返回数据资产的名称、分类、状态和记录数。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.data_asset import DataAsset
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(DataAsset)
            if category:
                query = query.where(DataAsset.category.ilike(f"%{category}%"))
            if status:
                query = query.where(DataAsset.status == status)
            query = query.order_by(DataAsset.created_at.desc()).limit(limit)
            result = await session.execute(query)
            assets = result.scalars().all()
            return _json.dumps({
                "total": len(assets),
                "assets": [{"id": str(a.id), "name": a.name, "category": a.category,
                            "status": a.status, "record_count": a.record_count}
                           for a in assets],
            }, ensure_ascii=False)

    @tool
    async def list_data_sources(protocol_type: str = "", limit: int = 10) -> str:
        """查询已注册的数据源列表。可按协议类型(protocol_type: DLMS/Modbus/HTTP/MQTT/OPC-UA/WebSocket)筛选。返回数据源的名称、协议类型和连接状态。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.connector import DataSource
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(DataSource)
            if protocol_type:
                query = query.where(DataSource.protocol_type.ilike(f"%{protocol_type}%"))
            query = query.order_by(DataSource.created_at.desc()).limit(limit)
            result = await session.execute(query)
            sources = result.scalars().all()
            return _json.dumps({
                "total": len(sources),
                "sources": [{"id": str(s.id), "name": s.name, "protocol_type": s.protocol_type,
                             "status": s.status} for s in sources],
            }, ensure_ascii=False)

    @tool
    async def list_compute_tasks(task_type: str = "", status: str = "", limit: int = 10) -> str:
        """查询可信计算任务列表。可按任务类型(task_type: FL联邦学习/MPC安全多方计算/TEE可信执行环境/HE同态加密/DP差分隐私/Sandbox沙箱)和状态筛选。返回任务名称、类型、状态和进度。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.compute_task import ComputeTask
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(ComputeTask)
            if task_type:
                query = query.where(ComputeTask.task_type == task_type)
            if status:
                query = query.where(ComputeTask.status == status)
            query = query.order_by(ComputeTask.created_at.desc()).limit(limit)
            result = await session.execute(query)
            tasks = result.scalars().all()
            return _json.dumps({
                "total": len(tasks),
                "tasks": [{"id": str(t.id), "name": t.name, "task_type": t.task_type,
                           "status": t.status, "progress": t.progress} for t in tasks],
            }, ensure_ascii=False)

    @tool
    async def list_products(product_type: str = "", status: str = "published", limit: int = 10) -> str:
        """查询数据产品市场列表。可按产品类型(product_type)和状态(status: published/draft/archived)筛选。返回产品名称、类型、定价和状态。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.product import DataProduct
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(DataProduct)
            if product_type:
                query = query.where(DataProduct.product_type.ilike(f"%{product_type}%"))
            if status:
                query = query.where(DataProduct.status == status)
            query = query.order_by(DataProduct.created_at.desc()).limit(limit)
            result = await session.execute(query)
            products = result.scalars().all()
            return _json.dumps({
                "total": len(products),
                "products": [{"id": str(p.id), "name": p.name, "product_type": p.product_type,
                              "pricing": p.pricing, "status": p.status} for p in products],
            }, ensure_ascii=False)

    @tool
    async def get_system_stats() -> str:
        """获取能源可信数据空间系统整体运行统计。返回数据资产总数、计算任务总数、数据产品总数及系统运行状态。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.data_asset import DataAsset
        from app.models.compute_task import ComputeTask
        from app.models.product import DataProduct
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            assets_count = (await session.execute(select(func.count(DataAsset.id)))).scalar() or 0
            tasks_count = (await session.execute(select(func.count(ComputeTask.id)))).scalar() or 0
            products_count = (await session.execute(select(func.count(DataProduct.id)))).scalar() or 0

            return _json.dumps({
                "data_assets_count": assets_count,
                "compute_tasks_count": tasks_count,
                "data_products_count": products_count,
                "system_status": "running",
            }, ensure_ascii=False)

    @tool
    async def query_blockchain_evidence(status: str = "", limit: int = 10) -> str:
        """查询区块链存证记录。可按状态(status: confirmed/pending/failed)筛选。返回存证ID、交易哈希、存证类型和时间。用于验证数据完整性和溯源。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.blockchain import EvidenceChain
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(EvidenceChain)
            if status:
                query = query.where(EvidenceChain.status == status)
            query = query.order_by(EvidenceChain.created_at.desc()).limit(limit)
            result = await session.execute(query)
            evidences = result.scalars().all()
            return _json.dumps({
                "total": len(evidences),
                "evidences": [{"id": str(e.id), "tx_hash": e.tx_hash, "node_type": e.node_type,
                               "status": e.status, "created_at": e.created_at.isoformat() if e.created_at else None}
                              for e in evidences],
            }, ensure_ascii=False)

    @tool
    async def query_security_threats(severity: str = "", status: str = "", limit: int = 10) -> str:
        """查询安全威胁事件。可按严重程度(severity: critical/high/medium/low/info)和状态(status: detected/investigating/resolved/dismissed)筛选。返回威胁类型、严重程度、状态和描述。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.security import ThreatEvent
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(ThreatEvent)
            if severity:
                query = query.where(ThreatEvent.severity == severity)
            if status:
                query = query.where(ThreatEvent.status == status)
            query = query.order_by(ThreatEvent.created_at.desc()).limit(limit)
            result = await session.execute(query)
            threats = result.scalars().all()
            return _json.dumps({
                "total": len(threats),
                "threats": [{"id": str(t.id), "threat_type": t.threat_type, "severity": t.severity,
                             "status": t.status, "description": (t.description or "")[:200]}
                            for t in threats],
            }, ensure_ascii=False)

    @tool
    async def list_catalog_registrations(catalog_type: str = "", security_level: str = "", status: str = "", limit: int = 10) -> str:
        """查询数据目录登记列表。可按目录类型(catalog_type: api/file/database/service/model)、安全等级(security_level: public/internal/confidential/secret)和状态筛选。返回目录名称、类型、安全等级和可见性。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.catalog import CatalogRegistration
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(CatalogRegistration)
            if catalog_type:
                query = query.where(CatalogRegistration.catalog_type == catalog_type)
            if security_level:
                query = query.where(CatalogRegistration.security_level == security_level)
            if status:
                query = query.where(CatalogRegistration.status == status)
            query = query.order_by(CatalogRegistration.created_at.desc()).limit(limit)
            result = await session.execute(query)
            catalogs = result.scalars().all()
            return _json.dumps({
                "total": len(catalogs),
                "catalogs": [{"id": str(c.id), "name": c.name, "catalog_type": c.catalog_type,
                              "security_level": c.security_level, "visibility": c.visibility,
                              "status": c.status}
                             for c in catalogs],
            }, ensure_ascii=False)

    @tool
    async def list_organizations(status: str = "", limit: int = 10) -> str:
        """查询平台注册的机构组织列表。可按状态(status: active/certified/suspended)筛选。返回机构名称、统一社会信用代码和认证状态。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.user import Organization
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(Organization)
            if status:
                query = query.where(Organization.status == status)
            query = query.order_by(Organization.created_at.desc()).limit(limit)
            result = await session.execute(query)
            orgs = result.scalars().all()
            return _json.dumps({
                "total": len(orgs),
                "organizations": [{"id": str(o.id), "name": o.name,
                                   "social_credit_code": getattr(o, "social_credit_code", ""),
                                   "status": o.status}
                                  for o in orgs],
            }, ensure_ascii=False)

    # 注册手动工具
    manual_tools = {
        "list_data_assets": (list_data_assets, "data", "查询数据资产列表，支持按分类和状态筛选"),
        "list_data_sources": (list_data_sources, "data", "查询已注册数据源列表，支持按协议类型筛选"),
        "list_compute_tasks": (list_compute_tasks, "compute", "查询可信计算任务列表，支持按类型和状态筛选"),
        "list_products": (list_products, "product", "查询数据产品市场列表，支持按类型和状态筛选"),
        "get_system_stats": (get_system_stats, "system", "获取系统整体运行统计信息"),
        "query_blockchain_evidence": (query_blockchain_evidence, "blockchain", "查询区块链存证记录，验证数据完整性"),
        "query_security_threats": (query_security_threats, "security", "查询安全威胁事件，支持按严重程度筛选"),
        "list_catalog_registrations": (list_catalog_registrations, "catalog", "查询数据目录登记列表，支持多维度筛选"),
        "list_organizations": (list_organizations, "org", "查询平台注册机构组织列表"),
    }

    for name, (func_obj, module, desc) in manual_tools.items():
        _tool_registry[name] = {
            "func": func_obj,
            "module": module,
            "path": f"manual/{name}",
            "method": "GET",
            "description": desc,
            "params": [],
            "auto_generated": False,
        }
        if module not in _module_tools:
            _module_tools[module] = []
        _module_tools[module].append(name)

    logger.info(f"Registered {len(manual_tools)} manual query tools")


# ==================== 隐私计算工具注册 ====================

def _register_privacy_compute_tools():
    """注册隐私计算相关工具 — Agent 通过这些工具驱动 FL/MPC/HE/DP 任务"""
    from langchain_core.tools import tool as _tool_decorator

    privacy_names = {"create_fl_task", "create_mpc_computation", "create_he_computation",
                     "check_privacy_budget", "get_compute_task_status",
                     "get_data_quality_report", "recommend_data_products", "assess_data_value"}
    if any(n in _tool_registry for n in privacy_names):
        return

    @tool
    async def create_fl_task(name: str, algorithm: str, participants: str, description: str = "") -> str:
        """创建联邦学习训练任务。algorithm可选: lr(逻辑回归)/secureboost(安全提升树)/nn(神经网络)/fm(因子分解机)/svd(奇异值分解)/kmeans(K均值聚类)。participants为参与方ID列表的JSON字符串，至少需要2个参与方。用于多方联合建模而不泄露原始数据。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.fl_service import submit_fl_training

        try:
            participant_list = _json.loads(participants) if participants else []
        except _json.JSONDecodeError:
            return _json.dumps({"success": False, "error": "participants 必须是合法的 JSON 数组字符串"}, ensure_ascii=False)

        async with AsyncSessionLocal() as session:
            try:
                result = await submit_fl_training(
                    db=session, name=name, algorithm=algorithm,
                    participants=participant_list,
                    dataset_config={"description": description} if description else {},
                    user_id="", organization_id="",
                )
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def create_mpc_computation(protocol: str, computation_type: str, parties: str, description: str = "") -> str:
        """创建MPC安全多方计算任务。protocol可选: spdz(恶意安全)/aby3(半诚实三方)/semi_honest(半诚实两方)/malicious(恶意安全两方)。computation_type可选: addition/multiplication/comparison/aggregation。parties为参与方ID列表的JSON字符串。用于多方联合计算而不泄露各方输入数据。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.mpc_service import create_mpc_session

        try:
            party_list = _json.loads(parties) if parties else []
        except _json.JSONDecodeError:
            return _json.dumps({"success": False, "error": "parties 必须是合法的 JSON 数组字符串"}, ensure_ascii=False)

        async with AsyncSessionLocal() as session:
            try:
                result = await create_mpc_session(
                    db=session, protocol=protocol, computation_type=computation_type,
                    parties=party_list,
                    config={"description": description} if description else {},
                )
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def create_he_computation(scheme: str, operation: str, data_description: str = "") -> str:
        """创建同态加密计算任务。scheme可选: ckks(近似浮点运算，适合机器学习)/bfv(精确整数运算，适合计数聚合)。operation可选: add/multiply/negate/square/encrypt/decrypt。用于在加密数据上直接执行计算，无需解密。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.he_service import create_he_task

        async with AsyncSessionLocal() as session:
            try:
                result = await create_he_task(
                    db=session, scheme=scheme, operation=operation,
                    config={"data_description": data_description} if data_description else {},
                    user_id="", organization_id="",
                )
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def check_privacy_budget(organization_id: str = "", epsilon_budget: float = 1.0) -> str:
        """查询差分隐私预算剩余量。返回当前组织的隐私预算消耗情况（epsilon已用/总量、delta已用/总量）。当预算不足时应停止差分隐私查询以保护隐私。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.dp_service import get_privacy_budget_status

        async with AsyncSessionLocal() as session:
            try:
                result = await get_privacy_budget_status(
                    db=session, organization_id=organization_id, epsilon_budget=epsilon_budget,
                )
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def get_compute_task_status(task_id: str) -> str:
        """查询计算任务状态（联邦学习/MPC/同态加密/差分隐私等）。返回任务名称、类型、状态、进度百分比、开始时间、结束时间等信息。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.compute_task import ComputeTask
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(ComputeTask).where(ComputeTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if not task:
                    return _json.dumps({"success": False, "error": f"任务 {task_id} 不存在"}, ensure_ascii=False)
                return _json.dumps({
                    "success": True,
                    "result": {
                        "id": str(task.id), "name": task.name, "task_type": task.task_type,
                        "status": task.status, "progress": task.progress,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                    }
                }, ensure_ascii=False)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def get_data_quality_report(asset_id: str = "", min_score: float = 0.0) -> str:
        """获取数据质量报告。返回数据资产的质量评分（完整性、准确性、时效性、一致性）、质量等级（excellent/good/fair/poor）和改进建议。可按asset_id指定资产或按min_score筛选高质量数据。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.models.compliance import DataQualityReport
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            try:
                query = select(DataQualityReport)
                if asset_id:
                    import uuid as _uuid
                    query = query.where(DataQualityReport.asset_id == _uuid.UUID(asset_id))
                if min_score > 0:
                    query = query.where(DataQualityReport.overall_score >= min_score)
                query = query.order_by(DataQualityReport.created_at.desc()).limit(10)
                result = await session.execute(query)
                reports = result.scalars().all()
                return _json.dumps({
                    "success": True,
                    "result": {
                        "total": len(reports),
                        "reports": [
                            {
                                "id": str(r.id), "asset_id": str(r.asset_id),
                                "overall_score": r.overall_score,
                                "completeness": getattr(r, "completeness_score", None),
                                "accuracy": getattr(r, "accuracy_score", None),
                                "timeliness": getattr(r, "timeliness_score", None),
                                "consistency": getattr(r, "consistency_score", None),
                                "grade": getattr(r, "quality_grade", "unknown"),
                            }
                            for r in reports
                        ],
                    }
                }, ensure_ascii=False)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def recommend_data_products(user_preferences: str = "", limit: int = 5) -> str:
        """智能推荐数据产品。user_preferences为用户偏好的JSON字符串，可包含industry(行业)、data_type(数据类型)、security_level(安全等级)等字段。基于用户历史订阅和协同过滤算法推荐最相关的数据产品。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.matching_service import recommend_products

        try:
            prefs = _json.loads(user_preferences) if user_preferences else {}
        except _json.JSONDecodeError:
            prefs = {}

        async with AsyncSessionLocal() as session:
            try:
                result = await recommend_products(db=session, user_preferences=prefs, limit=limit)
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    async def assess_data_value(asset_id: str) -> str:
        """数据资产评估。评估指定数据资产的经济价值，基于数据质量(40%)和使用频次(60%)计算，返回评估得分、质量分、使用次数、预估收益区间。用于数据资产入表和定价参考。"""
        import json as _json
        from app.database import AsyncSessionLocal
        from app.services.revenue_service import assess_asset_value

        async with AsyncSessionLocal() as session:
            try:
                result = await assess_asset_value(db=session, asset_id=asset_id)
                return _json.dumps({"success": True, "result": result}, ensure_ascii=False, default=str)
            except Exception as e:
                return _json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    # 注册隐私计算工具
    privacy_tools = {
        "create_fl_task": (create_fl_task, "compute", "创建联邦学习训练任务，支持多种FL算法"),
        "create_mpc_computation": (create_mpc_computation, "compute", "创建MPC安全多方计算任务"),
        "create_he_computation": (create_he_computation, "compute", "创建同态加密计算任务"),
        "check_privacy_budget": (check_privacy_budget, "compute", "查询差分隐私预算剩余量"),
        "get_compute_task_status": (get_compute_task_status, "compute", "查询计算任务状态"),
        "get_data_quality_report": (get_data_quality_report, "quality", "获取数据质量报告"),
        "recommend_data_products": (recommend_data_products, "product", "智能推荐数据产品"),
        "assess_data_value": (assess_data_value, "revenue", "数据资产评估"),
    }

    for name, (func_obj, module, desc) in privacy_tools.items():
        _tool_registry[name] = {
            "func": func_obj,
            "module": module,
            "path": f"manual/{name}",
            "method": "TOOL",
            "description": desc,
            "params": [],
            "auto_generated": False,
        }
        if module not in _module_tools:
            _module_tools[module] = []
        _module_tools[module].append(name)

    logger.info(f"Registered {len(privacy_tools)} privacy compute tools")


# ==================== 初始化 ====================

def initialize_tools(app=None, force: bool = False):
    """初始化工具注册表（扫描 API 路由并生成工具）"""
    global _initialized

    if _initialized and not force:
        logger.info("Tool registry already initialized")
        return

    logger.info("Initializing tool registry...")

    routes = _scan_api_routes(app)
    logger.info(f"Found {len(routes)} API routes")

    # 过滤出可写的操作（POST/PUT/DELETE）
    write_routes = [r for r in routes if r["method"] in ("POST", "PUT", "DELETE")]
    logger.info(f"Found {len(write_routes)} write operations")

    # 为每个路由生成工具
    registered = 0
    for route_info in write_routes:
        try:
            tool_name = _generate_tool_name(route_info["module"], route_info["func_name"], route_info["method"])

            # 跳过已存在的手动注册工具
            if tool_name in _tool_registry:
                continue

            # 生成工具函数
            tool_func = _create_dynamic_tool(route_info)
            register_tool(tool_name, tool_func, route_info["module"], route_info)
            registered += 1
        except Exception as e:
            logger.warning(f"Failed to generate tool for {route_info['path']}: {e}")

    # 注册手动查询工具（这些工具提供关键的数据查询能力）
    _register_manual_query_tools()

    # 注册隐私计算工具
    _register_privacy_compute_tools()

    _initialized = True
    logger.info(f"Tool registry initialized: {registered} tools registered from {len(write_routes)} routes")


def get_registry_stats() -> dict:
    """获取注册表统计"""
    return {
        "total_tools": len(_tool_registry),
        "modules": {m: len(tools) for m, tools in _module_tools.items()},
        "auto_generated": sum(1 for t in _tool_registry.values() if t.get("auto_generated")),
        "manual": sum(1 for t in _tool_registry.values() if not t.get("auto_generated")),
    }
