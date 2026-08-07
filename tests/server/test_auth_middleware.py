"""测试认证中间件

说明：使用 Flask 的 test_request_context 提供请求上下文，
避免直接 mock flask.request（Werkzeug 3.x 下 LocalProxy 无法被 mock）。
"""

from unittest.mock import patch

from flask import Flask

app = Flask(__name__)


class TestAuthMiddleware:
    """测试认证中间件"""

    def test_extract_token_from_header(self):
        """测试从 Authorization 头提取令牌"""
        from middleware.auth_middleware import _extract_token

        with app.test_request_context(
            headers={"Authorization": "Bearer test_token_123"}
        ):
            token = _extract_token()
            assert token == "test_token_123"

    def test_extract_token_from_query(self):
        """测试从查询参数提取令牌"""
        from middleware.auth_middleware import _extract_token

        with app.test_request_context(query_string={"token": "query_token_456"}):
            token = _extract_token()
            assert token == "query_token_456"

    def test_extract_token_from_cookie(self):
        """测试从 Cookie 提取令牌"""
        from middleware.auth_middleware import _extract_token

        with app.test_request_context(
            headers={"Cookie": "access_token=cookie_token_789"}
        ):
            token = _extract_token()
            assert token == "cookie_token_789"

    def test_extract_token_missing(self):
        """测试无令牌时返回 None"""
        from middleware.auth_middleware import _extract_token

        with app.test_request_context():
            token = _extract_token()
            assert token is None

    def test_login_required_no_token(self):
        """测试未提供令牌"""
        from middleware.auth_middleware import login_required

        @login_required
        def dummy_route():
            return "ok"

        with app.test_request_context():
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

        with app.test_request_context(
            headers={"Authorization": "Bearer refresh_token_here"}
        ):
            response = dummy_route()
            assert isinstance(response, tuple)
            data, status = response
            assert status == 401
            assert "访问令牌" in data.json["message"]

    @patch("middleware.auth_middleware.verify_token")
    @patch("middleware.auth_middleware.decode_token")
    def test_login_required_valid_token(self, mock_decode, mock_verify):
        """测试有效令牌"""
        from middleware.auth_middleware import login_required

        mock_decode.return_value = {"user_id": 1, "role": "user", "type": "access"}
        mock_verify.return_value = {"success": True, "message": "令牌有效"}

        @login_required
        def dummy_route():
            from flask import g
            return f"user_{g.user_id}"

        with app.test_request_context(
            headers={"Authorization": "Bearer valid_token"}
        ):
            result = dummy_route()
            assert result == "user_1"

    def test_admin_required_no_token(self):
        """测试管理员路由无令牌"""
        from middleware.auth_middleware import admin_required

        @admin_required
        def admin_route():
            return "admin"

        with app.test_request_context():
            response = admin_route()
            data, status = response
            assert status == 401

    @patch("middleware.auth_middleware.verify_token")
    @patch("middleware.auth_middleware.decode_token")
    def test_admin_required_not_admin(self, mock_decode, mock_verify):
        """测试非管理员访问管理员路由"""
        from middleware.auth_middleware import admin_required

        mock_decode.return_value = {"user_id": 1, "role": "user", "type": "access"}
        mock_verify.return_value = {"success": True, "message": "令牌有效"}

        @admin_required
        def admin_route():
            return "admin"

        with app.test_request_context(
            headers={"Authorization": "Bearer user_token"}
        ):
            response = admin_route()
            data, status = response
            assert status == 403
            assert "管理员" in data.json["message"]

    @patch("middleware.auth_middleware.verify_token")
    @patch("middleware.auth_middleware.decode_token")
    def test_admin_required_admin_ok(self, mock_decode, mock_verify):
        """测试管理员访问管理员路由成功"""
        from middleware.auth_middleware import admin_required

        mock_decode.return_value = {"user_id": 1, "role": "admin", "type": "access"}
        mock_verify.return_value = {"success": True, "message": "令牌有效"}

        @admin_required
        def admin_route():
            return "admin"

        with app.test_request_context(
            headers={"Authorization": "Bearer admin_token"}
        ):
            result = admin_route()
            assert result == "admin"

    @patch("middleware.auth_middleware.decode_token")
    def test_optional_login_valid(self, mock_decode):
        """测试可选登录：有 token 时设置用户上下文"""
        from middleware.auth_middleware import optional_login

        mock_decode.return_value = {"user_id": 7, "role": "user"}

        @optional_login
        def dummy_route():
            from flask import g
            return f"user_{getattr(g, 'user_id', None)}"

        with app.test_request_context(
            headers={"Authorization": "Bearer some_token"}
        ):
            result = dummy_route()
            assert result == "user_7"

    def test_optional_login_no_token(self):
        """测试可选登录：无 token 时不阻止请求"""
        from middleware.auth_middleware import optional_login

        @optional_login
        def dummy_route():
            return "ok"

        with app.test_request_context():
            assert dummy_route() == "ok"
