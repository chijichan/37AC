"""测试认证服务模块"""

from unittest.mock import patch, MagicMock, ANY

import pytest


class TestAuthService:
    """测试认证服务"""

    @patch("services.auth_service.get_connection")
    def test_register_success(self, mock_get_conn):
        """测试注册成功"""
        from services.auth_service import register

        # Mock 数据库连接 - 无重复用户
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # 用户名和邮箱都不存在
        mock_cursor.lastrowid = 1
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = register(username="newuser", password="password123", email="new@example.com")
        assert result["success"] is True
        assert result["data"]["user_id"] == 1
        assert result["data"]["username"] == "newuser"

    @patch("services.auth_service.get_connection")
    def test_register_duplicate_username(self, mock_get_conn):
        """测试重复用户名注册失败"""
        from services.auth_service import register

        # 第一次查询返回已存在的用户
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), None]  # 用户名存在, 邮箱不存在
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = register(username="existing", password="password123", email="new@example.com")
        assert result["success"] is False
        assert "用户名已存在" in result["message"]

    def test_register_weak_password(self):
        """测试弱密码注册失败"""
        from services.auth_service import register

        result = register(username="newuser", password="12", email="new@example.com")
        assert result["success"] is False

    def test_register_invalid_email(self):
        """测试无效邮箱注册失败"""
        from services.auth_service import register

        result = register(username="newuser", password="password123", email="notanemail")
        assert result["success"] is False
        assert "邮箱格式不正确" in result["message"]

    @patch("services.auth_service.get_connection")
    def test_login_success(self, mock_get_conn):
        """测试登录成功"""
        from services.auth_service import login, hash_password

        # Mock 数据库
        hashed = hash_password("correct_password")
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser",
            "password_hash": hashed, "role": "user", "status": 1,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = login(username="testuser", password="correct_password")
        assert result["success"] is True
        assert "access_token" in result["data"]
        assert "refresh_token" in result["data"]

    @patch("services.auth_service.get_connection")
    def test_login_wrong_password(self, mock_get_conn):
        """测试错误密码登录失败"""
        from services.auth_service import login, hash_password

        hashed = hash_password("correct_password")
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser",
            "password_hash": hashed, "role": "user", "status": 1,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = login(username="testuser", password="wrong_password")
        assert result["success"] is False
        assert "用户名或密码错误" in result["message"]

    @patch("services.auth_service.get_connection")
    def test_login_disabled_account(self, mock_get_conn):
        """测试禁用账号登录失败"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "disabled_user",
            "password_hash": "hash", "role": "user", "status": 0,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.auth_service import login
        result = login(username="disabled_user", password="any_password")
        assert result["success"] is False
        assert "禁用" in result["message"]

    @patch("services.auth_service.get_connection")
    def test_login_nonexistent_user(self, mock_get_conn):
        """测试不存在的用户登录"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        from services.auth_service import login
        result = login(username="nonexistent", password="any_password")
        assert result["success"] is False

    def test_refresh_token(self):
        """测试令牌刷新"""
        from services.auth_service import _generate_token, refresh_token

        # 生成有效的 refresh token
        refresh = _generate_token(user_id=1, role="user", expires_in=3600, token_type="refresh")
        result = refresh_token(refresh)
        assert result["success"] is True
        assert "access_token" in result["data"]

    def test_refresh_token_with_access_token(self):
        """测试使用 access token 刷新失败"""
        from services.auth_service import _generate_token, refresh_token

        access = _generate_token(user_id=1, role="user", expires_in=3600, token_type="access")
        result = refresh_token(access)
        assert result["success"] is False

    def test_refresh_expired_token(self):
        """测试过期 refresh token"""
        from services.auth_service import _generate_token, refresh_token

        expired = _generate_token(user_id=1, role="user", expires_in=0, token_type="refresh")
        import time
        time.sleep(0.1)
        result = refresh_token(expired)
        assert result["success"] is False