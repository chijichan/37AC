"""验证工具模块 - 提供用户名、密码、邮箱等格式验证"""

import re


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str) -> tuple:
    """验证用户名，返回 (是否合法, 错误信息)"""
    if len(username) < 3 or len(username) > 50:
        return False, "用户名长度必须在3-50个字符之间"
    if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", username):
        return False, "用户名只能包含字母、数字、下划线和中文"
    return True, ""


def validate_password(password: str) -> tuple:
    """验证密码强度，返回 (是否合法, 错误信息)"""
    if len(password) < 6 or len(password) > 128:
        return False, "密码长度必须在6-128个字符之间"
    return True, ""
