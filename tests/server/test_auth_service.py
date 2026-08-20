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
        # 第一次 fetchone 返回用户，第二次返回自增后的 token_version
        mock_cursor.fetchone.side_effect = [
            {
                "id": 1, "username": "testuser",
                "password_hash": hashed, "role": "user", "status": 1,
            },
            {"token_version": 1},
        ]
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

    @patch("services.auth_service.get_connection")
    def test_refresh_token(self, mock_get_conn):
        """测试令牌刷新"""
        from services.auth_service import _generate_token, refresh_token

        # Mock 数据库：用户存在、未禁用、token_version 与令牌一致
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "role": "user", "status": 1, "token_version": 0}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

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

    @patch("services.auth_service.get_connection")
    def test_refresh_token_version_mismatch(self, mock_get_conn):
        """测试刷新时 token_version 不一致拒绝刷新（旧登录已失效）"""
        from services.auth_service import _generate_token, refresh_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "status": 1, "token_version": 5}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 令牌携带 version=0，数据库当前为 5，不一致 → 拒绝
        refresh = _generate_token(user_id=1, role="user", expires_in=3600, token_type="refresh")
        result = refresh_token(refresh)
        assert result["success"] is False
        assert "其他设备登录" in result["message"]

    @patch("services.auth_service.get_connection")
    def test_verify_token_version_mismatch(self, mock_get_conn):
        """测试验证时 token_version 不一致令牌失效（单端登录）"""
        from services.auth_service import _generate_token, verify_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser", "role": "user", "status": 1, "token_version": 2,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 令牌携带 version=1，数据库当前为 2，不匹配 → 旧令牌失效
        token = _generate_token(user_id=1, role="user", expires_in=3600, token_type="access", token_version=1)
        result = verify_token(token)
        assert result["success"] is False
        assert "其他设备登录" in result["message"]

    @patch("services.auth_service.get_connection")
    def test_verify_token_version_match(self, mock_get_conn):
        """测试验证时 token_version 一致令牌有效"""
        from services.auth_service import _generate_token, verify_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "testuser", "role": "user", "status": 1, "token_version": 3,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        token = _generate_token(user_id=1, role="user", expires_in=3600, token_type="access", token_version=3)
        result = verify_token(token)
        assert result["success"] is True

    @patch("services.auth_service.get_connection")
    def test_login_increments_token_version(self, mock_get_conn):
        """测试每次登录 token_version 自增，旧登录令牌失效（单端登录核心）"""
        from services.auth_service import login, verify_token, hash_password

        hashed = hash_password("correct_password")
        user_row = {
            "id": 1, "username": "testuser",
            "password_hash": hashed, "role": "user", "status": 1,
        }

        # 第一次登录：token_version 自增为 1
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [user_row, {"token_version": 1}]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result1 = login(username="testuser", password="correct_password")
        assert result1["success"] is True
        token1 = result1["data"]["access_token"]

        # 第二次登录：token_version 自增为 2
        mock_cursor2 = MagicMock()
        mock_cursor2.fetchone.side_effect = [user_row, {"token_version": 2}]
        mock_conn2 = MagicMock()
        mock_conn2.cursor.return_value.__enter__.return_value = mock_cursor2
        mock_get_conn.return_value = mock_conn2

        result2 = login(username="testuser", password="correct_password")
        assert result2["success"] is True
        token2 = result2["data"]["access_token"]

        # 数据库当前 token_version = 2
        mock_cursor3 = MagicMock()
        mock_cursor3.fetchone.return_value = {
            "id": 1, "username": "testuser", "role": "user", "status": 1, "token_version": 2,
        }
        mock_conn3 = MagicMock()
        mock_conn3.cursor.return_value.__enter__.return_value = mock_cursor3
        mock_get_conn.return_value = mock_conn3

        # 第一次登录的令牌（version=1）已失效
        r1 = verify_token(token1)
        assert r1["success"] is False
        assert "其他设备登录" in r1["message"]

        # 第二次登录的令牌（version=2）仍有效
        r2 = verify_token(token2)
        assert r2["success"] is True