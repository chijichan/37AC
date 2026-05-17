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
    get_user_tasks_from_db,
)
from middleware.auth_middleware import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard/overview", methods=["GET"])
@dashboard_bp.route("/dashboard/summary", methods=["GET"])
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
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/dashboard/stats", methods=["GET"])
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
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/dashboard/nodes", methods=["GET"])
def api_dashboard_nodes():
    try:
        nodes = get_all_nodes_from_db()

        return jsonify(
            {
                "type": "dashboard_nodes",
                "timestamp": int(datetime.now().timestamp()),
                "data": nodes,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/dashboard/history", methods=["GET"])
@dashboard_bp.route("/dashboard/tasks", methods=["GET"])
def api_dashboard_tasks():
    try:
        # 获取查询参数
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 15, type=int)
        time_range = request.args.get("time_range", 30, type=int)
        status_filter = request.args.get("status", "")

        tasks = get_recent_tasks(limit=limit)

        if not tasks:
            tasks = []

        return jsonify(
            {
                "type": "dashboard_tasks",
                "timestamp": int(datetime.now().timestamp()),
                "data": tasks,
                "page": page,
                "total_pages": 1,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
