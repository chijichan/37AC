# routes/user_routes.py
"""用户路由 - 个人资料管理、密码修改等"""

from flask import Blueprint, request, jsonify, g

from services.auth_service import get_user_by_id, update_profile, change_password
from middleware.auth_middleware import login_required, optional_login

user_bp = Blueprint("user", __name__, url_prefix="/users")


@user_bp.route("/profile", methods=["GET"])
@optional_login
def get_profile():
    """获取当前用户个人资料（支持可选登录）"""
    if not hasattr(g, "user_id") or not g.user_id:
        return jsonify({"success": False, "message": "未登录，请先登录"}), 401
    result = get_user_by_id(g.user_id)
    status_code = 200 if result["success"] else 404
    return jsonify(result), status_code


@user_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile_route():
    """更新当前用户个人资料"""
    data = request.get_json(silent=True) or {}
    result = update_profile(g.user_id, data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@user_bp.route("/change-password", methods=["PUT"])
@login_required
def change_password_route():
    """修改当前用户密码"""
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"success": False, "message": "原密码和新密码不能为空"}), 400

    result = change_password(g.user_id, old_password, new_password)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@user_bp.route("/sessions", methods=["GET"])
@login_required
def get_sessions():
    """获取当前用户的登录会话（预留接口）"""
    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "sessions": [
                        {
                            "id": "current",
                            "ip": request.remote_addr or "0.0.0.0",
                            "user_agent": request.headers.get("User-Agent", ""),
                            "created_at": "当前会话",
                            "is_current": True,
                        }
                    ]
                },
            }
        ),
        200,
    )


@user_bp.route("/sessions/<session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    """登出指定会话（预留接口）"""
    return jsonify({"success": True, "message": "会话已登出"}), 200
