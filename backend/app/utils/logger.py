"""
结构化日志配置
"""
import logging
import sys
from typing import Optional

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = getattr(record, "extra_data", {})
        if extra:
            extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
            return f"{base} {extra_str}"
        return base


def setup_logging(level: Optional[str] = None) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
    """
    log_level = level or ("DEBUG" if settings.APP_DEBUG else "INFO")

    formatter = StructuredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.handlers = [handler]

    # 降低第三方库日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.APP_DEBUG else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger"""
    return logging.getLogger(name)
