"""统一日志配置（CLI 与 Server 共享）

设计：
- 根 logger 统一持有 RotatingFileHandler + StreamHandler（文件轮转，避免无限增长）
- 子 logger 不添加处理器，propagate=True 传播到根 logger，避免重复打印
- 通过 init_logging(log_file, debug) 在应用启动时初始化一次
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日志格式模板
LOG_FORMAT = "%(asctime)s - %(levelname)-4s - %(name)-4s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认轮转配置：单文件 10MB，保留 5 个备份
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5

# DEBUG 模式下也应静默的第三方库前缀：这些库在 DEBUG 级别下会输出大量
# 内部解析/调用日志（例如 PIL 每次读图时刷屏的 STREAM/iCCP 消息），
# 对排查项目代码毫无帮助，统一在此过滤。不在此列的其他 DEBUG 日志保留。
NOISE_LOGGER_PREFIXES = (
    "PIL",
    "matplotlib",
)

_initialized = False


def _is_noise_logger(name: str) -> bool:
    """判断 logger 名称是否为需要静默 DEBUG 消息的第三方库。"""
    if not name:
        return False
    return any(name.startswith(prefix) for prefix in NOISE_LOGGER_PREFIXES)


class ThirdPartyNoiseFilter(logging.Filter):
    """过滤第三方库在 DEBUG 级别下的噪音消息。

    仅当满足以下条件时才丢弃：
      - 日志级别为 DEBUG（INFO 及以上正常放行）
      - logger 名称以 NOISE_LOGGER_PREFIXES 中的前缀开头
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.INFO and _is_noise_logger(record.name):
            return False
        return True


def get_log_level(debug: bool = False) -> int:
    """根据调试开关返回日志级别"""
    return logging.DEBUG if debug else logging.INFO


def _make_formatter() -> logging.Formatter:
    return logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def init_logging(
    log_file: str | Path,
    debug: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    console: bool = True,
) -> None:
    """初始化根 logger（幂等：重复调用会先清空旧 handler 再重建）。

    Args:
        log_file: 日志文件路径
        debug: 是否为调试模式（DEBUG 级别）
        max_bytes: 单文件最大字节数
        backup_count: 轮转备份文件数
        console: 是否同时输出到控制台
    """
    global _initialized

    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level(debug))

    # 清空旧 handler，避免重复初始化导致日志重复输出
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 第三方库 DEBUG 噪音过滤器（根 logger 上安装一次即可，所有子 logger 随之生效）
    noise_filter = ThirdPartyNoiseFilter()

    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(get_log_level(debug))
    file_handler.setFormatter(_make_formatter())
    file_handler.addFilter(noise_filter)
    root_logger.addHandler(file_handler)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(get_log_level(debug))
        console_handler.setFormatter(_make_formatter())
        console_handler.addFilter(noise_filter)
        root_logger.addHandler(console_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取标准化的 logger。

    子 logger 不添加任何处理器、不设置级别（NOTSET 继承根），完全由根 logger
    （init_logging 配置）统一输出，避免重复打印。若根 logger 尚未初始化，
    自动添加一个控制台兜底 handler，保证日志不丢失。

    Args:
        name: logger 名称，通常传入 __name__

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    if not _initialized:
        # 根未初始化时给一个兜底 handler，避免 "No handlers could be found"
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_make_formatter())
            root_logger.addHandler(handler)
    logger.propagate = True
    return logger
