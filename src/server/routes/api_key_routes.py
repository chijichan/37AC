"""API密钥管理路由"""

from flask import Blueprint, request, jsonify, g

from services.api_key_service import (
    create_api_key,
    get_user_api_keys,
    update_api_key,
    revoke_api_key,
    delete_api_key,
    verify_api_key,
)
from middleware.auth_middleware import login_required

api_key_bp = Blueprint("api_keys", __name__, url_prefix="/api-keys")


@api_key_bp.route("", methods=["GET"])
@login_required
def list_api_keys():
    """获取当前用户的API密钥列表"""
    result = get_user_api_keys(g.user_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@api_key_bp.route("", methods=["POST"])
@login_required
def create_api_key_route():
    """创建新的API密钥"""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    permission = data.get("permission", "read")
    max_usage = data.get("max_usage", 10000)

    if not name:
        return jsonify({"success": False, "message": "密钥名称不能为空"}), 400

    if permission not in ("read", "write", "admin"):
        return jsonify({"success": False, "message": "权限级别无效"}), 400

    try:
        max_usage = int(max_usage)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "最大使用次数必须为正整数"}), 400

    if max_usage <= 0 or max_usage > 100_000_000:
        return jsonify({"success": False, "message": "最大使用次数必须在 1-100000000 之间"}), 400

    result = create_api_key(g.user_id, name, permission, max_usage)
    status_code = 201 if result["success"] else 400
    return jsonify(result), status_code


@api_key_bp.route("/<int:key_id>", methods=["PUT"])
@login_required
def update_api_key_route(key_id):
    """更新API密钥信息"""
    data = request.get_json(silent=True) or {}
    result = update_api_key(key_id, g.user_id, data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@api_key_bp.route("/<int:key_id>/revoke", methods=["POST"])
@login_required
def revoke_api_key_route(key_id):
    """撤销API密钥"""
    result = revoke_api_key(key_id, g.user_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@api_key_bp.route("/<int:key_id>", methods=["DELETE"])
@login_required
def delete_api_key_route(key_id):
    """删除API密钥"""
    result = delete_api_key(key_id, g.user_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@api_key_bp.route("/verify", methods=["POST"])
def verify_api_key_route():
    """验证API密钥（供外部服务调用）"""
    data = request.get_json(silent=True) or {}
    api_key = data.get("api_key", "")

    if not api_key:
        # 也支持从请求头获取
        api_key = request.headers.get("X-API-Key", "")

    if not api_key:
        return jsonify({"success": False, "message": "未提供API密钥"}), 400

    result = verify_api_key(api_key)
    status_code = 200 if result["success"] else 401
    return jsonify(result), status_code
