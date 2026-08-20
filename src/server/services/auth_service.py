"""用户认证服务 - 提供用户注册、登录、JWT令牌管理等功能"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
import pymysql

from config.base import (
    DB_CONFIG,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRES,
    JWT_REFRESH_TOKEN_EXPIRES,
)
from config.log_config import get_logger
from services.auth.password_service import hash_password, verify_password
from services.auth.validators import validate_email, validate_username, validate_password
from services.db import get_connection

logger = get_logger("auth_service")


def _generate_token(user_id: int, role: str, expires_in: int, token_type: str = "access", token_version: int = 0) -> str:
    """生成 JWT 令牌"""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "role": role,
        "type": token_type,
        "token_version": token_version,
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


def verify_token(token: str) -> dict:
    """验证 JWT 令牌并检查用户状态（含单端登录版本校验）"""
    payload = decode_token(token)
    if not payload:
        return {"success": False, "message": "令牌无效或已过期"}

    user_id = payload.get("user_id")
    token_version = payload.get("token_version", 0)

    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id, username, role, status, token_version FROM users WHERE id = %s",
                (user_id,),
            )
            user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "用户不存在"}

        if user["status"] == 0:
            return {"success": False, "message": "账号已被禁用"}

        # 单端登录：令牌携带的版本号必须与数据库当前版本一致，
        # 不一致说明该用户已在其他设备重新登录，此令牌已失效
        if user["token_version"] != token_version:
            return {"success": False, "message": "账号已在其他设备登录，请重新登录"}

        return {
            "success": True,
            "message": "令牌有效",
            "data": {
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
            },
        }
    except Exception as e:
        return {"success": False, "message": f"验证失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def register(username: str, password: str, email: str) -> dict:
    """用户注册"""
    valid, msg = validate_username(username)
    if not valid:
        return {"success": False, "message": msg}

    valid, msg = validate_password(password)
    if not valid:
        return {"success": False, "message": msg}

    if not email:
        return {"success": False, "message": "邮箱不能为空"}
    if not validate_email(email):
        return {"success": False, "message": "邮箱格式不正确"}

    password_hash_value = hash_password(password)

    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {"success": False, "message": "用户名已存在"}

            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {"success": False, "message": "邮箱已被注册"}

            cursor.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
                (username, password_hash_value, email),
            )
            conn.commit()
            user_id = cursor.lastrowid

        return {
            "success": True,
            "message": "注册成功",
            "data": {"user_id": user_id, "username": username},
        }
    except Exception as e:
        return {"success": False, "message": f"注册失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def login(username: str, password: str, ip: str = None) -> dict:
    """用户登录"""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id, username, password_hash, role, status FROM users WHERE username = %s",
                (username,),
            )
            user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "用户名或密码错误"}

        if user["status"] == 0:
            return {"success": False, "message": "账号已被禁用，请联系管理员"}

        if not verify_password(password, user["password_hash"]):
            return {"success": False, "message": "用户名或密码错误"}

        # 单端登录：每次登录将 token_version 自增，使旧登录立即失效
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "UPDATE users SET token_version = token_version + 1 WHERE id = %s",
                (user["id"],),
            )
            cursor.execute(
                "SELECT token_version FROM users WHERE id = %s",
                (user["id"],),
            )
            new_version = cursor.fetchone()["token_version"]
            cursor.execute(
                "UPDATE users SET last_login_at = NOW(), last_login_ip = %s WHERE id = %s",
                (ip or "0.0.0.0", user["id"]),
            )
            conn.commit()

        access_token = _generate_token(
            user["id"], user["role"], JWT_ACCESS_TOKEN_EXPIRES, "access", new_version
        )
        refresh_token_value = _generate_token(
            user["id"], user["role"], JWT_REFRESH_TOKEN_EXPIRES, "refresh", new_version
        )

        return {
            "success": True,
            "message": "登录成功",
            "data": {
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "access_token": access_token,
                "refresh_token": refresh_token_value,
                "expires_in": JWT_ACCESS_TOKEN_EXPIRES,
            },
        }
    except Exception as e:
        return {"success": False, "message": f"登录失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def refresh_token(refresh_token_str: str) -> dict:
    """刷新访问令牌"""
    payload = decode_token(refresh_token_str)
    if not payload:
        return {"success": False, "message": "刷新令牌无效或已过期"}

    # 只允许 refresh token 用于刷新，拒绝 access token
    if payload.get("type") != "refresh":
        return {"success": False, "message": "请使用刷新令牌而非访问令牌"}

    user_id = payload.get("user_id")
    role = payload.get("role")
    token_version = payload.get("token_version", 0)

    # 验证用户是否仍存在且未被禁用
    conn = get_connection()
    if conn:
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id, role, status, token_version FROM users WHERE id = %s",
                    (user_id,),
                )
                user = cursor.fetchone()
            if not user:
                return {"success": False, "message": "用户不存在"}
            if user["status"] == 0:
                return {"success": False, "message": "账号已被禁用"}
            # 单端登录：版本不一致则旧登录已失效，拒绝刷新
            if user["token_version"] != token_version:
                return {"success": False, "message": "账号已在其他设备登录，请重新登录"}
            # 以数据库最新角色为准，避免降权后旧 refresh token 继续拿到 admin token
            role = user["role"]
        except Exception as e:
            return {"success": False, "message": f"验证失败: {str(e)}"}
        finally:
            conn.close()
    else:
        return {"success": False, "message": "数据库连接失败"}

    # 生成新的访问令牌
    new_access_token = _generate_token(user_id, role, JWT_ACCESS_TOKEN_EXPIRES, "access", token_version)

    return {
        "success": True,
        "message": "令牌刷新成功",
        "data": {
            "access_token": new_access_token,
            "expires_in": JWT_ACCESS_TOKEN_EXPIRES,
        },
    }


# === 以下委托函数供 admin_routes / user_routes 引用 ===
from services.user_service import (  # noqa: E402, F401
    update_profile,
    get_user_by_id,
    get_users,
    create_user,
    update_user,
    delete_user,
    update_user_role,
    update_user_status,
)
from services.auth.password_service import (  # noqa: E402, F401
    change_password,
    generate_reset_token,
    validate_reset_token,
    reset_password,
)
