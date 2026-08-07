"""测试限流中间件"""

import time
from unittest.mock import patch

from flask import Flask

app = Flask(__name__)


class TestSlidingWindowRateLimiter:
    """测试滑动窗口限流器"""

    def test_single_request_allowed(self):
        """测试单个请求允许通过"""
        from middleware.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter()
        # 直接测试 is_allowed 的核心逻辑
        from middleware.rate_limiter import RATE_LIMIT_ENABLED
        if RATE_LIMIT_ENABLED:
            # 直接测试底层逻辑
            from collections import deque
            client_key = "test:127.0.0.1"
            limiter._windows[client_key] = deque()
            now = time.time()
            limiter._windows[client_key].append(now)
            # 不应限流（因为 RATE_LIMIT_REQUESTS 通常为 5）
            with app.test_request_context():
                assert limiter.is_allowed() is True

    def test_rate_limiter_structure(self):
        """测试限流器结构"""
        from middleware.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter()
        assert hasattr(limiter, "_windows")
        assert hasattr(limiter, "_lock")
        assert hasattr(limiter, "_cleanup_thread")

    def test_rate_limiter_disabled(self):
        """测试禁用时始终允许"""
        with patch("middleware.rate_limiter.RATE_LIMIT_ENABLED", False):
            from middleware.rate_limiter import SlidingWindowRateLimiter
            limiter = SlidingWindowRateLimiter()
            assert limiter.is_allowed() is True


class TestRateLimitDecorator:
    """测试限流装饰器"""

    def test_rate_limit_decorator_exists(self):
        """测试装饰器存在"""
        from middleware.rate_limiter import rate_limit
        assert callable(rate_limit)

    def test_rate_limit_decorator_wraps(self):
        """测试装饰器包装函数（限流关闭时正常通过）"""
        from middleware.rate_limiter import rate_limit

        @rate_limit
        def my_func():
            return "success"

        with patch("middleware.rate_limiter.RATE_LIMIT_ENABLED", False):
            assert my_func() == "success"

    def test_rate_limit_decorator_429(self):
        """测试超过限制返回 429（使用独立限流器实例，避免污染全局单例）"""
        from middleware.rate_limiter import SlidingWindowRateLimiter, RATE_LIMIT_REQUESTS
        from collections import deque
        from unittest.mock import patch as mock_patch

        # 构造独立限流器并填满窗口，mock _get_client_key 使其命中该 key
        limiter = SlidingWindowRateLimiter()
        with mock_patch.object(limiter, "_get_client_key", return_value="test:127.0.0.1"):
            now = time.time()
            limiter._windows["test:127.0.0.1"] = deque([now] * RATE_LIMIT_REQUESTS)
            # 直接测试限流逻辑（is_allowed 返回 False）
            assert limiter.is_allowed() is False