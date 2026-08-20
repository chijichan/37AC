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
        """测试日志实际写入文件（debug 关闭时 WARNING 及以上会落盘）"""
        from common.log_config import init_logging, get_logger

        log_file = tmp_path / "test_write.log"
        init_logging(log_file, debug=False, console=False)
        logger = get_logger("test_write")
        logger.warning("hello-log-test")
        # 关闭 handler 确保 flush
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "hello-log-test" in content

    def test_file_only_warning_when_debug_off(self, tmp_path):
        """debug 关闭时文件只保存 WARNING 及以上，INFO 不落盘"""
        from common.log_config import init_logging, get_logger

        log_file = tmp_path / "test_warning_only.log"
        init_logging(log_file, debug=False, console=False)
        logger = get_logger("test_warning_only")
        logger.info("info-should-not-be-saved")
        logger.warning("warning-should-be-saved")
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "info-should-not-be-saved" not in content
        assert "warning-should-be-saved" in content

    def test_file_saves_all_when_debug_on(self, tmp_path):
        """debug 开启时文件保存全部日志（DEBUG 及以上）"""
        from common.log_config import init_logging, get_logger

        log_file = tmp_path / "test_debug_all.log"
        init_logging(log_file, debug=True, console=False)
        logger = get_logger("test_debug_all")
        logger.debug("debug-log")
        logger.info("info-log")
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "debug-log" in content
        assert "info-log" in content

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


class TestThirdPartyNoiseFilter:
    """测试第三方库 DEBUG 噪音过滤器"""

    @pytest.mark.parametrize("name,expected", [
        ("PIL.PngImagePlugin", True),
        ("PIL.Image", True),
        ("matplotlib.pyplot", True),
        ("training.trainer", False),
        ("config.base", False),
        ("", False),
    ])
    def test_is_noise_logger(self, name, expected):
        """测试噪音 logger 名称判定"""
        from common.log_config import _is_noise_logger

        assert _is_noise_logger(name) is expected

    def test_filter_blocks_noise_debug(self):
        """测试 DEBUG 级别的 PIL 消息被过滤"""
        from common.log_config import ThirdPartyNoiseFilter

        f = ThirdPartyNoiseFilter()
        record = logging.LogRecord(
            name="PIL.PngImagePlugin", level=logging.DEBUG,
            pathname="PIL/PngImagePlugin.py", lineno=1, msg="STREAM b'IHDR'", args=(), exc_info=None,
        )
        assert f.filter(record) is False

    def test_filter_allows_own_debug(self):
        """测试项目自身 logger 的 DEBUG 消息不被过滤"""
        from common.log_config import ThirdPartyNoiseFilter

        f = ThirdPartyNoiseFilter()
        record = logging.LogRecord(
            name="training.trainer", level=logging.DEBUG,
            pathname="training/trainer.py", lineno=1, msg="debug msg", args=(), exc_info=None,
        )
        assert f.filter(record) is True

    @pytest.mark.parametrize("level", [logging.INFO, logging.WARNING, logging.ERROR])
    def test_filter_allows_non_debug(self, level):
        """测试非 DEBUG 级别的第三方库消息始终放行"""
        from common.log_config import ThirdPartyNoiseFilter

        f = ThirdPartyNoiseFilter()
        record = logging.LogRecord(
            name="PIL.PngImagePlugin", level=level,
            pathname="PIL/PngImagePlugin.py", lineno=1, msg="some message", args=(), exc_info=None,
        )
        assert f.filter(record) is True

    def test_init_logging_installs_filter(self, tmp_path):
        """测试初始化后根 logger 的 handler 均安装了噪音过滤器"""
        from common.log_config import init_logging, ThirdPartyNoiseFilter

        init_logging(tmp_path / "filter_test.log", debug=True, console=True)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            assert any(isinstance(f, ThirdPartyNoiseFilter) for f in handler.filters)