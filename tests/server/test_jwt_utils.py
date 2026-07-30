"""测试 JWT 工具模块"""

import time
from unittest.mock import patch

import pytest
import jwt as pyjwt


class TestGenerateToken:
    """测试 JWT 令牌生成"""

    def test_generate_token_returns_string(self):
        """测试生成令牌返回字符串"""
        from services.auth.jwt_utils import generate_token

        token = generate_token(user_id=1, role="user", expires_in=3600)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_decodable(self):
        """测试生成的令牌可解码"""
        from services.auth.jwt_utils import generate_token, decode_token

        token = generate_token(user_id=42, role="admin", expires_in=3600)
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["role"] == "admin"

    def test_generate_token_has_jti(self):
        """测试令牌包含 jti"""
        from services.auth.jwt_utils import generate_token, decode_token

        token = generate_token(user_id=1, role="user", expires_in=3600)
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_generate_token_unique_jti(self):
        """测试两次生成的 jti 不同"""
        from services.auth.jwt_utils import generate_token, decode_token

        token1 = generate_token(user_id=1, role="user", expires_in=3600)
        token2 = generate_token(user_id=1, role="user", expires_in=3600)
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        assert payload1["jti"] != payload2["jti"]


class TestDecodeToken:
    """测试 JWT 令牌解码"""

    def test_decode_valid_token(self):
        """测试解码有效令牌"""
        from services.auth.jwt_utils import generate_token, decode_token

        token = generate_token(user_id=1, role="user", expires_in=3600)
        payload = decode_token(token)
        assert payload is not None
        assert "user_id" in payload
        assert "role" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_expired_token(self):
        """测试过期令牌"""
        from services.auth.jwt_utils import generate_token, decode_token

        # 生成立即过期的令牌
        token = generate_token(user_id=1, role="user", expires_in=0)
        # 等待一小段时间确保过期
        time.sleep(0.1)
        payload = decode_token(token)
        assert payload is None

    def test_decode_invalid_token(self):
        """测试无效令牌"""
        from services.auth.jwt_utils import decode_token

        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        """测试空令牌"""
        from services.auth.jwt_utils import decode_token

        payload = decode_token("")
        assert payload is None

    def test_decode_tampered_token(self):
        """测试被篡改的令牌"""
        from services.auth.jwt_utils import generate_token, decode_token

        token = generate_token(user_id=1, role="user", expires_in=3600)
        # 篡改令牌
        parts = token.split(".")
        if len(parts) == 3:
            tampered = parts[0] + "." + parts[1] + ".invalidsignature"
            payload = decode_token(tampered)
            assert payload is None