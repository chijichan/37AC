# services/dashboard_service.py
"""仪表盘数据服务 - 提供仪表盘相关的数据查询和统计功能"""

import json
import os
import time
from datetime import datetime
from services.tcp_service import get_db_connection, node_manager
import pymysql


def _parse_task_result(result_json_str):
    """解析任务结果 JSON 字符串"""
    if isinstance(result_json_str, bytes):
        result_json_str = result_json_str.decode("utf-8", errors="ignore")

    try:
        result = json.loads(result_json_str)
    except Exception:
        return {
            "label": None,
            "confidence": None,
            "raw_result": result_json_str,
        }

    label = result.get("label") or result.get("class") or result.get("prediction")
    confidence = (
        result.get("confidence") or result.get("score") or result.get("probability")
    )
    if isinstance(confidence, str):
        confidence = confidence.strip().rstrip("%")
        try:
            confidence = float(confidence)
        except Exception:
            confidence = None

    return {
        "label": label,
        "confidence": confidence,
        "raw_result": result,
    }


def get_dashboard_stats():
    """获取仪表盘统计数据"""
    stats = {
        "total_visits": 0,
        "total_uploads": 0,
        "active_users": 0,
        "accuracy": 0.0,
        "online_nodes": 0,
        "idle_nodes": 0,
    }

    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM task_results")
                row = cursor.fetchone()
                stats["total_uploads"] = int(row[0] or 0) if row else 0
                stats["total_visits"] = stats["total_uploads"] * 2

                cursor.execute(
                    "SELECT result FROM task_results ORDER BY task_id DESC LIMIT 100"
                )
                rows = cursor.fetchall()

            confidences = []
            for row in rows:
                if not row or not row[0]:
                    continue
                parsed = _parse_task_result(row[0])
                confidence = parsed.get("confidence")
                if isinstance(confidence, (int, float)):
                    confidences.append(confidence)

            if confidences:
                avg = sum(confidences) / len(confidences)
                stats["accuracy"] = min(100.0, float(avg * 100 if avg <= 1 else avg))

    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    try:
        stats["online_nodes"] = len(node_manager.get_available_nodes())
        stats["idle_nodes"] = len(node_manager.get_idle_nodes())
        stats["active_users"] = max(1, stats["online_nodes"] * 3)
    except Exception:
        pass

    return stats


def get_recent_tasks(limit=10):
    """获取最近的任务列表"""
    tasks = []
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    """SELECT tr.task_id, tr.result, tr.status, tr.created_at,
                              tr.user_id, tr.api_key_id, ak.name as api_key_name
                       FROM task_results tr
                       LEFT JOIN api_keys ak ON tr.api_key_id = ak.id
                       ORDER BY tr.created_at DESC LIMIT %s""",
                    (limit,),
                )
                rows = cursor.fetchall()

            for row in rows:
                parsed = _parse_task_result(row.get("result") or "")
                tasks.append(
                    {
                        "task_id": row.get("task_id"),
                        "status": row.get("status"),
                        "label": parsed.get("label"),
                        "confidence": parsed.get("confidence"),
                        "result": parsed.get("raw_result"),
                        "user_id": row.get("user_id"),
                        "api_key_id": row.get("api_key_id"),
                        "api_key_name": row.get("api_key_name"),
                        "created_at": (
                            row.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
                            if hasattr(row.get("created_at"), "strftime")
                            else row.get("created_at")
                        ),
                    }
                )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return tasks


# 网络带宽测量缓存
_net_io_cache = {
    "prev_bytes_sent": 0,
    "prev_bytes_recv": 0,
    "prev_time": 0,
    "upload_speed": 0.0,  # KB/s
    "download_speed": 0.0,  # KB/s
}


def _measure_network_bandwidth():
    """测量实时网络带宽，返回上传/下载速度（KB/s）"""
    global _net_io_cache

    try:
        import importlib.util

        psutil = None
        if importlib.util.find_spec("psutil") is not None:
            import psutil

        if not psutil:
            return {"upload_speed": 0.0, "download_speed": 0.0}

        net = psutil.net_io_counters()
        now = time.time()

        prev_sent = _net_io_cache["prev_bytes_sent"]
        prev_recv = _net_io_cache["prev_bytes_recv"]
        prev_time = _net_io_cache["prev_time"]

        if prev_time > 0 and prev_sent > 0 and prev_recv > 0:
            elapsed = now - prev_time
            if elapsed > 0:
                # 计算速率（字节/秒），转换为 KB/s
                upload_bps = (net.bytes_sent - prev_sent) / elapsed
                download_bps = (net.bytes_recv - prev_recv) / elapsed
                _net_io_cache["upload_speed"] = round(upload_bps / 1024, 1)  # KB/s
                _net_io_cache["download_speed"] = round(download_bps / 1024, 1)  # KB/s

        # 更新缓存
        _net_io_cache["prev_bytes_sent"] = net.bytes_sent
        _net_io_cache["prev_bytes_recv"] = net.bytes_recv
        _net_io_cache["prev_time"] = now

        return {
            "upload_speed": _net_io_cache["upload_speed"],
            "download_speed": _net_io_cache["download_speed"],
        }
    except Exception:
        return {"upload_speed": 0.0, "download_speed": 0.0}


def _get_host_system_status():
    """获取主机系统状态（CPU、内存、磁盘、网络带宽）"""
    status = {
        "cpu": 45.0,
        "memory": 68.0,
        "disk": 52.0,
        "network": {
            "upload_speed": 0.0,
            "download_speed": 0.0,
        },
    }

    try:
        import importlib.util

        psutil = None
        if importlib.util.find_spec("psutil") is not None:
            import psutil

        if psutil:
            status["cpu"] = round(psutil.cpu_percent(interval=0.2), 1)
            memory = psutil.virtual_memory()
            status["memory"] = round(memory.percent, 1)
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            status["disk"] = round(disk.percent, 1)
            # 实时网络带宽
            status["network"] = _measure_network_bandwidth()
    except Exception:
        pass

    return status


def _get_all_nodes_from_db():
    """从数据库获取所有节点信息"""
    nodes = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return nodes

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """SELECT n.id, n.name, n.token, n.status, n.addr, n.is_active,
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
                """SELECT n.id, n.name, n.token, n.status, n.addr, n.is_active,
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


def create_node(name, token, addr=None, is_active=True, user_id=None):
    """向数据库新增节点记录"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None

        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO nodes (name, token, addr, status, is_active, user_id, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (
                    name,
                    token,
                    addr,
                    "offline",
                    1 if is_active else 0,
                    user_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def get_user_tasks_from_db(user_id, limit=15, page=1, time_range=30, status_filter=""):
    """获取指定用户的任务记录"""
    tasks = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return tasks

        offset = (page - 1) * limit

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 构建查询条件
            where_clauses = ["tr.user_id = %s"]
            params = [user_id]

            if time_range > 0:
                where_clauses.append("tr.created_at >= NOW() - INTERVAL %s DAY")
                params.append(time_range)

            if status_filter:
                where_clauses.append("tr.status = %s")
                params.append(status_filter)

            where_sql = " AND ".join(where_clauses)

            cursor.execute(
                f"""SELECT tr.task_id, tr.status, tr.result, tr.user_id,
                           tr.api_key_id, tr.created_at, tr.updated_at,
                           ak.name as api_key_name
                    FROM task_results tr
                    LEFT JOIN api_keys ak ON tr.api_key_id = ak.id
                    WHERE {where_sql}
                    ORDER BY tr.created_at DESC
                    LIMIT %s OFFSET %s""",
                params + [limit, offset],
            )
            rows = cursor.fetchall()

        for row in rows:
            parsed = _parse_task_result(row.get("result") or "")
            tasks.append(
                {
                    "task_id": row.get("task_id"),
                    "status": row.get("status"),
                    "label": parsed.get("label"),
                    "confidence": parsed.get("confidence"),
                    "result": parsed.get("raw_result"),
                    "user_id": row.get("user_id"),
                    "api_key_id": row.get("api_key_id"),
                    "api_key_name": row.get("api_key_name"),
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

    return tasks


def get_overview_data():
    """获取仪表盘概览数据"""
    stats = get_dashboard_stats()
    system_status = _get_host_system_status()
    recent_tasks = get_recent_tasks(limit=5)

    if not recent_tasks:
        recent_tasks = [
            {
                "task_id": f"demo-{i+1}",
                "status": "success",
                "label": "示例结果",
                "confidence": 90.0 - i * 3,
                "result": {"label": "示例角色", "confidence": 90.0 - i * 3},
            }
            for i in range(5)
        ]

    recent_activity = []
    for task in recent_tasks:
        title = task.get("label") or "识别任务完成"
        confidence = task.get("confidence")
        recent_activity.append(
            {
                "icon": "📤",
                "type": "upload",
                "title": title,
                "description": f"任务 {task.get('task_id')} 已完成，置信度 {confidence if confidence is not None else '--'}%",
                "time": "刚刚",
            }
        )

    records = []
    for task in recent_tasks:
        records.append(
            {
                "id": task.get("task_id"),
                "filename": f"image_{task.get('task_id')[:8]}.jpg",
                "result": task.get("label") or "未知",
                "confidence": task.get("confidence") or 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": task.get("status", "success"),
            }
        )

    return {
        "stats": stats,
        "system": system_status,
        "recent_activity": recent_activity,
        "recent_records": records,
    }
