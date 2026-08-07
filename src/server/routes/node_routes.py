# routes/node_routes.py
"""节点管理路由"""

from datetime import datetime
from flask import request, jsonify, Blueprint, g
import json
from middleware.auth_middleware import login_required
from services.dashboard.node_service import (
    create_node,
    update_node,
    delete_node as delete_node_from_db,
    get_all_nodes_from_db,
    get_user_nodes_from_db,
)
from services.node_manager import node_manager
from config.log_config import get_logger

node_bp = Blueprint("node", __name__)
logger = get_logger("node_routes")


def _is_admin():
    """当前请求用户是否为管理员"""
    return g.get("user_role") == "admin"


@node_bp.route("/nodes", methods=["GET"])
@login_required
def get_all_nodes():
    """节点查询接口：管理员返回全部节点，普通用户仅返回自己名下的节点。"""
    try:
        if _is_admin():
            nodes = get_all_nodes_from_db()
        else:
            nodes = get_user_nodes_from_db(g.user_id)

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
        logger.error("获取节点列表失败: %s", e)
        return (
            jsonify(
                {
                    "type": "nodes_list",
                    "timestamp": int(datetime.now().timestamp()),
                    "data": [],
                    "error": "获取节点列表失败",
                }
            ),
            500,
        )


@node_bp.route("/nodes", methods=["POST"])
@login_required
def add_node():
    """新增节点记录（归属当前登录用户）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        addr = (data.get("addr") or "").strip()
        # 用户自定义 Token（可选）：提供则哈希存储，否则服务端自动生成
        custom_token = (data.get("token") or "").strip() or None
        capabilities_raw = (data.get("capabilities") or "local").strip()
        # 将逗号分隔字符串转为 JSON 数组格式（用于 DB 存储）
        capabilities_list = [c.strip() for c in capabilities_raw.split(",")]
        capabilities_json = json.dumps(capabilities_list, ensure_ascii=False)

        if not name:
            return jsonify({"success": False, "message": "节点名称不能为空"}), 400

        node_id, raw_token = create_node(
            name,
            custom_token,
            addr if addr else None,
            user_id=g.user_id,
            capabilities=capabilities_json,
        )
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
                    "data": {
                        "id": node_id,
                        "capabilities": capabilities_list,
                        "token": raw_token,  # 仅在创建时返回一次
                    },
                }
            ),
            201,
        )
    except Exception as e:
        logger.error("新增节点失败: %s", e)
        return jsonify({"success": False, "message": "新增节点失败"}), 500


@node_bp.route("/nodes/<int:node_id>", methods=["PUT"])
@login_required
def edit_node(node_id):
    """修改节点记录（仅所属用户或管理员）"""
    try:
        data = request.get_json(force=True, silent=True) or {}

        name = (data.get("name") or "").strip()
        addr = (data.get("addr") or "").strip()
        capabilities_raw = (data.get("capabilities") or "").strip()
        # 修改 Token（可选）：提供则哈希存储并更新
        custom_token = (data.get("token") or "").strip() or None

        kwargs = {}
        if name:
            kwargs["name"] = name
        if addr:
            kwargs["addr"] = addr if addr else None
        if capabilities_raw:
            capabilities_list = [c.strip() for c in capabilities_raw.split(",")]
            kwargs["capabilities"] = json.dumps(capabilities_list, ensure_ascii=False)
        if custom_token:
            kwargs["token"] = custom_token

        if not kwargs:
            return jsonify({"success": False, "message": "没有需要更新的字段"}), 400

        success = update_node(node_id, user_id=g.user_id, is_admin=_is_admin(), **kwargs)
        if not success:
            return jsonify({"success": False, "message": "更新节点失败，请确认节点存在或无权操作"}), 403

        return jsonify({"success": True, "message": "节点更新成功"}), 200
    except Exception as e:
        logger.error("更新节点失败: %s", e)
        return jsonify({"success": False, "message": "更新节点失败"}), 500


@node_bp.route("/nodes/<int:node_id>", methods=["DELETE"])
@login_required
def delete_node(node_id):
    """删除节点记录（仅所属用户或管理员），同时从内存管理器移除在线连接"""
    try:
        # 先校验归属：非管理员仅能删除自己名下的节点
        success = delete_node_from_db(node_id, user_id=g.user_id, is_admin=_is_admin())
        if not success:
            return jsonify({"success": False, "message": "删除节点失败，请确认节点存在或无权操作"}), 403

        # 删除成功后再从内存管理器移除（关闭 socket、触发客户端断线重连）
        if node_manager.remove_node(node_id):
            logger.info("节点 %s 已从内存管理器移除", node_id)
        else:
            logger.info("节点 %s 不在内存管理器中（可能已离线）", node_id)

        return jsonify({"success": True, "message": "节点已删除"}), 200
    except Exception as e:
        logger.error("删除节点失败: %s", e)
        return jsonify({"success": False, "message": "删除节点失败"}), 500
