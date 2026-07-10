"""限流中间件 - 基于滑动窗口的内存限流"""

import time
import threading
from collections import defaultdict
from functools import wraps

from flask import request, jsonify

from config.log_config import get_logger
from config.base import RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SEC

logger = get_logger("rate_limiter")


class SlidingWindowRateLimiter:
    """滑动窗口限流器（内存实现，无外部依赖）"""

    def __init__(self):
        # client_key -> deque of timestamps
        self._windows = defaultdict(list)
        self._lock = threading.Lock()
        # 后台清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _get_client_key(self):
        """获取客户端唯一标识：优先用 user_id，否则用 IP"""
        try:
            from flask import g
            user_id = getattr(g, "user_id", None)
            if user_id is not None:
                return f"user:{user_id}"
        except RuntimeError:
            pass
        # 也用 API Key 作为标识
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{api_key}"
        # 兜底：IP + User-Agent 前缀
        ip = request.remote_addr or "unknown"
        return f"ip:{ip}"

    def is_allowed(self) -> bool:
        """检查当前请求是否允许通过"""
        if not RATE_LIMIT_ENABLED:
            return True

        client_key = self._get_client_key()
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SEC

        with self._lock:
            timestamps = self._windows[client_key]
            # 移除窗口外的时间戳
            while timestamps and timestamps[0] < window_start:
                timestamps.pop(0)

            if len(timestamps) >= RATE_LIMIT_REQUESTS:
                logger.warning(
                    "限流触发: client=%s, count=%d/%d in %.1fs",
                    client_key, len(timestamps), RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SEC
                )
                return False

            timestamps.append(now)
            return True

    def _cleanup_loop(self):
        """定期清理过期记录，避免内存泄漏"""
        while True:
            time.sleep(RATE_LIMIT_WINDOW_SEC * 2)
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW_SEC * 2
            with self._lock:
                stale_keys = [
                    k for k, v in self._windows.items()
                    if not v or v[-1] < window_start
                ]
                for k in stale_keys:
                    del self._windows[k]
                if stale_keys:
                    logger.debug("限流器清理过期 key: %d 个", len(stale_keys))


# 全局限流器实例
rate_limiter = SlidingWindowRateLimiter()


def rate_limit(f):
    """限流装饰器：超过限制返回 429"""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not rate_limiter.is_allowed():
            return jsonify({
                "success": False,
                "message": f"请求过于频繁，请在 {RATE_LIMIT_WINDOW_SEC} 秒后重试",
            }), 429
        return f(*args, **kwargs)

    return decorated
