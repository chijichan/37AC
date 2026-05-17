# services/dashboard/task_service.py
"""任务解析服务 - 任务结果解析和用户任务查询"""

import json
import pymysql
from services.node_manager import get_db_connection


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
