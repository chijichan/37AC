# routes/dashboard_routes.py
"""仪表盘相关路由"""

from datetime import datetime
from flask import jsonify, Blueprint
from services.dashboard_service import (
    get_dashboard_stats,
    get_recent_tasks,
    get_overview_data,
    _get_all_nodes_from_db,
)

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
        nodes = _get_all_nodes_from_db()

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
        tasks = get_recent_tasks(limit=10)
        if not tasks:
            tasks = [
                {
                    "task_id": f"demo-{i+1}",
                    "status": "success" if i % 2 == 0 else "failure",
                    "label": "示例角色",
                    "confidence": 90.0 - i * 5,
                    "result": {"label": "示例角色", "confidence": 90.0 - i * 5},
                }
                for i in range(10)
            ]

        return jsonify(
            {
                "type": "dashboard_tasks",
                "timestamp": int(datetime.now().timestamp()),
                "data": tasks,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
