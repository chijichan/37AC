# services/auth_service.py
"""用户认证服务 - 提供用户注册、登录、JWT令牌管理等功能"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone

import jwt
import pymysql

from config import (
    DB_CONFIG,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRES,
    JWT_REFRESH_TOKEN_EXPIRES,
)


def _get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def _hash_password(password: str) -> str:
    """使用 SHA-256 哈希密码"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return _hash_password(password) == password_hash


def _generate_token(user_id: int, role: str, expires_in: int) -> str:
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


def register(username: str, password: str, email: str) -> dict:
    """用户注册"""
    # 验证用户名
    valid, msg = validate_username(username)
    if not valid:
        return {"success": False, "message": msg}

    # 验证密码
    valid, msg = validate_password(password)
    if not valid:
        return {"success": False, "message": msg}

    # 验证邮箱
    if not email:
        return {"success": False, "message": "邮箱不能为空"}
    if not validate_email(email):
        return {"success": False, "message": "邮箱格式不正确"}

    password_hash = _hash_password(password)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {"success": False, "message": "用户名已存在"}

            # 检查邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {"success": False, "message": "邮箱已被注册"}

            # 插入新用户
            cursor.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
                (username, password_hash, email),
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
    conn = None
    try:
        conn = _get_connection()
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

        if not _verify_password(password, user["password_hash"]):
            return {"success": False, "message": "用户名或密码错误"}

        # 更新最后登录时间和IP
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login_at = NOW(), last_login_ip = %s WHERE id = %s",
                (ip or "0.0.0.0", user["id"]),
            )
            conn.commit()

        # 生成令牌
        access_token = _generate_token(
            user["id"], user["role"], JWT_ACCESS_TOKEN_EXPIRES
        )
        refresh_token = _generate_token(
            user["id"], user["role"], JWT_REFRESH_TOKEN_EXPIRES
        )

        return {
            "success": True,
            "message": "登录成功",
            "data": {
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "access_token": access_token,
                "refresh_token": refresh_token,
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

    user_id = payload.get("user_id")
    role = payload.get("role")

    # 生成新的访问令牌
    new_access_token = _generate_token(user_id, role, JWT_ACCESS_TOKEN_EXPIRES)

    return {
        "success": True,
        "message": "令牌刷新成功",
        "data": {
            "access_token": new_access_token,
            "expires_in": JWT_ACCESS_TOKEN_EXPIRES,
        },
    }


def get_user_by_id(user_id: int) -> dict:
    """根据用户ID获取用户信息"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT id, username, email, role, status,
                          last_login_at, last_login_ip, created_at, updated_at
                   FROM users WHERE id = %s""",
                (user_id,),
            )
            user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "用户不存在"}

        # 格式化日期时间字段
        for field in ["last_login_at", "created_at", "updated_at"]:
            if user.get(field) and hasattr(user[field], "strftime"):
                user[field] = user[field].strftime("%Y-%m-%d %H:%M:%S")

        return {"success": True, "data": user}
    except Exception as e:
        return {"success": False, "message": f"获取用户信息失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def update_profile(user_id: int, data: dict) -> dict:
    """更新用户个人资料"""
    allowed_fields = {"email", "avatar", "username"}
    update_fields = []
    update_values = []

    for field in allowed_fields:
        if field in data:
            if field == "email" and data[field] and not validate_email(data[field]):
                return {"success": False, "message": "邮箱格式不正确"}
            update_fields.append(f"{field} = %s")
            update_values.append(data[field])

    if not update_fields:
        return {"success": False, "message": "没有需要更新的字段"}

    update_values.append(user_id)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            # 如果更新邮箱，检查是否已被使用
            if "email" in data and data["email"]:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (data["email"], user_id),
                )
                if cursor.fetchone():
                    return {"success": False, "message": "邮箱已被其他用户使用"}

            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, update_values)
            conn.commit()

        return {"success": True, "message": "更新成功"}
    except Exception as e:
        return {"success": False, "message": f"更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    # 验证新密码
    valid, msg = validate_password(new_password)
    if not valid:
        return {"success": False, "message": msg}

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "message": "用户不存在"}

            if not _verify_password(old_password, row[0]):
                return {"success": False, "message": "原密码错误"}

            new_hash = _hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
            conn.commit()

        return {"success": True, "message": "密码修改成功"}
    except Exception as e:
        return {"success": False, "message": f"密码修改失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def get_users(page: int = 1, per_page: int = 20, keyword: str = None) -> dict:
    """获取用户列表（管理员）"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 构建查询条件
            where_clause = ""
            params = []
            if keyword:
                where_clause = "WHERE username LIKE %s OR email LIKE %s"
                like_keyword = f"%{keyword}%"
                params = [like_keyword, like_keyword]

            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM users {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 查询分页数据
            offset = (page - 1) * per_page
            sql = f"""SELECT id, username, email, role, status, avatar,
                             last_login_at, last_login_ip, created_at, updated_at
                      FROM users {where_clause}
                      ORDER BY created_at DESC
                      LIMIT %s OFFSET %s"""
            cursor.execute(sql, params + [per_page, offset])
            users = cursor.fetchall()

        # 格式化日期时间字段
        for user in users:
            for field in ["last_login_at", "created_at", "updated_at"]:
                if user.get(field) and hasattr(user[field], "strftime"):
                    user[field] = user[field].strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "data": {
                "users": users,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        }
    except Exception as e:
        return {"success": False, "message": f"获取用户列表失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def create_user(
    username: str, password: str, email: str = None, role: str = "user"
) -> dict:
    """创建用户（管理员）"""
    # 验证用户名
    valid, msg = validate_username(username)
    if not valid:
        return {"success": False, "message": msg}

    # 验证密码
    valid, msg = validate_password(password)
    if not valid:
        return {"success": False, "message": msg}

    # 验证邮箱
    if email and not validate_email(email):
        return {"success": False, "message": "邮箱格式不正确"}

    # 验证角色
    if role not in ("admin", "user"):
        return {"success": False, "message": "角色无效"}

    password_hash = _hash_password(password)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {"success": False, "message": "用户名已存在"}

            if email:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return {"success": False, "message": "邮箱已被注册"}

            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                (username, password_hash, email, role),
            )
            conn.commit()

        return {
            "success": True,
            "message": "用户创建成功",
            "data": {"user_id": cursor.lastrowid},
        }
    except Exception as e:
        return {"success": False, "message": f"创建用户失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def update_user(user_id: int, data: dict) -> dict:
    """更新用户信息（管理员）"""
    allowed_fields = {"email", "role", "status", "avatar"}
    update_fields = []
    update_values = []

    for field in allowed_fields:
        if field in data:
            if field == "email" and data[field] and not validate_email(data[field]):
                return {"success": False, "message": "邮箱格式不正确"}
            if field == "role" and data[field] not in ("admin", "user"):
                return {"success": False, "message": "角色无效"}
            if field == "status":
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    return {"success": False, "message": "状态值无效"}
                if data[field] not in (0, 1):
                    return {"success": False, "message": "状态值无效"}
            update_fields.append(f"{field} = %s")
            update_values.append(data[field])

    if not update_fields:
        return {"success": False, "message": "没有需要更新的字段"}

    update_values.append(user_id)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            if "email" in data and data["email"]:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (data["email"], user_id),
                )
                if cursor.fetchone():
                    return {"success": False, "message": "邮箱已被其他用户使用"}

            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, update_values)
            conn.commit()

        return {"success": True, "message": "用户更新成功"}
    except Exception as e:
        return {"success": False, "message": f"更新用户失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def delete_user(user_id: int) -> dict:
    """删除用户（管理员）"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return {"success": False, "message": "用户不存在"}

            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()

        return {"success": True, "message": "用户已删除"}
    except Exception as e:
        return {"success": False, "message": f"删除用户失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def update_user_role(user_id: int, role: str) -> dict:
    """分配用户角色（管理员）"""
    if role not in ("admin", "user"):
        return {"success": False, "message": "角色无效"}

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return {"success": False, "message": "用户不存在"}

            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
            conn.commit()

        return {"success": True, "message": "角色更新成功"}
    except Exception as e:
        return {"success": False, "message": f"角色更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def update_user_status(user_id: int, status: int) -> dict:
    """修改用户状态（管理员）"""
    if status not in (0, 1):
        return {"success": False, "message": "状态值无效"}

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return {"success": False, "message": "用户不存在"}

            cursor.execute(
                "UPDATE users SET status = %s WHERE id = %s", (status, user_id)
            )
            conn.commit()

        status_text = "启用" if status == 1 else "禁用"
        return {"success": True, "message": f"用户已{status_text}"}
    except Exception as e:
        return {"success": False, "message": f"状态更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
