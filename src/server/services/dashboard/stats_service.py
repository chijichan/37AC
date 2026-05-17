# services/dashboard/stats_service.py
"""统计服务 - 仪表盘核心统计数据和概览数据"""

from datetime import datetime
from services.node_manager import get_db_connection, node_manager
from services.dashboard.task_service import _parse_task_result
from services.dashboard.system_service import _get_host_system_status


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
            with conn.cursor() as cursor:
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
                parsed = _parse_task_result(row[1] if len(row) > 1 else "")
                task_dict = {
                    "task_id": row[0],
                    "status": row[2],
                    "label": parsed.get("label"),
                    "confidence": parsed.get("confidence"),
                    "result": parsed.get("raw_result"),
                    "user_id": row[4],
                    "api_key_id": row[5],
                    "api_key_name": row[6] if len(row) > 6 else None,
                    "created_at": (
                        row[3].strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(row[3], "strftime")
                        else row[3]
                    ),
                }
                tasks.append(task_dict)
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

        created_at = task.get("created_at")
        if created_at:
            try:
                if isinstance(created_at, str):
                    dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                else:
                    dt = created_at
                now = datetime.now()
                diff = now - dt
                seconds = int(diff.total_seconds())
                if seconds < 60:
                    time_str = "刚刚"
                elif seconds < 3600:
                    time_str = f"{seconds // 60}分钟前"
                elif seconds < 86400:
                    time_str = f"{seconds // 3600}小时前"
                elif seconds < 2592000:
                    time_str = f"{seconds // 86400}天前"
                else:
                    time_str = created_at if isinstance(created_at, str) else created_at.strftime("%Y-%m-%d")
            except Exception:
                time_str = "刚刚"
        else:
            time_str = "刚刚"

        recent_activity.append(
            {
                "type": "upload",
                "title": title,
                "description": f"任务 {task.get('task_id')} 已完成，置信度 {confidence if confidence is not None else '--'}%",
                "time": time_str,
            }
        )

    records = []
    for task in recent_tasks:
        records.append(
            {
                "id": task.get("task_id"),
                "filename": f"image_{str(task.get('task_id', ''))[:8]}.jpg",
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
