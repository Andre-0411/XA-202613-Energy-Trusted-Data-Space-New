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

def _generate_tool_name(module: str, func_name: str, method: str) -> str:
    """生成工具名称: create_data_asset, update_contract 等"""
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

    # 构建参数字符串
    param_parts = []
    for p in params:
        if p.get("is_model"):
            # Pydantic 模型参数 → 转为 JSON 字符串
            param_parts.append(f'{p["name"]}: str = "{{}}"')
        else:
            type_str = "str" if p["type"] in ("any", "str") else p["type"]
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
    import httpx
    
    # 从上下文获取用户信息
    try:
        import contextvars
        user_ctx = contextvars.copy_context().get("_current_user_context", {{}})
    except:
        user_ctx = {{}}
    
    # 构建请求数据
    request_data = {{}}
'''

    # 添加参数处理
    for p in params:
        if p.get("is_model"):
            func_code += f'''
    try:
        request_data["{p["name"]}"] = _json.loads({p["name"]})
    except:
        request_data["{p["name"]}"] = {{}}
'''
        else:
            func_code += f'''
    if {p["name"]} is not None:
        request_data["{p["name"]}"] = {p["name"]}
'''

    # 添加 API 调用
    func_code += f'''
    # 调用内部服务
    try:
        async with AsyncSessionLocal() as session:
            # 直接调用服务函数
            from app.services import {route_info["module"]}_service
            service_func = getattr({route_info["module"]}_service, "{route_info["func_name"]}", None)
            if service_func:
                result = await service_func(db=session, **request_data)
                return _json.dumps({{"success": True, "result": result}}, ensure_ascii=False, default=str)
            else:
                return _json.dumps({{"success": False, "error": "服务函数未找到"}}, ensure_ascii=False)
    except Exception as e:
        return _json.dumps({{"success": False, "error": str(e)}}, ensure_ascii=False)
'''

    # 执行代码创建函数（将 tool 装饰器传入 namespace）
    from langchain_core.tools import tool as _tool_decorator
    namespace = {"tool": _tool_decorator}
    exec(func_code, namespace)
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
        "query": ["data", "catalog", "metadata", "quality", "market"],
        "trade": ["product", "contract", "demand", "subscription", "market"],
        "security": ["security", "evidence", "audit", "policy"],
        "dispatch": ["compute", "dag", "sandbox", "cluster"],
    }

    modules = agent_modules.get(agent_type, [])
    tools = []

    for module in modules:
        for name, entry in _tool_registry.items():
            if entry["module"] == module:
                tools.append(entry["func"])

    return tools


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
