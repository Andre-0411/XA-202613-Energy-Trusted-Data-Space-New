"""
可信数据空间双层角色体系
基于《可信数据空间 能力要求》(TDSA/A-001-2025) 第9章 生态主体定义

第一层：生态角色（组织级）— 定义组织在数据空间中的身份
第二层：操作角色（用户级）— 定义个人用户在组织内的操作权限
"""

from enum import Enum
from typing import Dict, List, Set


# ==================== 第一层：生态角色（组织级） ====================

class EcoRole(str, Enum):
    """生态角色 — 基于标准定义的8类生态主体"""
    # 数据提供方：提供数据资源并决定访问权限
    DATA_PROVIDER = "data_provider"
    # 数据使用方：依据合约对数据进行加工使用
    DATA_CONSUMER = "data_consumer"
    # 数据中介方：提供供需撮合服务
    DATA_INTERMEDIARY = "data_intermediary"
    # 数据托管方：提供数据存储托管运营服务
    DATA_TRUSTEE = "data_trustee"
    # 数据开发方：基于数据资源进行产品开发
    DATA_DEVELOPER = "data_developer"
    # 空间运营者：制定规则、运维平台、生态治理
    SPACE_OPERATOR = "space_operator"
    # 监管方：合规审查、安全监管、违规处理
    REGULATOR = "regulator"
    # 混合角色：同时具备多种生态角色
    HYBRID = "hybrid"


ECO_ROLE_LABELS: Dict[EcoRole, str] = {
    EcoRole.DATA_PROVIDER: "数据提供方",
    EcoRole.DATA_CONSUMER: "数据使用方",
    EcoRole.DATA_INTERMEDIARY: "数据中介方",
    EcoRole.DATA_TRUSTEE: "数据托管方",
    EcoRole.DATA_DEVELOPER: "数据开发方",
    EcoRole.SPACE_OPERATOR: "空间运营者",
    EcoRole.REGULATOR: "监管方",
    EcoRole.HYBRID: "混合角色",
}

ECO_ROLE_DESCRIPTIONS: Dict[EcoRole, str] = {
    EcoRole.DATA_PROVIDER: "提供数据资源并决定数据的访问和使用权限，通过数据共享获得收益",
    EcoRole.DATA_CONSUMER: "依据数字合约对获取的数据进行加工使用，实现数据价值转化",
    EcoRole.DATA_INTERMEDIARY: "在数据提供方与使用方之间提供供需撮合服务，促进数据资源高效匹配",
    EcoRole.DATA_TRUSTEE: "为数据提供方或使用方提供数据托管运营服务，包括数据存储、管理、运维",
    EcoRole.DATA_DEVELOPER: "基于数据资源进行数据产品开发、分析和应用创新",
    EcoRole.SPACE_OPERATOR: "制定管理规范与运营规则，建设和运维中间服务平台",
    EcoRole.REGULATOR: "对可信数据空间的运行进行监督管理，确保合规合法",
    EcoRole.HYBRID: "同时具备多种生态角色的组织",
}


# ==================== 第二层：操作角色（用户级） ====================

class OpRole(str, Enum):
    """操作角色 — 定义用户在组织内的操作权限"""
    # 系统级
    SYSTEM_ADMIN = "system_admin"           # 系统管理员
    # 组织级
    ORG_ADMIN = "org_admin"                 # 机构管理员
    # 数据操作
    DATA_STEWARD = "data_steward"           # 数据管理员（数据接入/治理/发布）
    DATA_SUBSCRIBER = "data_subscriber"     # 数据订阅员（搜索/申请/使用）
    # 产品操作
    PRODUCT_DEVELOPER = "product_developer"  # 产品开发员（开发/测试/上架）
    PRODUCT_PUBLISHER = "product_publisher"  # 产品上架员（上架/审核/定价）
    # 需求操作
    DEMAND_MANAGER = "demand_manager"        # 需求管理员（发布/认领/承接）
    # 审批操作
    APPROVER = "approver"                    # 审批员（审批/驳回/转交）
    # 运维操作
    OPERATOR = "operator"                    # 运维人员（平台运维/监控）
    # 审计操作
    AUDITOR = "auditor"                      # 审计员（审计/合规/监管）
    # 安全操作
    SECURITY_ADMIN = "security_admin"        # 安全管理员（密钥/策略/威胁）
    # 普通用户
    USER = "user"                            # 普通用户


OP_ROLE_LABELS: Dict[OpRole, str] = {
    OpRole.SYSTEM_ADMIN: "系统管理员",
    OpRole.ORG_ADMIN: "机构管理员",
    OpRole.DATA_STEWARD: "数据管理员",
    OpRole.DATA_SUBSCRIBER: "数据订阅员",
    OpRole.PRODUCT_DEVELOPER: "产品开发员",
    OpRole.PRODUCT_PUBLISHER: "产品上架员",
    OpRole.DEMAND_MANAGER: "需求管理员",
    OpRole.APPROVER: "审批员",
    OpRole.OPERATOR: "运维人员",
    OpRole.AUDITOR: "审计员",
    OpRole.SECURITY_ADMIN: "安全管理员",
    OpRole.USER: "普通用户",
}


# ==================== 权限定义 ====================

class Permission(str, Enum):
    """系统权限枚举"""
    # 数据资源
    DATA_VIEW = "data:view"
    DATA_CREATE = "data:create"
    DATA_EDIT = "data:edit"
    DATA_DELETE = "data:delete"
    DATA_PUBLISH = "data:publish"
    DATA_SUBSCRIBE = "data:subscribe"
    DATA_APPROVE = "data:approve"
    # 数据产品
    PRODUCT_VIEW = "product:view"
    PRODUCT_CREATE = "product:create"
    PRODUCT_PUBLISH = "product:publish"
    PRODUCT_APPROVE = "product:approve"
    PRODUCT_SUBSCRIBE = "product:subscribe"
    # 需求
    DEMAND_VIEW = "demand:view"
    DEMAND_CREATE = "demand:create"
    DEMAND_CLAIM = "demand:claim"
    DEMAND_APPROVE = "demand:approve"
    # 合约
    CONTRACT_VIEW = "contract:view"
    CONTRACT_CREATE = "contract:create"
    CONTRACT_SIGN = "contract:sign"
    CONTRACT_APPROVE = "contract:approve"
    # 计算
    COMPUTE_VIEW = "compute:view"
    COMPUTE_CREATE = "compute:create"
    COMPUTE_EXECUTE = "compute:execute"
    # 区块链
    BLOCKCHAIN_VIEW = "blockchain:view"
    BLOCKCHAIN_EVIDENCE = "blockchain:evidence"
    BLOCKCHAIN_NFT = "blockchain:nft"
    # 运营管理
    OPS_USER_MANAGE = "ops:user_manage"
    OPS_ORG_MANAGE = "ops:org_manage"
    OPS_MONITOR = "ops:monitor"
    OPS_BILLING = "ops:billing"
    # 安全管控
    SECURITY_KEY_MANAGE = "security:key_manage"
    SECURITY_POLICY = "security:policy"
    SECURITY_AUDIT = "security:audit"
    # 系统管理
    SYS_CONFIG = "sys:config"
    SYS_APPROVAL = "sys:approval"


# ==================== 生态角色 → 默认操作角色映射 ====================

ECO_TO_DEFAULT_OP_ROLES: Dict[EcoRole, List[OpRole]] = {
    EcoRole.DATA_PROVIDER: [OpRole.ORG_ADMIN, OpRole.DATA_STEWARD, OpRole.DATA_SUBSCRIBER],
    EcoRole.DATA_CONSUMER: [OpRole.ORG_ADMIN, OpRole.DATA_SUBSCRIBER, OpRole.PRODUCT_DEVELOPER],
    EcoRole.DATA_INTERMEDIARY: [OpRole.ORG_ADMIN, OpRole.DEMAND_MANAGER],
    EcoRole.DATA_TRUSTEE: [OpRole.ORG_ADMIN, OpRole.OPERATOR],
    EcoRole.DATA_DEVELOPER: [OpRole.ORG_ADMIN, OpRole.PRODUCT_DEVELOPER, OpRole.PRODUCT_PUBLISHER],
    EcoRole.SPACE_OPERATOR: [OpRole.SYSTEM_ADMIN, OpRole.OPERATOR, OpRole.APPROVER, OpRole.AUDITOR],
    EcoRole.REGULATOR: [OpRole.AUDITOR, OpRole.SECURITY_ADMIN],
    EcoRole.HYBRID: [OpRole.ORG_ADMIN, OpRole.DATA_STEWARD, OpRole.DATA_SUBSCRIBER, OpRole.PRODUCT_DEVELOPER],
}


# ==================== 操作角色 → 权限映射 ====================

OP_ROLE_PERMISSIONS: Dict[OpRole, Set[Permission]] = {
    OpRole.SYSTEM_ADMIN: set(Permission),  # 全部权限

    OpRole.ORG_ADMIN: {
        Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_EDIT, Permission.DATA_PUBLISH,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_CREATE, Permission.PRODUCT_PUBLISH,
        Permission.DEMAND_VIEW, Permission.DEMAND_CREATE, Permission.DEMAND_APPROVE,
        Permission.CONTRACT_VIEW, Permission.CONTRACT_CREATE, Permission.CONTRACT_SIGN, Permission.CONTRACT_APPROVE,
        Permission.COMPUTE_VIEW, Permission.COMPUTE_CREATE,
        Permission.BLOCKCHAIN_VIEW,
        Permission.OPS_USER_MANAGE, Permission.OPS_ORG_MANAGE, Permission.OPS_MONITOR,
        Permission.SYS_APPROVAL,
    },

    OpRole.DATA_STEWARD: {
        Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_EDIT, Permission.DATA_PUBLISH,
        Permission.CONTRACT_VIEW, Permission.CONTRACT_SIGN,
        Permission.BLOCKCHAIN_VIEW, Permission.BLOCKCHAIN_EVIDENCE,
    },

    OpRole.DATA_SUBSCRIBER: {
        Permission.DATA_VIEW, Permission.DATA_SUBSCRIBE,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_SUBSCRIBE,
        Permission.CONTRACT_VIEW, Permission.CONTRACT_SIGN,
        Permission.COMPUTE_VIEW, Permission.COMPUTE_CREATE, Permission.COMPUTE_EXECUTE,
    },

    OpRole.PRODUCT_DEVELOPER: {
        Permission.DATA_VIEW,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_CREATE,
        Permission.COMPUTE_VIEW, Permission.COMPUTE_CREATE, Permission.COMPUTE_EXECUTE,
        Permission.BLOCKCHAIN_VIEW,
    },

    OpRole.PRODUCT_PUBLISHER: {
        Permission.PRODUCT_VIEW, Permission.PRODUCT_PUBLISH, Permission.PRODUCT_APPROVE,
        Permission.CONTRACT_VIEW,
    },

    OpRole.DEMAND_MANAGER: {
        Permission.DEMAND_VIEW, Permission.DEMAND_CREATE, Permission.DEMAND_CLAIM,
        Permission.DATA_VIEW,
        Permission.CONTRACT_VIEW, Permission.CONTRACT_SIGN,
    },

    OpRole.APPROVER: {
        Permission.DATA_VIEW, Permission.DATA_APPROVE,
        Permission.PRODUCT_VIEW, Permission.PRODUCT_APPROVE,
        Permission.DEMAND_VIEW, Permission.DEMAND_APPROVE,
        Permission.CONTRACT_VIEW, Permission.CONTRACT_APPROVE,
        Permission.SYS_APPROVAL,
    },

    OpRole.OPERATOR: {
        Permission.DATA_VIEW,
        Permission.OPS_MONITOR, Permission.OPS_BILLING,
        Permission.SECURITY_POLICY,
    },

    OpRole.AUDITOR: {
        Permission.DATA_VIEW,
        Permission.PRODUCT_VIEW,
        Permission.DEMAND_VIEW,
        Permission.CONTRACT_VIEW,
        Permission.BLOCKCHAIN_VIEW,
        Permission.OPS_MONITOR,
        Permission.SECURITY_AUDIT,
    },

    OpRole.SECURITY_ADMIN: {
        Permission.SECURITY_KEY_MANAGE, Permission.SECURITY_POLICY, Permission.SECURITY_AUDIT,
        Permission.DATA_VIEW,
        Permission.BLOCKCHAIN_VIEW,
    },

    OpRole.USER: {
        Permission.DATA_VIEW,
        Permission.PRODUCT_VIEW,
        Permission.DEMAND_VIEW,
        Permission.COMPUTE_VIEW,
    },
}


# ==================== 辅助函数 ====================

def get_permissions_for_role(role: str) -> Set[Permission]:
    """获取角色的所有权限"""
    try:
        op_role = OpRole(role)
        return OP_ROLE_PERMISSIONS.get(op_role, {Permission.DATA_VIEW})
    except ValueError:
        return {Permission.DATA_VIEW}


def get_eco_role_label(eco_role: str) -> str:
    """获取生态角色中文标签"""
    try:
        return ECO_ROLE_LABELS[EcoRole(eco_role)]
    except (ValueError, KeyError):
        return eco_role


def get_op_role_label(op_role: str) -> str:
    """获取操作角色中文标签"""
    try:
        return OP_ROLE_LABELS[OpRole(op_role)]
    except (ValueError, KeyError):
        return op_role


def get_default_op_roles_for_eco(eco_role: str) -> List[str]:
    """获取生态角色的默认操作角色列表"""
    try:
        roles = ECO_TO_DEFAULT_OP_ROLES[EcoRole(eco_role)]
        return [r.value for r in roles]
    except (ValueError, KeyError):
        return [OpRole.USER.value]


def check_permission(role: str, permission: str) -> bool:
    """检查角色是否拥有指定权限"""
    perms = get_permissions_for_role(role)
    try:
        return Permission(permission) in perms
    except ValueError:
        return False
