# routes/dashboard_routes.py
"""仪表盘相关路由"""

from datetime import datetime
from flask import jsonify, Blueprint, request, g
from services.dashboard import (
    get_dashboard_stats,
    get_recent_tasks,
    get_overview_data,
)
from services.dashboard.node_service import (
    get_all_nodes_from_db,
    get_user_nodes_from_db,
)
from services.dashboard.task_service import (
    get_tasks_paginated,
)
from middleware.auth_middleware import login_required
from config.log_config import get_logger

logger = get_logger("dashboard_routes")

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard/overview", methods=["GET"])
@dashboard_bp.route("/dashboard/summary", methods=["GET"])
@login_required
def api_dashboard_summary():
    try:
        return jsonify(
            {
                "type": "dashboard_summary",
                "timestamp": int(datetime.now().timestamp()),
                "data": get_overview_data(),
            }
        )
    except Exception as e:
        logger.error("仪表盘概览接口错误: %s", e)
        return jsonify({"error": "获取仪表盘数据失败"}), 500


@dashboard_bp.route("/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    try:
        return jsonify(
            {
                "type": "dashboard_stats",
                "timestamp": int(datetime.now().timestamp()),
                "data": get_dashboard_stats(),
            }
        )
    except Exception as e:
        logger.error("仪表盘统计接口错误: %s", e)
        return jsonify({"error": "获取仪表盘数据失败"}), 500


@dashboard_bp.route("/dashboard/nodes", methods=["GET"])
@login_required
def api_dashboard_nodes():
    try:
        # 管理员返回全部节点，普通用户仅返回自己名下的节点
        if g.get("user_role") == "admin":
            nodes = get_all_nodes_from_db()
        else:
            nodes = get_user_nodes_from_db(g.user_id)

        return jsonify(
            {
                "type": "dashboard_nodes",
                "timestamp": int(datetime.now().timestamp()),
                "data": nodes,
            }
        )
    except Exception as e:
        logger.error("节点列表接口错误: %s", e)
        return jsonify({"error": "获取节点列表失败"}), 500


@dashboard_bp.route("/dashboard/history", methods=["GET"])
@dashboard_bp.route("/dashboard/tasks", methods=["GET"])
@login_required
def api_dashboard_tasks():
    try:
        # 获取查询参数
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 15, type=int)
        time_range = request.args.get("time_range", 30, type=int)
        status = request.args.get("status", "", type=str)

        # 限制分页与时间范围，防止大数据扫描
        page = max(1, page)
        limit = max(1, min(100, limit))
        time_range = max(1, min(365, time_range))

        result = get_tasks_paginated(
            limit=limit, page=page, time_range=time_range, status_filter=status
        )

        return jsonify(
            {
                "type": "dashboard_tasks",
                "timestamp": int(datetime.now().timestamp()),
                "data": result["tasks"],
                "page": result["page"],
                "total_pages": result["total_pages"],
                "total_count": result["total"],
                "completed_count": result["completed"],
                "pending_count": result["pending"],
            }
        )
    except Exception as e:
        logger.error("任务历史接口错误: %s", e)
        return jsonify({"error": "获取任务历史失败"}), 500
