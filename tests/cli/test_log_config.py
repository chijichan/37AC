"""测试日志配置模块"""

import logging
from unittest.mock import patch

import pytest


class TestLogConfig:
    """测试日志系统"""

    def test_get_logger_basic(self):
        """测试获取 logger"""
        from config.log_config import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_reuses(self):
        """测试重复获取返回同一实例"""
        from config.log_config import get_logger

        logger1 = get_logger("test_reuse")
        logger2 = get_logger("test_reuse")
        assert logger1 is logger2

    def test_get_logger_level(self):
        """测试日志级别"""
        from config.log_config import get_logger, get_log_level

        logger = get_logger("test_level")
        assert logger.level == get_log_level()

    def test_logger_has_handlers(self):
        """测试 logger 有处理器"""
        from config.log_config import get_logger

        logger = get_logger("test_handlers")
        assert len(logger.handlers) >= 1

    def test_logger_propagate_false(self):
        """测试日志不传播到根 logger"""
        from config.log_config import get_logger

        logger = get_logger("test_propagate")
        assert logger.propagate is False

    @patch("config.base.TSAC_DEBUG", True)
    def test_debug_level(self):
        """测试 DEBUG 模式下的日志级别"""
        from config.log_config import get_logger, get_log_level

        # 重新获取级别
        level = get_log_level()
        assert level == logging.DEBUG

    @patch("config.base.TSAC_DEBUG", False)
    def test_info_level(self):
        """测试 INFO 模式下的日志级别"""
        from config.log_config import get_logger, get_log_level

        level = get_log_level()
        assert level == logging.INFO