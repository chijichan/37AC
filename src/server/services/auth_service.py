# services/auth_service.py
"""用户认证服务 - 提供用户注册、登录、JWT令牌管理等功能"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone

import jwt
import pymysql

from config.base import (
    DB_CONFIG,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRES,
    JWT_REFRESH_TOKEN_EXPIRES,
    FRONTEND_URL,
)
from config.email_config import RESET_RATE_LIMIT
from services.email_service import is_configured as smtp_is_configured, send_password_reset_email
from config.log_config import get_logger

logger = get_logger("auth_service")


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


def _count_recent_reset_requests(email: str) -> int:
    """统计指定邮箱在限流时间窗口内的重置请求次数"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            window_minutes = RESET_RATE_LIMIT.get("window_minutes", 15)
            cursor.execute(
                """SELECT COUNT(*) FROM password_reset_tokens prt
                   JOIN users u ON u.id = prt.user_id
                   WHERE u.email = %s AND prt.created_at >= NOW() - INTERVAL %s MINUTE""",
                (email, window_minutes),
            )
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.warning("检查重置请求频率时出错: %s", str(e))
        return 0
    finally:
        if conn:
            conn.close()


def _cleanup_expired_tokens() -> int:
    """清理已过期且未使用的重置令牌，返回清理数量"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM password_reset_tokens WHERE expires_at < NOW() AND used = 0"
            )
            conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info("已清理 %d 条过期的密码重置令牌", deleted)
            return deleted
    except Exception as e:
        logger.warning("清理过期令牌时出错: %s", str(e))
        return 0
    finally:
        if conn:
            conn.close()


def generate_reset_token(email: str) -> dict:
    """生成密码重置令牌并发送邮件（如果 SMTP 已配置）"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        if not user:
            # 出于安全考虑，不暴露邮箱是否存在，但返回成功
            return {
                "success": True,
                "message": "如果该邮箱已注册，重置链接将发送到你的邮箱",
                "data": {"token": None}
            }

        # 速率限制检查
        recent_count = _count_recent_reset_requests(email)
        max_requests = RESET_RATE_LIMIT.get("max_requests", 3)
        window_minutes = RESET_RATE_LIMIT.get("window_minutes", 15)

        if recent_count >= max_requests:
            logger.warning("邮箱 %s 请求过于频繁 (%d 次 / %d 分钟)", email, recent_count, window_minutes)
            return {
                "success": False,
                "message": f"请求过于频繁，请 {window_minutes} 分钟后再试",
                "data": {"retry_after_minutes": window_minutes}
            }

        # 顺便清理过期令牌
        _cleanup_expired_tokens()

        # 生成随机令牌
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # 设置过期时间（1小时，使用系统本地时间）
        expires_at = datetime.now() + timedelta(hours=1)
        expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

        # 将旧令牌标记为已使用
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE user_id = %s AND used = 0",
                (user["id"],),
            )

            # 插入新令牌
            cursor.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user["id"], token_hash, expires_at_str),
            )
            conn.commit()

        # 尝试发送邮件
        if smtp_is_configured():
            # 使用配置的前端地址构建重置链接
            reset_url = f"{FRONTEND_URL}/auth/reset-password?token={raw_token}"
            # 发送密码重置邮件
            email_result = send_password_reset_email(
                to_email=user["email"],
                username=user["username"],
                reset_url=reset_url,
                expires_at=expires_at_str
            )

            if email_result["success"]:
                return {
                    "success": True,
                    "message": "重置链接已发送到你的邮箱，请查收",
                    "data": {"token": None}  # 邮件发送成功，不返回令牌
                }
            else:
                # 邮件发送失败，记录错误但不影响令牌生成
                logger.error("发送密码重置邮件失败: %s", email_result["message"])
                # 降级为直接返回令牌（开发模式）
                return {
                    "success": True,
                    "message": f"邮件发送失败({email_result['message']})，但已生成重置令牌",
                    "data": {
                        "token": raw_token,
                        "user_id": user["id"],
                        "expires_at": expires_at_str
                    }
                }
        else:
            # SMTP 未配置，开发模式：直接返回令牌
            return {
                "success": True,
                "message": "SMTP 未配置，重置令牌已生成（仅开发/调试模式）",
                "data": {
                    "token": raw_token,
                    "user_id": user["id"],
                    "expires_at": expires_at_str
                }
            }
    except Exception as e:
        return {"success": False, "message": f"生成重置令牌失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def validate_reset_token(token: str) -> dict:
    """验证重置令牌是否有效"""
    if not token:
        return {"success": False, "message": "重置令牌不能为空"}

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT prt.id, prt.user_id, prt.expires_at, u.username
                   FROM password_reset_tokens prt
                   JOIN users u ON u.id = prt.user_id
                   WHERE prt.token = %s AND prt.used = 0""",
                (token_hash,),
            )
            reset_record = cursor.fetchone()

        if not reset_record:
            return {"success": False, "message": "重置令牌无效或已被使用"}

        # 检查是否过期
        expires_at = reset_record["expires_at"]
        if hasattr(expires_at, "strftime"):
            # 已经是 datetime 对象
            expires_dt = expires_at
        else:
            expires_dt = datetime.strptime(str(expires_at), "%Y-%m-%d %H:%M:%S")

        if expires_dt < datetime.now():
            return {"success": False, "message": "重置令牌已过期，请重新申请"}

        return {
            "success": True,
            "data": {
                "token_id": reset_record["id"],
                "user_id": reset_record["user_id"],
                "username": reset_record["username"],
            }
        }
    except Exception as e:
        return {"success": False, "message": f"验证令牌失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def reset_password(token: str, new_password: str) -> dict:
    """使用重置令牌重置密码"""
    # 验证新密码
    valid, msg = validate_password(new_password)
    if not valid:
        return {"success": False, "message": msg}

    # 验证令牌
    validation = validate_reset_token(token)
    if not validation["success"]:
        return validation

    user_id = validation["data"]["user_id"]
    token_id = validation["data"]["token_id"]
    new_hash = _hash_password(new_password)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            # 更新密码
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
            # 标记令牌为已使用
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE id = %s",
                (token_id,),
            )
            conn.commit()

        return {"success": True, "message": "密码重置成功，请使用新密码登录"}
    except Exception as e:
        return {"success": False, "message": f"密码重置失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


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
