# routes/auth_routes.py
"""认证路由 - 用户注册、登录、令牌刷新、注销等"""

from flask import Blueprint, request, jsonify

from services.auth_service import register, login, refresh_token
from services.auth.password_service import generate_reset_token, validate_reset_token, reset_password
from middleware.auth_middleware import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
def register_route():
    """用户注册"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400

    result = register(username, password, email)
    status_code = 201 if result["success"] else 400
    return jsonify(result), status_code


@auth_bp.route("/login", methods=["POST"])
def login_route():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip = request.remote_addr

    if not username or not password:
        return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400

    result = login(username, password, ip)
    status_code = 200 if result["success"] else 401
    return jsonify(result), status_code


@auth_bp.route("/refresh", methods=["POST"])
def refresh_route():
    """刷新访问令牌"""
    data = request.get_json(silent=True) or {}
    refresh_token_str = data.get("refresh_token", "")

    if not refresh_token_str:
        return jsonify({"success": False, "message": "缺少刷新令牌"}), 400

    result = refresh_token(refresh_token_str)
    status_code = 200 if result["success"] else 401
    return jsonify(result), status_code


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout_route():
    """用户注销（客户端清除令牌即可，服务端无状态）"""
    return jsonify({"success": True, "message": "注销成功"}), 200


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password_route():
    """忘记密码 - 发送密码重置链接"""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400

    result = generate_reset_token(email)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password_route():
    """重置密码 - 使用重置令牌设置新密码"""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not token:
        return jsonify({"success": False, "message": "重置令牌不能为空"}), 400

    if not password:
        return jsonify({"success": False, "message": "新密码不能为空"}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "两次输入的密码不一致"}), 400

    result = reset_password(token, password)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@auth_bp.route("/verify-reset-token", methods=["POST"])
def verify_reset_token_route():
    """验证重置令牌是否有效"""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"success": False, "message": "重置令牌不能为空"}), 400

    result = validate_reset_token(token)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email_route():
    """邮箱验证（预留接口）"""
    return jsonify({"success": False, "message": "功能开发中"}), 501
