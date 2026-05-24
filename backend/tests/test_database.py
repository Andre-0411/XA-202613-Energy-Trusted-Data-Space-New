"""
数据库模块测试
测试 logger 引用顺序修复
"""
import logging
import importlib
import sys


def test_logger_defined_before_use():
    """测试 logger 在使用前已定义"""
    # 重新加载模块以测试初始化顺序
    if "app.database" in sys.modules:
        del sys.modules["app.database"]

    # 这应该不会抛出 NameError
    from app.database import logger

    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.database"


def test_logger_warning_no_error():
    """测试 logger.warning 调用不会出错"""
    from app.database import logger

    # 这应该不会抛出任何异常
    logger.warning("Test warning message")
    logger.info("Test info message")
