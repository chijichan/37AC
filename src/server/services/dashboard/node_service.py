# services/dashboard/node_service.py
"""节点服务 - 节点数据库操作"""

import pymysql
from common.crypto import generate_node_token, hash_node_token
from common.db_utils import build_update_sql
from services.node_manager import get_db_connection


def create_node(name, token=None, addr=None, is_active=True, user_id=None, capabilities='["local"]'):
    """向数据库新增节点记录。

    若传入 token 为字符串则直接哈希存储；若为 None 则自动生成新的 token。
    返回 (node_id, raw_token) 元组，raw_token 仅在创建时返回一次。
    """
    conn = None
    raw_token = None
    if token is None:
        raw_token, token_hash = generate_node_token()
    else:
        token_hash = hash_node_token(token)

    # addr 列为 NOT NULL，空地址归一化为空字符串（地址是可选项）
    addr = (addr or "").strip() or ""

    try:
        conn = get_db_connection()
        if not conn:
            return None, raw_token

        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO nodes (name, token, addr, status, is_active, user_id, capabilities, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (
                    name,
                    token_hash,
                    addr,
                    "offline",
                    1 if is_active else 0,
                    user_id,
                    capabilities,
                ),
            )
            conn.commit()
            return cursor.lastrowid, raw_token
    except Exception:
        return None, raw_token
    finally:
        if conn:
            conn.close()


def update_node(node_id, name=None, addr=None, capabilities=None, is_active=None, token=None,
                user_id=None, is_admin=False):
    """更新节点记录。

    非管理员（is_admin=False）时，仅允许更新 user_id 名下的节点；
    管理员不受限制。
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return False

        updates = {
            "name": name,
            "addr": addr,
            "capabilities": capabilities,
            "is_active": None if is_active is None else (1 if is_active else 0),
            "token": hash_node_token(token) if token is not None else None,
        }

        where = "id = %s"
        where_params = [node_id]
        if not is_admin:
            where += " AND user_id = %s"
            where_params.append(user_id)

        sql, params = build_update_sql(
            "nodes", updates, where, where_params,
            raw_assignments=["updated_at = NOW()"],
        )
        if not sql:
            return True  # 无字段需要更新

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


def delete_node(node_id, user_id=None, is_admin=False):
    """删除节点记录，返回是否成功。

    非管理员（is_admin=False）时，仅允许删除 user_id 名下的节点；
    管理员不受限制。
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return False

        sql = "DELETE FROM nodes WHERE id = %s"
        params = [node_id]
        if not is_admin:
            sql += " AND user_id = %s"
            params.append(user_id)

        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            conn.commit()
            return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


def _row_to_node_dict(row):
    """将数据库行转换为节点字典（不暴露 token）"""
    return {
        "id": row.get("id"),
        "name": row.get("name") or row.get("node_name") or row.get("id"),
        "capabilities": row.get("capabilities") or '["local"]',
        "status": row.get("status"),
        "addr": row.get("addr"),
        "is_active": bool(row.get("is_active")),
        "user_id": row.get("user_id"),
        "username": row.get("username"),
        "created_at": (
            row.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(row.get("created_at"), "strftime")
            else row.get("created_at")
        ),
        "updated_at": (
            row.get("updated_at").strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(row.get("updated_at"), "strftime")
            else row.get("updated_at")
        ),
    }


def _query_nodes(where_clause="", params=None):
    """查询节点通用方法"""
    nodes = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return nodes

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = f"""SELECT n.id, n.name, n.token, n.capabilities, n.status, n.addr, n.is_active,
                          n.user_id, n.created_at, n.updated_at, u.username
                   FROM nodes n
                   LEFT JOIN users u ON n.user_id = u.id
                   {where_clause}
                   ORDER BY n.updated_at DESC"""
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()

        for row in rows:
            nodes.append(_row_to_node_dict(row))
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return nodes


def get_all_nodes_from_db():
    """从数据库获取所有节点信息"""
    return _query_nodes()


def get_user_nodes_from_db(user_id):
    """获取指定用户的节点信息"""
    return _query_nodes("WHERE n.user_id = %s", (user_id,))
