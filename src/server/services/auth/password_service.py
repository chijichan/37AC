"""密码服务模块 - 提供密码哈希（bcrypt）、重置令牌管理、密码修改等功能"""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
import pymysql

from config.base import FRONTEND_URL
from config.email_config import RESET_RATE_LIMIT
from config.log_config import get_logger
from services.db import get_connection
from services.email_service import is_configured as smtp_is_configured, send_password_reset_email
from .validators import validate_password

logger = get_logger("password_service")


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（自动加盐）"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    valid, msg = validate_password(new_password)
    if not valid:
        return {"success": False, "message": msg}

    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "message": "用户不存在"}

            if not verify_password(old_password, row[0]):
                return {"success": False, "message": "原密码错误"}

            new_hash = hash_password(new_password)
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


def _count_recent_reset_requests(email: str) -> int:
    """统计指定邮箱在限流时间窗口内的重置请求次数"""
    conn = get_connection()
    if not conn:
        return 0
    try:
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
    conn = get_connection()
    if not conn:
        return 0
    try:
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
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        if not user:
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

        _cleanup_expired_tokens()

        # 生成随机令牌
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # 设置过期时间（1小时）
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
            reset_url = f"{FRONTEND_URL}/auth/reset-password?token={raw_token}"
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
                    "data": {"token": None}
                }
            else:
                # 生产环境禁止将 raw_token 返回给客户端
                logger.error("发送密码重置邮件失败: %s", email_result["message"])
                return {
                    "success": False,
                    "message": "邮件发送失败，请稍后重试",
                    "data": {"token": None}
                }
        else:
            # 未配置 SMTP 时绝不在响应中暴露 raw_token
            logger.warning("SMTP 未配置，无法发送密码重置邮件")
            return {
                "success": False,
                "message": "邮件服务未配置，无法发送重置链接",
                "data": {"token": None}
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
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
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

        expires_at = reset_record["expires_at"]
        if hasattr(expires_at, "strftime"):
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
    valid, msg = validate_password(new_password)
    if not valid:
        return {"success": False, "message": msg}

    validation = validate_reset_token(token)
    if not validation["success"]:
        return validation

    user_id = validation["data"]["user_id"]
    token_id = validation["data"]["token_id"]
    new_hash = hash_password(new_password)

    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
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
