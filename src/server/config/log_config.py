# config/log_config.py
"""统一日志配置 - 所有模块共享同一个日志系统"""

import logging
import sys
from pathlib import Path
from config.base import TSAC_DEBUG, LOGS_PATH

# 日志格式模板
LOG_FORMAT = "%(asctime)s - %(levelname)-4s - %(name)-4s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 统一的日志文件路径
SERVER_LOG_FILE = LOGS_PATH / "server.log"

# 存储已配置的 logger 缓存
_loggers_configured = set()


def get_log_level():
    """获取当前日志级别"""
    return logging.DEBUG if TSAC_DEBUG else logging.INFO


def get_logger(name: str) -> logging.Logger:
    """获取标准化的 logger

    所有模块通过此函数获取 logger，保证：
    - 统一的日志级别
    - 统一的格式
    - 统一的文件输出
    - 统一的控制台输出

    Args:
        name: logger 名称，通常传入 __name__

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if name in _loggers_configured:
        return logger

    logger.setLevel(get_log_level())

    # 如果 logger 已有处理器（可能来自根日志配置），跳过添加
    if logger.handlers:
        _loggers_configured.add(name)
        return logger

    # 子 logger 只添加控制台处理器，文件处理器由根 logger 统一管理
    logger.propagate = True

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(get_log_level())
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    _loggers_configured.add(name)
    return logger


def init_logging():
    """初始化全局日志系统（在应用启动时调用一次）

    配置根 logger，为所有未配置的模块提供默认日志行为。
    """
    # 确保日志目录存在
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 文件处理器
    file_handler = logging.FileHandler(
        SERVER_LOG_FILE,
        encoding="utf-8",
        mode="a",
    )
    file_handler.setLevel(get_log_level())
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(get_log_level())
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # 记录启动日志
    logger = logging.getLogger("init")
    logger.info("=" * 80)
    logger.info("  日志系统初始化完成")
    logger.info(f"  日志文件: {SERVER_LOG_FILE}")
    logger.info(f"  日志级别: {'DEBUG' if TSAC_DEBUG else 'INFO'}")
    logger.info("=" * 80)
