# services/dashboard/task_service.py
"""任务解析服务 - 任务结果解析和用户任务查询"""

import json
import pymysql
from services.node_manager import get_db_connection


def _parse_task_result(result_json_str):
    """解析任务结果 JSON 字符串

    新结构（识别结果统一为 class_probs）：
        {"success": true, "class_probs": [{"name": "IP/角色", "prob": 0-100}, ...], ...}
    展示用 label / confidence 从 class_probs 第一项推导；
    兼容旧结构（顶层 label / confidence / class / prediction / score 等）。
    """
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

    label = None
    confidence = None

    # 新结构：从 class_probs 第一项推导最佳结果
    class_probs = result.get("class_probs")
    if isinstance(class_probs, list) and class_probs:
        top = class_probs[0]
        if isinstance(top, dict):
            label = top.get("name") or top.get("label")
            prob = top.get("prob", top.get("probability"))
            if isinstance(prob, (int, float)) and not isinstance(prob, bool):
                confidence = float(prob)

    # 兼容旧结构：顶层 label / confidence（含 class / prediction / score 等别名）
    if not label:
        label = result.get("label") or result.get("class") or result.get("prediction")
    if confidence is None:
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


def get_tasks_paginated(limit=15, page=1, time_range=30, status_filter=""):
    """分页获取任务记录（含全量统计），供仪表盘使用记录页使用"""
    result = {
        "tasks": [],
        "total": 0,
        "completed": 0,
        "pending": 0,
        "page": max(1, page),
        "total_pages": 1,
    }
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return result

        page = max(1, page)
        limit = max(1, min(100, limit))
        offset = (page - 1) * limit

        where_clauses = ["1=1"]
        params = []

        if time_range > 0:
            where_clauses.append("tr.created_at >= NOW() - INTERVAL %s DAY")
            params.append(time_range)

        if status_filter:
            where_clauses.append("tr.status = %s")
            params.append(status_filter)

        where_sql = " AND ".join(where_clauses)

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 全量统计（与筛选条件一致）
            cursor.execute(
                f"""SELECT COUNT(*) AS total,
                           SUM(CASE WHEN tr.status = 'completed' THEN 1 ELSE 0 END) AS completed
                    FROM task_results tr
                    WHERE {where_sql}""",
                params,
            )
            stat_row = cursor.fetchone() or {}
            total = int(stat_row.get("total") or 0)
            completed = int(stat_row.get("completed") or 0)

            result["total"] = total
            result["completed"] = completed
            result["pending"] = total - completed
            result["total_pages"] = max(1, (total + limit - 1) // limit)
            result["page"] = min(page, result["total_pages"])
            offset = (result["page"] - 1) * limit

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
            result["tasks"].append(
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

    return result


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
