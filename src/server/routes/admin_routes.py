# routes/admin_routes.py
"""管理员路由 - 用户管理 CRUD"""

from flask import Blueprint, request, jsonify

from services.auth_service import (
    get_users,
    get_user_by_id,
    create_user,
    update_user,
    delete_user,
    update_user_role,
    update_user_status,
)
from middleware.auth_middleware import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """获取用户列表"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    keyword = request.args.get("keyword", "").strip() or None

    # 限制分页参数
    page = max(1, page)
    per_page = max(1, min(100, per_page))

    result = get_users(page, per_page, keyword)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user_route():
    """创建用户"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400

    result = create_user(username, password, email, role)
    status_code = 201 if result["success"] else 400
    return jsonify(result), status_code


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user_detail(user_id):
    """获取用户详情"""
    result = get_user_by_id(user_id)
    status_code = 200 if result["success"] else 404
    return jsonify(result), status_code


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user_route(user_id):
    """更新用户信息"""
    data = request.get_json(silent=True) or {}
    result = update_user(user_id, data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user_route(user_id):
    """删除用户"""
    result = delete_user(user_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@admin_bp.route("/users/<int:user_id>/roles", methods=["PUT"])
@admin_required
def assign_role(user_id):
    """分配用户角色"""
    data = request.get_json(silent=True) or {}
    role = data.get("role", "")

    if not role:
        return jsonify({"success": False, "message": "角色不能为空"}), 400

    result = update_user_role(user_id, role)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@admin_required
def change_status(user_id):
    """修改用户状态"""
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status is None:
        return jsonify({"success": False, "message": "状态值不能为空"}), 400

    if not isinstance(status, int) or status not in (0, 1):
        return jsonify({"success": False, "message": "状态值必须为 0 或 1"}), 400

    result = update_user_status(user_id, status)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code
