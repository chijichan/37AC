"""测试日志配置模块"""

import logging

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
        """测试日志级别（未初始化时兜底为 WARNING 级别）"""
        from config.log_config import get_logger

        logger = get_logger("test_level")
        # 子 logger 不设级别（NOTSET），继承根 logger
        assert logger.level == logging.NOTSET

    def test_logger_propagate_true(self):
        """测试子 logger 传播到根 logger（统一输出，避免重复 handler）"""
        from config.log_config import get_logger

        logger = get_logger("test_propagate")
        assert logger.propagate is True

    def test_init_logging_root_handlers(self, tmp_path):
        """测试初始化后根 logger 持有文件（轮转）与控制台处理器"""
        from common.log_config import init_logging

        init_logging(tmp_path / "test.log", debug=False, console=False)
        root_logger = logging.getLogger()
        handlers = root_logger.handlers
        assert len(handlers) >= 1
        # 文件处理器为 RotatingFileHandler
        from logging.handlers import RotatingFileHandler
        assert any(isinstance(h, RotatingFileHandler) for h in handlers)

    def test_init_logging_writes_file(self, tmp_path):
        """测试日志实际写入文件"""
        from common.log_config import init_logging, get_logger

        log_file = tmp_path / "test_write.log"
        init_logging(log_file, debug=False, console=False)
        logger = get_logger("test_write")
        logger.info("hello-log-test")
        # 关闭 handler 确保 flush
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "hello-log-test" in content

    def test_init_logging_idempotent(self, tmp_path):
        """测试重复初始化不会重复添加 handler"""
        from common.log_config import init_logging

        init_logging(tmp_path / "a.log", console=False)
        count_after_first = len(logging.getLogger().handlers)
        init_logging(tmp_path / "b.log", console=False)
        count_after_second = len(logging.getLogger().handlers)
        assert count_after_second <= count_after_first

    @pytest.mark.parametrize("debug,expected", [
        (True, logging.DEBUG),
        (False, logging.INFO),
    ])
    def test_get_log_level(self, debug, expected):
        """测试日志级别计算"""
        from common.log_config import get_log_level

        assert get_log_level(debug) == expected