"""
日志记录模块
"""
import logging
import sys
from typing import Optional
from datetime import datetime

# 配置日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 创建根日志记录器
logger = logging.getLogger("hserp")
logger.setLevel(logging.INFO)

# 避免重复添加处理器
if not logger.handlers:
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选，如果需要写入文件）
    # file_handler = logging.FileHandler("app.log")
    # file_handler.setLevel(logging.INFO)
    # file_handler.setFormatter(console_formatter)
    # logger.addHandler(file_handler)


def log_info(message: str, **kwargs):
    """记录信息日志"""
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    if extra_info:
        logger.info(f"{message} | {extra_info}")
    else:
        logger.info(message)


def log_error(message: str, error: Optional[Exception] = None, **kwargs):
    """记录错误日志"""
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    error_info = f" | error={str(error)}" if error else ""
    logger.error(f"{message} | {extra_info}{error_info}")


def log_warning(message: str, **kwargs):
    """记录警告日志"""
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    if extra_info:
        logger.warning(f"{message} | {extra_info}")
    else:
        logger.warning(message)


def log_debug(message: str, **kwargs):
    """记录调试日志"""
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    if extra_info:
        logger.debug(f"{message} | {extra_info}")
    else:
        logger.debug(message)

