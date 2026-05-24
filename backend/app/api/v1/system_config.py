"""
系统配置管理 API
提供系统参数配置、邮件设置、通知设置等管理功能
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

router = APIRouter()

# ===== 数据模型 =====

class ConfigItem(BaseModel):
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值")
    description: str = Field("", description="配置描述")
    category: str = Field("general", description="配置分类")
    is_sensitive: bool = Field(False, description="是否敏感信息")

class ConfigUpdate(BaseModel):
    value: Any = Field(..., description="配置值")

class ConfigBatchUpdate(BaseModel):
    configs: List[ConfigItem] = Field(..., description="配置列表")

# ===== Mock配置数据 =====

SYSTEM_CONFIGS = {
    # 通用配置
    "general": {
        "site_name": {
            "value": "能源可信数据空间",
            "description": "平台名称",
            "is_sensitive": False
        },
        "site_description": {
            "value": "面向能源行业的可信数据共享与流通平台",
            "description": "平台描述",
            "is_sensitive": False
        },
        "admin_email": {
            "value": "admin@energy-trusted.com",
            "description": "管理员邮箱",
            "is_sensitive": False
        },
        "timezone": {
            "value": "Asia/Shanghai",
            "description": "系统时区",
            "is_sensitive": False
        },
        "language": {
            "value": "zh-CN",
            "description": "默认语言",
            "is_sensitive": False
        },
        "maintenance_mode": {
            "value": False,
            "description": "维护模式开关",
            "is_sensitive": False
        }
    },
    # 邮件配置
    "email": {
        "smtp_host": {
            "value": "smtp.energy-trusted.com",
            "description": "SMTP服务器地址",
            "is_sensitive": False
        },
        "smtp_port": {
            "value": 587,
            "description": "SMTP端口",
            "is_sensitive": False
        },
        "smtp_username": {
            "value": "noreply@energy-trusted.com",
            "description": "SMTP用户名",
            "is_sensitive": False
        },
        "smtp_password": {
            "value": "********",
            "description": "SMTP密码",
            "is_sensitive": True
        },
        "sender_name": {
            "value": "能源可信数据空间",
            "description": "发件人名称",
            "is_sensitive": False
        },
        "enable_tls": {
            "value": True,
            "description": "启用TLS加密",
            "is_sensitive": False
        }
    },
    # 通知配置
    "notification": {
        "enable_email_notification": {
            "value": True,
            "description": "启用邮件通知",
            "is_sensitive": False
        },
        "enable_sms_notification": {
            "value": False,
            "description": "启用短信通知",
            "is_sensitive": False
        },
        "enable_browser_notification": {
            "value": True,
            "description": "启用浏览器通知",
            "is_sensitive": False
        },
        "notification_retention_days": {
            "value": 30,
            "description": "通知保留天数",
            "is_sensitive": False
        },
        "alert_email_recipients": {
            "value": ["admin@energy-trusted.com", "ops@energy-trusted.com"],
            "description": "告警邮件接收人",
            "is_sensitive": False
        }
    },
    # 安全配置
    "security": {
        "session_timeout_minutes": {
            "value": 30,
            "description": "会话超时时间(分钟)",
            "is_sensitive": False
        },
        "max_login_attempts": {
            "value": 5,
            "description": "最大登录尝试次数",
            "is_sensitive": False
        },
        "password_min_length": {
            "value": 8,
            "description": "密码最小长度",
            "is_sensitive": False
        },
        "require_2fa": {
            "value": False,
            "description": "强制两步验证",
            "is_sensitive": False
        },
        "allowed_ip_ranges": {
            "value": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
            "description": "允许的IP范围",
            "is_sensitive": False
        }
    },
    # 存储配置
    "storage": {
        "max_file_size_mb": {
            "value": 100,
            "description": "最大文件大小(MB)",
            "is_sensitive": False
        },
        "allowed_file_types": {
            "value": [".csv", ".json", ".xlsx", ".pdf", ".txt"],
            "description": "允许的文件类型",
            "is_sensitive": False
        },
        "storage_backend": {
            "value": "local",
            "description": "存储后端(local/s3/oss)",
            "is_sensitive": False
        },
        "data_retention_days": {
            "value": 365,
            "description": "数据保留天数",
            "is_sensitive": False
        }
    }
}

# ===== API端点 =====

@router.get("/categories", summary="获取配置分类列表")
async def get_config_categories():
    """获取所有配置分类"""
    categories = [
        {"key": "general", "name": "通用配置", "description": "平台基础配置"},
        {"key": "email", "name": "邮件配置", "description": "SMTP邮件服务配置"},
        {"key": "notification", "name": "通知配置", "description": "消息通知相关配置"},
        {"key": "security", "name": "安全配置", "description": "系统安全相关配置"},
        {"key": "storage", "name": "存储配置", "description": "文件存储相关配置"},
    ]
    return {"code": 0, "message": "success", "data": categories}

@router.get("/{category}", summary="获取分类下的配置")
async def get_configs_by_category(category: str):
    """获取指定分类下的所有配置"""
    if category not in SYSTEM_CONFIGS:
        raise HTTPException(status_code=404, detail=f"配置分类 '{category}' 不存在")
    
    configs = []
    for key, config in SYSTEM_CONFIGS[category].items():
        configs.append({
            "key": key,
            "value": "********" if config["is_sensitive"] else config["value"],
            "description": config["description"],
            "category": category,
            "is_sensitive": config["is_sensitive"]
        })
    
    return {"code": 0, "message": "success", "data": configs}

@router.put("/{category}/{key}", summary="更新配置项")
async def update_config(category: str, key: str, data: ConfigUpdate):
    """更新指定配置项"""
    if category not in SYSTEM_CONFIGS:
        raise HTTPException(status_code=404, detail=f"配置分类 '{category}' 不存在")
    if key not in SYSTEM_CONFIGS[category]:
        raise HTTPException(status_code=404, detail=f"配置项 '{key}' 不存在")
    
    SYSTEM_CONFIGS[category][key]["value"] = data.value
    return {"code": 0, "message": "更新成功", "data": {"key": key, "value": data.value}}

@router.post("/batch-update", summary="批量更新配置")
async def batch_update_configs(data: ConfigBatchUpdate):
    """批量更新配置项"""
    updated_count = 0
    for config in data.configs:
        if config.category in SYSTEM_CONFIGS and config.key in SYSTEM_CONFIGS[config.category]:
            SYSTEM_CONFIGS[config.category][config.key]["value"] = config.value
            updated_count += 1
    
    return {"code": 0, "message": f"成功更新 {updated_count} 项配置"}

@router.post("/reset/{category}", summary="重置分类配置")
async def reset_category_config(category: str):
    """重置指定分类的配置为默认值（仅用于演示）"""
    if category not in SYSTEM_CONFIGS:
        raise HTTPException(status_code=404, detail=f"配置分类 '{category}' 不存在")
    
    return {"code": 0, "message": f"已重置 {category} 分类的配置"}

@router.get("/export/all", summary="导出所有配置")
async def export_all_configs():
    """导出所有配置（不含敏感信息）"""
    export_data = {}
    for category, configs in SYSTEM_CONFIGS.items():
        export_data[category] = {}
        for key, config in configs.items():
            if not config["is_sensitive"]:
                export_data[category][key] = config["value"]
    
    return {"code": 0, "message": "success", "data": export_data}
