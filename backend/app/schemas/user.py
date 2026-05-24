"""
用户 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


class OrganizationCreate(BaseModel):
    """创建组织"""
    name: str = Field(max_length=200, description="组织名称")
    code: str = Field(max_length=50, description="组织编码")
    parent_id: Optional[str] = Field(default=None, description="父组织 ID")
    level: int = Field(default=1, ge=1, le=4, description="层级")
    did: Optional[str] = Field(default=None, description="组织 DID")
    metadata: Optional[dict] = Field(default=None, description="扩展信息")


class OrganizationResponse(BaseModel):
    """组织响应"""
    id: str
    name: str
    code: str
    parent_id: Optional[str] = None
    level: int
    status: str
    did: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Handle metadata_ -> metadata mapping
        if hasattr(obj, 'metadata_') and not hasattr(obj, 'metadata'):
            obj.metadata = obj.metadata_
        elif hasattr(obj, 'get'):
            if 'metadata_' in obj and 'metadata' not in obj:
                obj['metadata'] = obj.get('metadata_')
        return super().model_validate(obj, **kwargs)


class DepartmentCreate(BaseModel):
    """创建部门"""
    name: str = Field(max_length=200, description="部门名称")
    organization_id: str = Field(description="所属组织 ID")
    parent_id: Optional[str] = Field(default=None, description="父部门 ID")


class DepartmentResponse(BaseModel):
    """部门响应"""
    id: str
    name: str
    organization_id: str
    parent_id: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(max_length=100, description="用户名")
    password: str = Field(min_length=8, max_length=128, description="密码")
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="手机号")
    role: str = Field(default="user", description="角色")
    department_id: Optional[str] = Field(default=None, description="部门 ID")
    organization_id: str = Field(description="组织 ID")


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="手机号")
    role: Optional[str] = Field(default=None, description="角色")
    department_id: Optional[str] = Field(default=None, description="部门 ID")
    status: Optional[str] = Field(default=None, description="状态")
    mfa_enabled: Optional[bool] = Field(default=None, description="MFA 开关")


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    did: Optional[str] = None
    sm2_public_key: Optional[str] = None
    mfa_enabled: bool = False
    role: str
    department_id: Optional[str] = None
    organization_id: str
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
