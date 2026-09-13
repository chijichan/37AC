# services/settings_service.py
"""系统设置服务 - settings 表读写（仅管理员可修改）

默认设置项：
  - auto_split_ratio    auto 模式下走 37ac 的百分比（默认 55，即 55% 37ac / 45% llm）
  - rate_limit_enabled  是否开启限流（1/0）
  - task_max_retries    任务最大重试次数
  - maintenance_mode    维护模式（1/0，暂只记录）
"""

import threading
import time

from utils.db_utils import get_connection
from config.log_config import get_logger

logger = get_logger("settings_service")

DEFAULTS = {
    "auto_split_ratio": "55",
    "rate_limit_enabled": "1",
    "task_max_retries": "3",
    "maintenance_mode": "0",
}
ALLOWED_KEYS = set(DEFAULTS.keys())

# 热路径缓存：限流中间件、任务管理器会在每个请求/每个任务上读取设置，
# 这里做短 TTL 缓存，避免频繁打数据库；写入设置后立即失效。
_CACHE_TTL_SEC = 5.0
_cache = {"at": 0.0, "values": None}
_cache_lock = threading.Lock()


def invalidate_cache():
    """清空设置缓存（设置更新后调用）。"""
    with _cache_lock:
        _cache["values"] = None
        _cache["at"] = 0.0


def _cached_settings() -> dict:
    """带 TTL 的设置快照。"""
    now = time.monotonic()
    with _cache_lock:
        values = _cache["values"]
        if values is not None and now - _cache["at"] < _CACHE_TTL_SEC:
            return values

    values = get_settings()
    with _cache_lock:
        _cache["values"] = values
        _cache["at"] = time.monotonic()
    return values


def get_setting(key: str, default=None):
    """读取单个设置项（带缓存，读库失败时回退默认值）。"""
    value = _cached_settings().get(key)
    if value is None:
        value = DEFAULTS.get(key, default)
    return default if value is None else value


def get_int(key: str, default: int = 0) -> int:
    """读取整数设置项。"""
    try:
        return int(str(get_setting(key, default)).strip())
    except (TypeError, ValueError):
        return default


def get_settings() -> dict:
    """读取系统设置（缺失项用默认值补齐）。"""
    result = dict(DEFAULTS)
    conn = get_connection()
    if not conn:
        return result
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT `key`, `value` FROM settings")
            for key, value in cursor.fetchall():
                if key in result and value is not None:
                    result[key] = str(value)
    except Exception as e:
        logger.error("读取系统设置失败: %s", e)
    finally:
        conn.close()
    return result


def update_settings(data: dict) -> dict:
    """更新系统设置（只接受白名单 key）。"""
    updates = {
        key: str(value)
        for key, value in (data or {}).items()
        if key in ALLOWED_KEYS and value is not None
    }
    if not updates:
        return {"success": False, "message": "没有可更新的设置项"}

    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            for key, value in updates.items():
                cursor.execute(
                    "INSERT INTO settings (`key`, `value`) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
                    (key, value),
                )
        conn.commit()
        invalidate_cache()
        logger.info("系统设置已更新: %s", ", ".join(updates.keys()))
        return {"success": True, "data": get_settings()}
    except Exception as e:
        conn.rollback()
        logger.error("更新系统设置失败: %s", e)
        return {"success": False, "message": f"更新失败: {e}"}
    finally:
        conn.close()
