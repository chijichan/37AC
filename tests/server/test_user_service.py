"""测试用户服务模块"""

from unittest.mock import patch, MagicMock

import pytest


class TestGetUserById:
    """测试根据 ID 获取用户"""

    @patch("services.user_service._get_connection")
    def test_get_existing_user(self, mock_get_conn):
        """测试获取存在的用户"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser", "email": "test@example.com",
            "role": "user", "status": 1,
            "last_login_at": None, "last_login_ip": "127.0.0.1",
            "created_at": None, "updated_at": None,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.user_service import get_user_by_id
        result = get_user_by_id(1)
        assert result["success"] is True
        assert result["data"]["username"] == "testuser"

    @patch("services.user_service._get_connection")
    def test_get_nonexistent_user(self, mock_get_conn):
        """测试获取不存在的用户"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.user_service import get_user_by_id
        result = get_user_by_id(999)
        assert result["success"] is False


class TestUpdateProfile:
    """测试更新用户资料"""

    @patch("services.user_service._get_connection")
    def test_update_email(self, mock_get_conn):
        """测试更新邮箱"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # 邮箱不重复
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.user_service import update_profile
        result = update_profile(1, {"email": "new@example.com"})
        assert result["success"] is True

    @patch("services.user_service._get_connection")
    def test_update_duplicate_email(self, mock_get_conn):
        """测试更新为已存在的邮箱"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 2}  # 邮箱已被其他用户使用
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.user_service import update_profile
        result = update_profile(1, {"email": "existing@example.com"})
        assert result["success"] is False
        assert "已被" in result["message"]

    def test_update_invalid_email(self):
        """测试更新为无效邮箱"""
        from services.user_service import update_profile
        result = update_profile(1, {"email": "invalid"})
        assert result["success"] is False


class TestGetUsers:
    """测试获取用户列表"""

    @patch("services.user_service._get_connection")
    def test_get_users_list(self, mock_get_conn):
        """测试获取用户列表"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"total": 1}
        mock_cursor.fetchall.return_value = [{
            "id": 1, "username": "testuser", "email": "test@example.com",
            "role": "user", "status": 1,
            "last_login_at": None, "last_login_ip": "127.0.0.1",
            "created_at": None, "updated_at": None,
        }]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.user_service import get_users
        result = get_users(page=1, per_page=20)
        assert result["success"] is True
        assert len(result["data"]["users"]) == 1
        assert result["data"]["total"] == 1