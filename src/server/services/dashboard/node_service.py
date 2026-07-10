# services/dashboard/node_service.py
"""节点服务 - 节点数据库操作"""

import pymysql
from services.node_manager import get_db_connection


def create_node(name, token, addr=None, is_active=True, user_id=None, capabilities='["local"]'):
    """向数据库新增节点记录"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None

        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO nodes (name, token, addr, status, is_active, user_id, capabilities, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (
                    name,
                    token,
                    addr,
                    "offline",
                    1 if is_active else 0,
                    user_id,
                    capabilities,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def get_all_nodes_from_db():
    """从数据库获取所有节点信息"""
    nodes = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return nodes

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT n.id, n.name, n.token, n.capabilities, n.status, n.addr, n.is_active,
                          n.user_id, n.created_at, n.updated_at, u.username
                   FROM nodes n
                   LEFT JOIN users u ON n.user_id = u.id
                   ORDER BY n.updated_at DESC"""
            )
            rows = cursor.fetchall()

        for row in rows:
            nodes.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name") or row.get("node_name") or row.get("id"),
                    "token": row.get("token"),
                    "capabilities": row.get("capabilities") or "local",
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
            )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return nodes


def get_user_nodes_from_db(user_id):
    """获取指定用户的节点信息"""
    nodes = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return nodes

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT n.id, n.name, n.token, n.capabilities, n.status, n.addr, n.is_active,
                          n.user_id, n.created_at, n.updated_at, u.username
                   FROM nodes n
                   LEFT JOIN users u ON n.user_id = u.id
                   WHERE n.user_id = %s
                   ORDER BY n.updated_at DESC""",
                (user_id,),
            )
            rows = cursor.fetchall()

        for row in rows:
            nodes.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name") or row.get("node_name") or row.get("id"),
                    "token": row.get("token"),
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
            )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return nodes
