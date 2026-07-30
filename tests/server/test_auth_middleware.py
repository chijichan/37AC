"""测试认证中间件"""

import json
from unittest.mock import patch, MagicMock

import pytest


class TestAuthMiddleware:
    """测试认证中间件"""

    def test_extract_token_from_header(self):
        """测试从 Authorization 头提取令牌"""
        from middleware.auth_middleware import _extract_token

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": "Bearer test_token_123"}
            mock_request.args = {}
            mock_request.cookies = {}
            token = _extract_token()
            assert token == "test_token_123"

    def test_extract_token_from_query(self):
        """测试从查询参数提取令牌"""
        from middleware.auth_middleware import _extract_token

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": ""}
            mock_request.args = {"token": "query_token_456"}
            mock_request.cookies = {}
            token = _extract_token()
            assert token == "query_token_456"

    def test_extract_token_from_cookie(self):
        """测试从 Cookie 提取令牌"""
        from middleware.auth_middleware import _extract_token

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": ""}
            mock_request.args = {}
            mock_request.cookies = {"access_token": "cookie_token_789"}
            token = _extract_token()
            assert token == "cookie_token_789"

    def test_extract_token_missing(self):
        """测试无令牌时返回 None"""
        from middleware.auth_middleware import _extract_token

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": ""}
            mock_request.args = {}
            mock_request.cookies = {}
            token = _extract_token()
            assert token is None

    def test_login_required_no_token(self):
        """测试未提供令牌"""
        from middleware.auth_middleware import login_required

        @login_required
        def dummy_route():
            return "ok"

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": ""}
            mock_request.args = {}
            mock_request.cookies = {}

            response = dummy_route()
            # 应返回 401 JSON 响应
            assert isinstance(response, tuple)
            data, status = response
            assert status == 401
            assert data.json["message"] == "未提供认证令牌"

    @patch("middleware.auth_middleware.decode_token")
    def test_login_required_refresh_token(self, mock_decode):
        """测试拒绝 refresh token"""
        from middleware.auth_middleware import login_required

        mock_decode.return_value = {"user_id": 1, "role": "user", "type": "refresh"}

        @login_required
        def dummy_route():
            return "ok"

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": "Bearer refresh_token_here"}
            mock_request.args = {}
            mock_request.cookies = {}

            response = dummy_route()
            assert isinstance(response, tuple)
            data, status = response
            assert status == 401
            assert "访问令牌" in data.json["message"]

    @patch("middleware.auth_middleware.decode_token")
    def test_login_required_valid_token(self, mock_decode):
        """测试有效令牌"""
        from middleware.auth_middleware import login_required

        mock_decode.return_value = {"user_id": 1, "role": "user", "type": "access"}

        @login_required
        def dummy_route():
            from flask import g
            return f"user_{g.user_id}"

        with patch("middleware.auth_middleware.request") as mock_request, \
             patch("middleware.auth_middleware.g") as mock_g:
            mock_request.headers = {"Authorization": "Bearer valid_token"}
            mock_request.args = {}
            mock_request.cookies = {}
            mock_g.user_id = 1
            mock_g.user_role = "user"

            result = dummy_route()
            assert result == "user_1"

    def test_admin_required_no_token(self):
        """测试管理员路由无令牌"""
        from middleware.auth_middleware import admin_required

        @admin_required
        def admin_route():
            return "admin"

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": ""}
            mock_request.args = {}
            mock_request.cookies = {}

            response = admin_route()
            data, status = response
            assert status == 401

    @patch("middleware.auth_middleware.decode_token")
    def test_admin_required_not_admin(self, mock_decode):
        """测试非管理员访问管理员路由"""
        from middleware.auth_middleware import admin_required

        mock_decode.return_value = {"user_id": 1, "role": "user", "type": "access"}

        @admin_required
        def admin_route():
            return "admin"

        with patch("middleware.auth_middleware.request") as mock_request:
            mock_request.headers = {"Authorization": "Bearer user_token"}
            mock_request.args = {}
            mock_request.cookies = {}

            response = admin_route()
            data, status = response
            assert status == 403
            assert "管理员" in data.json["message"]