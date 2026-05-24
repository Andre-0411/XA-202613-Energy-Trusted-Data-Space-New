"""
注册/认证 Schema
InviteCode / OrganizationCertification / OrganizationJoinRequest / CustomRole / UserRole
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 邀请码 ====================

class InviteCodeCreate(BaseModel):
    """创建邀请码"""
    organization_id: Optional[str] = Field(default=None, description="关联组织 ID")
    max_uses: int = Field(default=1, ge=1, le=1000, description="最大使用次数")
    expires_at: str = Field(description="过期时间 ISO 8601")


class InviteCodeBatchCreate(BaseModel):
    """批量创建邀请码"""
    count: int = Field(default=5, ge=1, le=100, description="生成数量")
    organization_id: Optional[str] = Field(default=None, description="关联组织 ID")
    max_uses: int = Field(default=1, ge=1, le=1000, description="每个邀请码最大使用次数")
    expires_hours: int = Field(default=24, ge=1, le=720, description="有效小时数（默认24小时）")


class InviteCodeResponse(BaseModel):
    """邀请码响应"""
    id: str = Field(description="邀请码 ID")
    code: str = Field(description="邀请码")
    created_by: str = Field(description="创建者 ID")
    organization_id: Optional[str] = Field(default=None, description="关联组织 ID")
    max_uses: int = Field(description="最大使用次数")
    used_count: int = Field(description="已使用次数")
    error_count: int = Field(description="错误次数")
    status: str = Field(description="状态")
    expires_at: str = Field(description="过期时间")
    created_at: str = Field(description="创建时间")


class InviteCodeVerify(BaseModel):
    """验证邀请码"""
    code: str = Field(description="邀请码")


# ==================== 机构认证 ====================

class CertificationCreate(BaseModel):
    """创建机构认证申请"""
    cert_type: str = Field(description="认证类型: standard/diamond/gold/silver")
    business_license_url: Optional[str] = Field(default=None, description="营业执照 URL")
    legal_person_id_url: Optional[str] = Field(default=None, description="法人身份证 URL")
    credit_report_url: Optional[str] = Field(default=None, description="信用报告 URL")
    authorization_letter_url: Optional[str] = Field(default=None, description="授权委托书 URL")
    dcmm_cert_url: Optional[str] = Field(default=None, description="DCMM 证书 URL")
    iso_cert_url: Optional[str] = Field(default=None, description="ISO 证书 URL")
    social_credit_code: Optional[str] = Field(default=None, description="统一社会信用代码")


class CertificationReview(BaseModel):
    """审核认证申请"""
    status: str = Field(description="审核结果: approved/rejected")
    review_comment: Optional[str] = Field(default=None, description="审核意见")
    review_level: int = Field(default=1, description="审核级别: 1=机构管理员初审, 2=平台运营方终审")


class CertificationResponse(BaseModel):
    """认证申请响应"""
    id: str = Field(description="认证申请 ID")
    organization_id: str = Field(description="组织 ID")
    cert_type: str = Field(description="认证类型")
    business_license_url: Optional[str] = Field(default=None)
    legal_person_id_url: Optional[str] = Field(default=None)
    credit_report_url: Optional[str] = Field(default=None)
    authorization_letter_url: Optional[str] = Field(default=None)
    dcmm_cert_url: Optional[str] = Field(default=None)
    iso_cert_url: Optional[str] = Field(default=None)
    social_credit_code: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 机构加入申请 ====================

class JoinRequestCreate(BaseModel):
    """创建机构加入申请"""
    organization_id: str = Field(description="目标组织 ID")
    reason: Optional[str] = Field(default=None, description="申请理由")


class JoinRequestReview(BaseModel):
    """审核加入申请"""
    status: str = Field(description="审核结果: approved/rejected")
    review_comment: Optional[str] = Field(default=None, description="审核意见")


class JoinRequestResponse(BaseModel):
    """加入申请响应"""
    id: str = Field(description="申请 ID")
    user_id: str = Field(description="申请人 ID")
    organization_id: str = Field(description="目标组织 ID")
    reason: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 自定义角色 ====================

class CustomRoleCreate(BaseModel):
    """创建自定义角色"""
    name: str = Field(description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    permissions: dict = Field(default_factory=dict, description="权限配置")


class CustomRoleUpdate(BaseModel):
    """更新自定义角色"""
    name: Optional[str] = Field(default=None, description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    permissions: Optional[dict] = Field(default=None, description="权限配置")
    status: Optional[str] = Field(default=None, description="状态")


class CustomRoleResponse(BaseModel):
    """自定义角色响应"""
    id: str = Field(description="角色 ID")
    name: str = Field(description="角色名称")
    description: Optional[str] = Field(default=None)
    organization_id: str = Field(description="所属组织 ID")
    permissions: dict = Field(default_factory=dict)
    is_system: bool = Field(description="是否系统角色")
    status: str = Field(description="状态")
    created_by: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


class UserRoleAssign(BaseModel):
    """分配用户角色"""
    user_id: str = Field(description="用户 ID")
    role_id: str = Field(description="角色 ID")


class UserRoleResponse(BaseModel):
    """用户角色关联响应"""
    id: str = Field(description="关联 ID")
    user_id: str = Field(description="用户 ID")
    role_id: str = Field(description="角色 ID")
    assigned_by: Optional[str] = Field(default=None)
    assigned_at: str = Field(description="分配时间")
