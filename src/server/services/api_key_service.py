"""API密钥管理服务 - 提供API密钥的生成、验证和管理功能"""

import secrets
import string
from datetime import datetime

import pymysql

from common.crypto import sha256_hex
from common.db_utils import build_update_sql
from config.base import DB_CONFIG


def _get_connection():
    """获取数据库连接（线程本地连接池，复用连接避免对远程 MySQL 反复握手）"""
    from services.db import get_connection
    return get_connection()


def _generate_key_string(prefix="37ac"):
    """生成唯一的API密钥字符串"""
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(40))
    return f"{prefix}_{random_part}"


def _hash_key(api_key: str) -> str:
    """对API密钥进行哈希（SHA-256）"""
    return sha256_hex(api_key)


def create_api_key(
    user_id: int, name: str, permission: str = "read", max_usage: int = 10000
) -> dict:
    """创建新的API密钥"""
    if not name or len(name.strip()) == 0:
        return {"success": False, "message": "密钥名称不能为空"}

    if permission not in ("read", "write", "admin"):
        return {"success": False, "message": "权限级别无效"}

    # 生成密钥
    raw_key = _generate_key_string()
    key_hash = _hash_key(raw_key)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO api_keys (user_id, name, key_hash, permission, max_usage)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, name.strip(), key_hash, permission, max_usage),
            )
            conn.commit()
            key_id = cursor.lastrowid

        return {
            "success": True,
            "message": "API密钥创建成功",
            "data": {
                "id": key_id,
                "name": name.strip(),
                "key": raw_key,  # 仅在创建时返回原始密钥
                "permission": permission,
                "max_usage": max_usage,
            },
        }
    except pymysql.err.IntegrityError as e:
        return {"success": False, "message": f"创建失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"创建失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def get_user_api_keys(user_id: int) -> dict:
    """获取用户的所有API密钥"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT id, name, permission, status, usage_count, max_usage,
                          last_used_at, created_at, updated_at
                   FROM api_keys
                   WHERE user_id = %s
                   ORDER BY created_at DESC""",
                (user_id,),
            )
            keys = cursor.fetchall()

        # 格式化日期字段
        for key in keys:
            for field in ["last_used_at", "created_at", "updated_at"]:
                if key.get(field) and hasattr(key[field], "strftime"):
                    key[field] = key[field].strftime("%Y-%m-%d %H:%M:%S")

        return {"success": True, "data": keys}
    except Exception as e:
        return {"success": False, "message": f"获取密钥列表失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def get_all_api_keys(page: int = 1, per_page: int = 20) -> dict:
    """获取所有API密钥（管理员）"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 查询总数
            cursor.execute("SELECT COUNT(*) as total FROM api_keys")
            total = cursor.fetchone()["total"]

            # 查询分页数据
            offset = (page - 1) * per_page
            cursor.execute(
                """SELECT ak.id, ak.user_id, ak.name, ak.permission, ak.status,
                          ak.usage_count, ak.max_usage, ak.last_used_at,
                          ak.created_at, ak.updated_at, u.username
                   FROM api_keys ak
                   LEFT JOIN users u ON ak.user_id = u.id
                   ORDER BY ak.created_at DESC
                   LIMIT %s OFFSET %s""",
                (per_page, offset),
            )
            keys = cursor.fetchall()

        # 格式化日期字段
        for key in keys:
            for field in ["last_used_at", "created_at", "updated_at"]:
                if key.get(field) and hasattr(key[field], "strftime"):
                    key[field] = key[field].strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "data": {
                "keys": keys,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        }
    except Exception as e:
        return {"success": False, "message": f"获取密钥列表失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def update_api_key(key_id: int, user_id: int, data: dict) -> dict:
    """更新API密钥信息"""
    allowed_fields = {"name", "permission", "status", "max_usage"}
    updates: dict = {}

    # 校验字段值合法性（使用局部副本，不修改调用方传入的 data）
    for field in allowed_fields:
        if field in data:
            value = data[field]
            if field == "permission" and value not in ("read", "write", "admin"):
                return {"success": False, "message": "权限级别无效"}
            if field == "status" and value not in ("active", "paused", "revoked"):
                return {"success": False, "message": "状态值无效"}
            if field == "max_usage":
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    return {"success": False, "message": "最大使用次数无效"}
            updates[field] = value

    sql, params = build_update_sql(
        "api_keys",
        updates,
        "id = %s AND user_id = %s",
        (key_id, user_id),
    )
    if not sql:
        return {"success": False, "message": "没有需要更新的字段"}

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            # 验证密钥属于当前用户
            cursor.execute(
                "SELECT id FROM api_keys WHERE id = %s AND user_id = %s",
                (key_id, user_id),
            )
            if not cursor.fetchone():
                return {"success": False, "message": "密钥不存在或无权操作"}

            cursor.execute(sql, params)
            conn.commit()

        return {"success": True, "message": "密钥更新成功"}
    except Exception as e:
        return {"success": False, "message": f"更新失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def revoke_api_key(key_id: int, user_id: int) -> dict:
    """撤销API密钥"""
    return update_api_key(key_id, user_id, {"status": "revoked"})


def verify_api_key(api_key: str) -> dict:
    """验证API密钥是否有效，返回用户信息"""
    if not api_key:
        return {"success": False, "message": "未提供API密钥"}

    key_hash = _hash_key(api_key)

    conn = None
    try:
        conn = _get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT ak.id, ak.user_id, ak.name, ak.permission, ak.status,
                          ak.usage_count, ak.max_usage, u.username, u.role
                   FROM api_keys ak
                   JOIN users u ON ak.user_id = u.id
                   WHERE ak.key_hash = %s""",
                (key_hash,),
            )
            key_info = cursor.fetchone()

        if not key_info:
            return {"success": False, "message": "API密钥无效"}

        if key_info["status"] != "active":
            return {"success": False, "message": f"API密钥已{key_info['status']}"}

        # 原子化更新使用计数和最后使用时间，并在同一语句中校验上限
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE api_keys
                   SET usage_count = usage_count + 1, last_used_at = NOW()
                   WHERE id = %s AND (max_usage <= 0 OR usage_count < max_usage)""",
                (key_info["id"],),
            )
            conn.commit()

        if cursor.rowcount == 0:
            return {"success": False, "message": "API密钥使用次数已达上限"}

        return {
            "success": True,
            "data": {
                "key_id": key_info["id"],
                "user_id": key_info["user_id"],
                "username": key_info["username"],
                "role": key_info["role"],
                "permission": key_info["permission"],
                "key_name": key_info["name"],
            },
        }
    except Exception as e:
        return {"success": False, "message": f"验证失败: {str(e)}"}
    finally:
        if conn:
            conn.close()


def delete_api_key(key_id: int, user_id: int) -> dict:
    """删除API密钥"""
    conn = None
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM api_keys WHERE id = %s AND user_id = %s",
                (key_id, user_id),
            )
            if not cursor.fetchone():
                return {"success": False, "message": "密钥不存在或无权操作"}

            cursor.execute(
                "DELETE FROM api_keys WHERE id = %s AND user_id = %s", (key_id, user_id)
            )
            conn.commit()

        return {"success": True, "message": "密钥已删除"}
    except Exception as e:
        return {"success": False, "message": f"删除失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
