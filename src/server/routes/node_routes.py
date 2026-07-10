# routes/node_routes.py
"""节点管理路由"""

from datetime import datetime
from flask import request, jsonify, Blueprint
import json
from middleware.auth_middleware import login_required
from services.dashboard.node_service import create_node, update_node
from services.node_manager import node_manager

node_bp = Blueprint("node", __name__)


@node_bp.route("/nodes", methods=["GET"])
def get_all_nodes():
    """节点查询接口。

    * 如果通过浏览器直接访问，则渲染 `nodes.html` 页面；
    * 如果通过 AJAX 或希望获取 JSON 格式数据，会返回一份标准的 JSON 响应。

    返回 JSON 时的数据结构参考 `NodeManager.get_available_nodes()`。
    """
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        nodes = node_manager.get_available_nodes()

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

    except Exception as e:
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


@node_bp.route("/nodes", methods=["POST"])
@login_required
def add_node():
    """新增节点记录"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        token = (data.get("token") or "").strip()
        addr = (data.get("addr") or "").strip()
        capabilities_raw = (data.get("capabilities") or "local").strip()
        # 将逗号分隔字符串转为 JSON 数组格式（用于 DB 存储）
        capabilities_list = [c.strip() for c in capabilities_raw.split(",")]
        capabilities_json = json.dumps(capabilities_list, ensure_ascii=False)

        if not name:
            return jsonify({"success": False, "message": "节点名称不能为空"}), 400
        if not token:
            return jsonify({"success": False, "message": "节点 Token 不能为空"}), 400

        node_id = create_node(name, token, addr if addr else None, capabilities=capabilities_json)
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
                    "data": {"id": node_id, "capabilities": capabilities_list},
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@node_bp.route("/nodes/<int:node_id>", methods=["PUT"])
@login_required
def edit_node(node_id):
    """修改节点记录"""
    try:
        data = request.get_json(force=True, silent=True) or {}

        name = (data.get("name") or "").strip()
        addr = (data.get("addr") or "").strip()
        capabilities_raw = (data.get("capabilities") or "").strip()

        kwargs = {}
        if name:
            kwargs["name"] = name
        if addr:
            kwargs["addr"] = addr if addr else None
        if capabilities_raw:
            capabilities_list = [c.strip() for c in capabilities_raw.split(",")]
            kwargs["capabilities"] = json.dumps(capabilities_list, ensure_ascii=False)

        if not kwargs:
            return jsonify({"success": False, "message": "没有需要更新的字段"}), 400

        success = update_node(node_id, **kwargs)
        if not success:
            return jsonify({"success": False, "message": "更新节点失败，请确认节点存在"}), 500

        return jsonify({"success": True, "message": "节点更新成功"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
