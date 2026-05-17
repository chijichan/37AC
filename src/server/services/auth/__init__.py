# services/auth/__init__.py
"""用户认证子模块 - 提供认证相关的独立工具类"""

from services.auth.password_service import (
    hash_password,
    verify_password,
    change_password,
    generate_reset_token,
    validate_reset_token,
    reset_password,
)
# jwt_utils.py 中实际定义的是 generate_token / decode_token
# 为保持与 services/__init__.py 的兼容性，使用别名导出
from services.auth.jwt_utils import generate_token, decode_token
create_jwt_token = generate_token
decode_jwt_token = decode_token
from services.auth.validators import (
    validate_email,
    validate_username,
    validate_password,
)

__all__ = [
    "hash_password",
    "verify_password",
    "change_password",
    "generate_reset_token",
    "validate_reset_token",
    "reset_password",
    "create_jwt_token",
    "decode_jwt_token",
    "validate_email",
    "validate_username",
    "validate_password",
]
