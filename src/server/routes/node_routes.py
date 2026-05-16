# routes/node_routes.py
"""节点管理路由"""

from datetime import datetime
from flask import render_template, request, flash, jsonify, Blueprint
from middleware.auth_middleware import login_required
from services.dashboard_service import create_node
from services.listen_service import node_manager

node_bp = Blueprint("node", __name__)


@node_bp.route("/nodes", methods=["GET"])
def get_all_nodes():
    """节点查询接口。

    * 如果通过浏览器直接访问，则渲染 `nodes.html` 页面；
    * 如果通过 AJAX 或希望获取 JSON 格式数据，会返回一份标准的 JSON 响应。

    返回 JSON 时的数据结构参考 `NodeManager.get_available_nodes()`。
    """
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    wants_json = is_ajax or request.accept_mimetypes.accept_json

    try:
        nodes = node_manager.get_available_nodes()

        if wants_json:
            return (
                jsonify(
                    {
                        "type": "nodes_list",
                        "timestamp": int(datetime.now().timestamp()),
                        "data": nodes,
                    }
                ),
                200,
            )
        else:
            # 普通浏览器访问，渲染页面，由 JS 进行刷新
            return render_template(
                "nodes.html", title="节点管理", year=datetime.now().year
            )

    except Exception as e:
        if wants_json:
            return (
                jsonify(
                    {
                        "type": "nodes_list",
                        "timestamp": int(datetime.now().timestamp()),
                        "data": [],
                        "error": str(e),
                    }
                ),
                500,
            )
        else:
            flash(f"获取节点信息失败: {e}")
            return render_template(
                "nodes.html", title="节点管理", year=datetime.now().year
            )


@node_bp.route("/nodes", methods=["POST"])
@login_required
def add_node():
    """新增节点记录"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        token = (data.get("token") or "").strip()
        addr = (data.get("addr") or "").strip()

        if not name:
            return jsonify({"success": False, "message": "节点名称不能为空"}), 400
        if not token:
            return jsonify({"success": False, "message": "节点 Token 不能为空"}), 400

        node_id = create_node(name, token, addr if addr else None)
        if not node_id:
            return (
                jsonify(
                    {"success": False, "message": "新增节点失败，请检查输入或稍后重试"}
                ),
                500,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "节点添加成功",
                    "data": {"id": node_id},
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
