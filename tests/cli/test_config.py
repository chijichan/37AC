"""测试 CLI 配置模块"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestCLIConfig:
    """CLI 配置基础测试"""

    @patch.dict(os.environ, {
        "TSAC_DEBUG": "True",
        "NUM_EPOCHS": "100",
        "BATCH_SIZE": "32",
        "IMAGE_SIZE": "128",
        "LEARNING_RATE": "1e-3",
    })
    def test_config_from_env(self):
        """验证从环境变量读取配置"""
        # 重新加载模块（模拟新的环境变量）
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        # 使用新加载的配置
        from config.base import (
            TSAC_DEBUG, NUM_EPOCHS, BATCH_SIZE,
            IMAGE_SIZE, LEARNING_RATE,
        )
        assert TSAC_DEBUG is True
        assert NUM_EPOCHS == 100
        assert BATCH_SIZE == 32
        assert IMAGE_SIZE == 128
        assert LEARNING_RATE == 1e-3

    @patch.dict(os.environ, {}, clear=True)
    @patch("dotenv.load_dotenv", lambda *args, **kwargs: False)
    def test_config_defaults(self):
        """验证默认值（禁用 .env 加载，避免本地配置干扰）"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import (
            TSAC_DEBUG, NUM_EPOCHS, BATCH_SIZE,
            IMAGE_SIZE, LEARNING_RATE,
            TCP_HOST, TCP_PORT,
        )
        # 布尔值默认 False
        assert TSAC_DEBUG is False
        # 数值默认
        assert NUM_EPOCHS == 50
        assert BATCH_SIZE == 16
        assert IMAGE_SIZE == 224
        assert LEARNING_RATE == 1e-4
        # 网络默认
        assert TCP_HOST == "127.0.0.1"
        assert TCP_PORT == 13137

    @patch.dict(os.environ, {
        "USE_DIRECTML": "True",
        "AUTO_DEVICE": "False",
        "YOLO_ENABLED": "False",
        "LLM_RECOGNITION_ENABLED": "True",
        "LLM_MODEL_NAME": "deepseek-vl2",
        "LLM_API_KEY": "test-key-123",
    })
    def test_feature_flags(self):
        """验证特性开关配置"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import (
            USE_DIRECTML, AUTO_DEVICE, YOLO_ENABLED,
            LLM_RECOGNITION_ENABLED, LLM_MODEL_NAME, LLM_API_KEY,
        )
        assert USE_DIRECTML is True
        assert AUTO_DEVICE is False
        assert YOLO_ENABLED is False
        assert LLM_RECOGNITION_ENABLED is True
        assert LLM_MODEL_NAME == "deepseek-vl2"
        assert LLM_API_KEY == "test-key-123"

    @patch.dict(os.environ, {
        "TCP_HOST": "0.0.0.0",
        "TCP_PORT": "9999",
        "NODE_ID": "42",
        "HEARTBEAT_INTERVAL_SEC": "10",
        "HEARTBEAT_MISS_LIMIT": "5",
    })
    def test_node_config(self):
        """验证节点服务配置"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import (
            TCP_HOST, TCP_PORT, NODE_ID,
            HEARTBEAT_INTERVAL_SEC, HEARTBEAT_MISS_LIMIT,
        )
        assert TCP_HOST == "0.0.0.0"
        assert TCP_PORT == 9999
        assert NODE_ID == 42
        assert HEARTBEAT_INTERVAL_SEC == 10
        assert HEARTBEAT_MISS_LIMIT == 5

    @patch.dict(os.environ, {
        "RESUME_MODEL_PATH": "",
        "MODEL_FILENAME": "custom_model.pth",
    })
    def test_model_paths(self):
        """验证模型路径配置"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import (
            RESUME_MODEL_PATH, MODEL_DIR, MODEL_PATH,
        )
        # RESUME_MODEL_PATH 为空时应为 None
        assert RESUME_MODEL_PATH is None
        # MODEL_DIR 应在 saves/models 下
        assert MODEL_DIR.name == "models"
        # MODEL_PATH 应使用自定义文件名
        assert MODEL_PATH.name == "custom_model.pth"

    def test_capabilities_local_only(self):
        """验证默认能力列表（仅 local）"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import CAPABILITIES
        import json
        caps = json.loads(CAPABILITIES)
        assert "local" in caps
        assert "llm" not in caps

    @patch.dict(os.environ, {"LLM_RECOGNITION_ENABLED": "True"})
    def test_capabilities_with_llm(self):
        """验证启用 LLM 后的能力列表"""
        from importlib import reload
        import config.base as cfg
        reload(cfg)

        from config.base import CAPABILITIES
        import json
        caps = json.loads(CAPABILITIES)
        assert "local" in caps
        assert "llm" in caps