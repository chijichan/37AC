# services/user_service.py
"""用户服务 - 提供用户 CRUD 操作和用户列表查询（含管理员功能）"""

import pymysql

from common.db_utils import build_update_sql
from config.base import DB_CONFIG
from config.log_config import get_logger
from services.auth.validators import validate_email, validate_username, validate_password
from services.auth.password_service import hash_password

logger = get_logger("user_service")


def _get_connection():
    """获取数据库连接（线程本地连接池，复用连接避免对远程 MySQL 反复握手）"""
    from utils.db_utils import get_connection
    return get_connection()


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

    for field in allowed_fields:
        if field in data and field == "email" and data[field] and not validate_email(data[field]):
            return {"success": False, "message": "邮箱格式不正确"}

    sql, params = build_update_sql(
        "users",
        {field: data.get(field) for field in allowed_fields},
        "id = %s",
        (user_id,),
    )
    if not sql:
        return {"success": False, "message": "没有需要更新的字段"}

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

            cursor.execute(sql, params)
            conn.commit()

        return {"success": True, "message": "更新成功"}
    except Exception as e:
        return {"success": False, "message": f"更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def get_users(page: int = 1, per_page: int = 20, keyword: str = None) -> dict:
    """获取用户列表（管理员）"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            where_clause = ""
            params = []
            if keyword:
                where_clause = "WHERE username LIKE %s OR email LIKE %s"
                like_keyword = f"%{keyword}%"
                params = [like_keyword, like_keyword]

            count_sql = f"SELECT COUNT(*) as total FROM users {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            offset = (page - 1) * per_page
            sql = f"""SELECT id, username, email, role, status, avatar,
                             last_login_at, last_login_ip, created_at, updated_at
                      FROM users {where_clause}
                      ORDER BY created_at DESC
                      LIMIT %s OFFSET %s"""
            cursor.execute(sql, params + [per_page, offset])
            users = cursor.fetchall()

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


def create_user(username: str, password: str, email: str = None, role: str = "user") -> dict:
    """创建用户（管理员）"""
    valid, msg = validate_username(username)
    if not valid:
        return {"success": False, "message": msg}

    valid, msg = validate_password(password)
    if not valid:
        return {"success": False, "message": msg}

    if email and not validate_email(email):
        return {"success": False, "message": "邮箱格式不正确"}

    if role not in ("admin", "user"):
        return {"success": False, "message": "角色无效"}

    password_hash_value = hash_password(password)

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
                (username, password_hash_value, email, role),
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

    sql, params = build_update_sql(
        "users",
        {field: data.get(field) for field in allowed_fields},
        "id = %s",
        (user_id,),
    )
    if not sql:
        return {"success": False, "message": "没有需要更新的字段"}

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

            cursor.execute(sql, params)
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

            cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            conn.commit()

        status_text = "启用" if status == 1 else "禁用"
        return {"success": True, "message": f"用户已{status_text}"}
    except Exception as e:
        return {"success": False, "message": f"状态更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
