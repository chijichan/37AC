"""测试 API 密钥管理服务模块"""

from unittest.mock import patch, MagicMock

import pytest


class TestCreateApiKey:
    """测试创建 API 密钥"""

    @patch("services.api_key_service._get_connection")
    def test_create_key_success(self, mock_get_conn):
        """测试创建密钥成功"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.api_key_service import create_api_key
        result = create_api_key(user_id=1, name="测试密钥", permission="read")
        assert result["success"] is True
        assert result["data"]["name"] == "测试密钥"
        assert "key" in result["data"]  # 创建时返回原始密钥
        assert result["data"]["key"].startswith("37ac_")

    def test_create_key_empty_name(self):
        """测试空名称创建失败"""
        from services.api_key_service import create_api_key
        result = create_api_key(user_id=1, name="", permission="read")
        assert result["success"] is False
        assert "名称不能为空" in result["message"]

    def test_create_key_invalid_permission(self):
        """测试无效权限"""
        from services.api_key_service import create_api_key
        result = create_api_key(user_id=1, name="test", permission="superadmin")
        assert result["success"] is False
        assert "权限" in result["message"]


class TestGetUserApiKeys:
    """测试获取用户 API 密钥列表"""

    @patch("services.api_key_service._get_connection")
    def test_get_user_keys(self, mock_get_conn):
        """测试获取用户密钥列表"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Key1", "permission": "read", "status": "active",
             "usage_count": 5, "max_usage": 1000,
             "created_at": None, "updated_at": None, "last_used_at": None},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.api_key_service import get_user_api_keys
        result = get_user_api_keys(user_id=1)
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "Key1"


class TestHashKey:
    """测试密钥哈希"""

    def test_hash_is_sha256(self):
        """测试哈希使用 SHA-256"""
        from services.api_key_service import _hash_key
        hashed = _hash_key("test_key_123")
        assert len(hashed) == 64  # SHA-256 十六进制长度

    def test_hash_deterministic(self):
        """测试相同密钥哈希值相同"""
        from services.api_key_service import _hash_key
        assert _hash_key("test_key") == _hash_key("test_key")

    def test_hash_different_keys(self):
        """测试不同密钥哈希值不同"""
        from services.api_key_service import _hash_key
        assert _hash_key("key1") != _hash_key("key2")


class TestGenerateKeyString:
    """测试密钥字符串生成"""

    def test_key_format(self):
        """测试密钥格式"""
        from services.api_key_service import _generate_key_string
        key = _generate_key_string()
        assert key.startswith("37ac_")
        assert len(key) == 5 + 40  # prefix + 40 random chars

    def test_key_custom_prefix(self):
        """测试自定义前缀"""
        from services.api_key_service import _generate_key_string
        key = _generate_key_string(prefix="custom")
        assert key.startswith("custom_")