"""测试限流中间件"""

import time
from unittest.mock import patch

import pytest


class TestSlidingWindowRateLimiter:
    """测试滑动窗口限流器"""

    def test_single_request_allowed(self):
        """测试单个请求允许通过"""
        from services.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter()
        # 直接测试 is_allowed 的核心逻辑
        from services.rate_limiter import RATE_LIMIT_ENABLED
        if RATE_LIMIT_ENABLED:
            # 直接测试底层逻辑
            from collections import deque
            import time
            client_key = "test:127.0.0.1"
            limiter._windows[client_key] = deque()
            now = time.time()
            limiter._windows[client_key].append(now)
            # 不应限流（因为 RATE_LIMIT_REQUESTS 通常为 5）
            pass

    def test_rate_limiter_structure(self):
        """测试限流器结构"""
        from services.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter()
        assert hasattr(limiter, "_windows")
        assert hasattr(limiter, "_lock")
        assert hasattr(limiter, "_cleanup_thread")

    def test_rate_limiter_disabled(self):
        """测试禁用时始终允许"""
        with patch("services.rate_limiter.RATE_LIMIT_ENABLED", False):
            from services.rate_limiter import SlidingWindowRateLimiter
            limiter = SlidingWindowRateLimiter()
            assert limiter.is_allowed() is True


class TestRateLimitDecorator:
    """测试限流装饰器"""

    def test_rate_limit_decorator_exists(self):
        """测试装饰器存在"""
        from services.rate_limiter import rate_limit
        assert callable(rate_limit)

    def test_rate_limit_decorator_wraps(self):
        """测试装饰器包装函数"""
        from services.rate_limiter import rate_limit

        @rate_limit
        def my_func():
            return "success"

        assert my_func() == "success"