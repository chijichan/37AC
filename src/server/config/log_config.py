# config/log_config.py
"""Server 日志配置（薄封装，统一实现在 src/common/log_config.py）"""

from config.base import TSAC_DEBUG, LOGS_PATH
from common.log_config import (
    get_logger,
    init_logging as _common_init_logging,
    get_log_level as _common_get_log_level,
)

# 统一的日志文件路径
SERVER_LOG_FILE = LOGS_PATH / "server.log"


def get_log_level():
    """获取当前日志级别"""
    return _common_get_log_level(TSAC_DEBUG)


def init_logging():
    """初始化 Server 全局日志系统（根 logger + RotatingFileHandler，应用启动时调用一次）"""
    _common_init_logging(SERVER_LOG_FILE, debug=TSAC_DEBUG)
