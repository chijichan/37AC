"""测试服务器验证工具模块"""

import pytest

from services.auth.validators import (
    validate_email,
    validate_username,
    validate_password,
)


class TestValidateEmail:
    """测试邮箱验证"""

    @pytest.mark.parametrize("email,expected", [
        ("user@example.com", True),
        ("test.user@domain.co.jp", True),
        ("user+tag@example.org", True),
        ("a@b.cd", True),
        ("", False),
        ("notanemail", False),
        ("@domain.com", False),
        ("user@", False),
        ("user@.com", False),
        ("user@domain", False),  # 缺少顶级域名
    ])
    def test_email_validation(self, email, expected):
        """测试各种邮箱格式"""
        assert validate_email(email) == expected


class TestValidateUsername:
    """测试用户名验证"""

    @pytest.mark.parametrize("username,expected_valid", [
        ("testuser", True),
        ("测试用户", True),
        ("user_123", True),
        ("ab", False),       # 太短
        ("a" * 51, False),  # 太长
        ("user name", False),  # 含空格
        ("user@name", False),  # 含特殊字符
    ])
    def test_username_validation(self, username, expected_valid):
        """测试各种用户名格式"""
        valid, msg = validate_username(username)
        assert valid == expected_valid, f"用户名 '{username}' 预期 {'有效' if expected_valid else '无效'}, 消息: {msg}"

    def test_username_error_message(self):
        """测试错误消息"""
        valid, msg = validate_username("ab")
        assert valid is False
        assert "3" in msg  # 应包含长度信息


class TestValidatePassword:
    """测试密码验证"""

    @pytest.mark.parametrize("password,expected_valid", [
        ("123456", True),
        ("a" * 128, True),
        ("abc123!@#", True),
        ("12345", False),     # 太短
        ("a" * 129, False),  # 太长
    ])
    def test_password_validation(self, password, expected_valid):
        """测试各种密码长度"""
        valid, msg = validate_password(password)
        assert valid == expected_valid, f"密码长度={len(password)}, 预期: {expected_valid}, 消息: {msg}"

    def test_password_error_message(self):
        """测试错误消息"""
        valid, msg = validate_password("12345")
        assert valid is False
        assert "6" in msg  # 应包含长度下限