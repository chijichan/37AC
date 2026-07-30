"""测试密码服务模块"""

from unittest.mock import patch, MagicMock

import pytest


class TestHashPassword:
    """测试密码哈希"""

    def test_hash_returns_string(self):
        """测试哈希返回字符串"""
        from services.auth.password_service import hash_password

        hashed = hash_password("test_password_123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_differs_from_original(self):
        """测试哈希值和原密码不同"""
        from services.auth.password_service import hash_password

        password = "test_password_123"
        hashed = hash_password(password)
        assert hashed != password

    def test_same_password_different_hashes(self):
        """测试相同密码两次哈希不同（自动加盐）"""
        from services.auth.password_service import hash_password

        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2


class TestVerifyPassword:
    """测试密码验证"""

    def test_verify_correct_password(self):
        """测试正确密码验证通过"""
        from services.auth.password_service import hash_password, verify_password

        password = "correct_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """测试错误密码验证不通过"""
        from services.auth.password_service import hash_password, verify_password

        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_empty_password(self):
        """测试空密码"""
        from services.auth.password_service import hash_password, verify_password

        hashed = hash_password("some_password")
        assert verify_password("", hashed) is False


class TestChangePassword:
    """测试密码修改"""

    @patch("services.auth.password_service.get_connection")
    def test_change_password_success(self, mock_get_conn):
        """测试密码修改成功"""
        from services.auth.password_service import hash_password, change_password

        # Mock 数据库连接
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (hash_password("old_pass"),)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = change_password(user_id=1, old_password="old_pass", new_password="new_pass_123")
        assert result["success"] is True

    @patch("services.auth.password_service.get_connection")
    def test_change_password_wrong_old(self, mock_get_conn):
        """测试原密码错误"""
        from services.auth.password_service import hash_password, change_password

        mock_cursor = MagicMock()
        # 返回不同的密码哈希
        mock_cursor.fetchone.return_value = (hash_password("actual_old_pass"),)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = change_password(user_id=1, old_password="wrong_old_pass", new_password="new_pass_123")
        assert result["success"] is False
        assert "原密码错误" in result["message"]

    @patch("services.auth.password_service.get_connection")
    def test_change_password_weak_new(self, mock_get_conn):
        """测试新密码太弱"""
        from services.auth.password_service import change_password

        result = change_password(user_id=1, old_password="old_pass", new_password="12")
        assert result["success"] is False
        assert "6" in result["message"]