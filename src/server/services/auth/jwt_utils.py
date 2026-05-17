"""JWT 令牌工具模块 - 提供 JWT 的生成和验证功能"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt

from config.base import JWT_SECRET, JWT_ALGORITHM


def generate_token(user_id: int, role: str, expires_in: int) -> str:
    """生成 JWT 令牌"""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT 令牌，返回 payload 或 None"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
