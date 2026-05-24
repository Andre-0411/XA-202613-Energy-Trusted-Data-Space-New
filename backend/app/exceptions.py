"""
全局异常处理
AppException 基类 + 错误码体系

错误码规范:
  0     = 成功
  1xxx  = 认证错误
  2xxx  = 数据错误
  3xxx  = 计算错误
  4xxx  = 区块链错误
  5xxx  = 运营错误
  6xxx  = 安全错误
  9xxx  = 系统错误
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.data = data
        self.status_code = status_code
        super().__init__(message)


# ==================== 认证错误 (1xxx) ====================

class AuthenticationError(AppException):
    """认证错误"""
    def __init__(self, message: str = "认证失败", code: int = 1000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=401)


class TokenExpiredError(AuthenticationError):
    """Token 过期"""
    def __init__(self, message: str = "令牌已过期"):
        super().__init__(message=message, code=1003)


class TokenInvalidError(AuthenticationError):
    """Token 无效"""
    def __init__(self, message: str = "令牌无效"):
        super().__init__(message=message, code=1002)


class PermissionDeniedError(AppException):
    """权限不足"""
    def __init__(self, message: str = "权限不足", data: Any = None):
        super().__init__(code=1006, message=message, data=data, status_code=403)


class LoginFailedError(AuthenticationError):
    """登录失败"""
    def __init__(self, message: str = "用户名或密码错误"):
        super().__init__(message=message, code=1007)


# ==================== 数据错误 (2xxx) ====================

class DataError(AppException):
    """数据错误"""
    def __init__(self, message: str = "数据操作失败", code: int = 2000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=400)


class DataNotFoundError(DataError):
    """数据未找到"""
    def __init__(self, message: str = "数据未找到"):
        super().__init__(message=message, code=2001, status_code=404)


class DataAlreadyExistsError(DataError):
    """数据已存在"""
    def __init__(self, message: str = "数据已存在"):
        super().__init__(message=message, code=2002)


class DataValidationError(DataError):
    """数据验证失败"""
    def __init__(self, message: str = "数据验证失败", data: Any = None):
        super().__init__(message=message, code=2003, data=data)


class DataSourceError(DataError):
    """数据源错误"""
    def __init__(self, message: str = "数据源操作失败"):
        super().__init__(message=message, code=2010)


class DataQualityError(DataError):
    """数据质量错误"""
    def __init__(self, message: str = "数据质量检查失败"):
        super().__init__(message=message, code=2020)


# ==================== 计算错误 (3xxx) ====================

class ComputeError(AppException):
    """计算错误"""
    def __init__(self, message: str = "计算任务失败", code: int = 3000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=400)


class ComputeTaskNotFoundError(ComputeError):
    """计算任务未找到"""
    def __init__(self, message: str = "计算任务未找到"):
        super().__init__(message=message, code=3001, status_code=404)


class ComputeTaskRunningError(ComputeError):
    """计算任务正在运行"""
    def __init__(self, message: str = "计算任务正在运行中"):
        super().__init__(message=message, code=3002)


class ComputeSandboxError(ComputeError):
    """沙箱错误"""
    def __init__(self, message: str = "计算沙箱错误"):
        super().__init__(message=message, code=3010)


class ComputeDagError(ComputeError):
    """DAG 错误"""
    def __init__(self, message: str = "DAG 流程错误"):
        super().__init__(message=message, code=3020)


class QuotaExceededError(ComputeError):
    """配额超限错误"""
    def __init__(self, message: str = "配额超限"):
        super().__init__(message=message, code=3030)


# ==================== 区块链错误 (4xxx) ====================

class BlockchainError(AppException):
    """区块链错误"""
    def __init__(self, message: str = "区块链操作失败", code: int = 4000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=400)


class BlockchainConnectionError(BlockchainError):
    """区块链连接错误"""
    def __init__(self, message: str = "区块链节点连接失败"):
        super().__init__(message=message, code=4001)


class SmartContractError(BlockchainError):
    """智能合约错误"""
    def __init__(self, message: str = "智能合约执行失败"):
        super().__init__(message=message, code=4010)


class EvidenceError(BlockchainError):
    """存证错误"""
    def __init__(self, message: str = "存证操作失败"):
        super().__init__(message=message, code=4020)


class SettlementError(BlockchainError):
    """结算错误"""
    def __init__(self, message: str = "链上结算失败"):
        super().__init__(message=message, code=4030)


# ==================== 运营错误 (5xxx) ====================

class OpsError(AppException):
    """运营错误"""
    def __init__(self, message: str = "运营操作失败", code: int = 5000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=400)


class UserNotFoundError(OpsError):
    """用户未找到"""
    def __init__(self, message: str = "用户未找到"):
        super().__init__(message=message, code=5001, status_code=404)


class ServiceUnavailableError(OpsError):
    """服务不可用"""
    def __init__(self, message: str = "服务不可用"):
        super().__init__(message=message, code=5010, status_code=503)


class BillingError(OpsError):
    """计费错误"""
    def __init__(self, message: str = "计费操作失败"):
        super().__init__(message=message, code=5020)


class ComplianceError(OpsError):
    """合规错误"""
    def __init__(self, message: str = "合规检查失败"):
        super().__init__(message=message, code=5030)


# ==================== 安全错误 (6xxx) ====================

class SecurityError(AppException):
    """安全错误"""
    def __init__(self, message: str = "安全操作失败", code: int = 6000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=400)


class DIDError(SecurityError):
    """DID 错误"""
    def __init__(self, message: str = "DID 操作失败"):
        super().__init__(message=message, code=6010)


class VCError(SecurityError):
    """可验证凭证错误"""
    def __init__(self, message: str = "可验证凭证操作失败"):
        super().__init__(message=message, code=6020)


class CryptoError(SecurityError):
    """国密算法错误"""
    def __init__(self, message: str = "国密算法操作失败"):
        super().__init__(message=message, code=6030)


class ZKPError(SecurityError):
    """零知识证明错误"""
    def __init__(self, message: str = "零知识证明操作失败"):
        super().__init__(message=message, code=6040)


class ThreatDetectedError(SecurityError):
    """威胁检测"""
    def __init__(self, message: str = "检测到安全威胁"):
        super().__init__(message=message, code=6050, status_code=403)


class KeyManagementError(SecurityError):
    """密钥管理错误"""
    def __init__(self, message: str = "密钥管理操作失败"):
        super().__init__(message=message, code=6060)


# ==================== 系统错误 (9xxx) ====================

class SystemError(AppException):
    """系统错误"""
    def __init__(self, message: str = "系统内部错误", code: int = 9000, data: Any = None):
        super().__init__(code=code, message=message, data=data, status_code=500)


class DatabaseError(SystemError):
    """数据库错误"""
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message=message, code=9001)


class CacheError(SystemError):
    """缓存错误"""
    def __init__(self, message: str = "缓存操作失败"):
        super().__init__(message=message, code=9002)


class ExternalServiceError(SystemError):
    """外部服务错误"""
    def __init__(self, message: str = "外部服务调用失败"):
        super().__init__(message=message, code=9003, status_code=502)


class RateLimitExceededError(SystemError):
    """限流错误"""
    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(message=message, code=9010, status_code=429)


# ==================== 全局异常处理器 ====================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """应用异常统一处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未处理异常兜底"""
    import logging
    logging.getLogger(__name__).error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "code": 9999,
            "message": "系统内部错误",
            "data": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
