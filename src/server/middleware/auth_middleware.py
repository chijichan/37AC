# middleware/auth_middleware.py
"""认证与权限中间件 - 提供 JWT 验证和角色权限控制"""

from functools import wraps

from flask import request, jsonify, g

from services.auth_service import decode_token, verify_token


def _verify_access_token(token):
    """校验 access token 的有效性、类型及用户状态。

    返回 (payload, error_response, status_code)。
    payload 仅在验证通过时非 None。
    """
    if not token:
        return None, {"success": False, "message": "未提供认证令牌"}, 401

    payload = decode_token(token)
    if not payload:
        return None, {"success": False, "message": "令牌无效或已过期"}, 401

    # 拒绝 refresh token 当作 access token 使用
    if payload.get("type") == "refresh":
        return None, {"success": False, "message": "请使用访问令牌而非刷新令牌"}, 401

    # 校验用户是否被禁用或删除，并以数据库中的最新角色覆盖 token 内角色
    result = verify_token(token)
    if not result.get("success"):
        return None, {"success": False, "message": result.get("message")}, 401

    user_data = result.get("data") or {}
    payload["user_id"] = user_data.get("user_id", payload.get("user_id"))
    payload["role"] = user_data.get("role", payload.get("role"))

    return payload, None, None


def login_required(f):
    """需要登录认证的装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        payload, error, status = _verify_access_token(token)
        if error:
            return jsonify(error), status

        # 将用户信息存入 Flask 全局上下文
        g.user_id = payload.get("user_id")
        g.user_role = payload.get("role")

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """需要管理员权限的装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        payload, error, status = _verify_access_token(token)
        if error:
            return jsonify(error), status

        if payload.get("role") != "admin":
            return jsonify({"success": False, "message": "需要管理员权限"}), 403

        # 将用户信息存入 Flask 全局上下文
        g.user_id = payload.get("user_id")
        g.user_role = payload.get("role")

        return f(*args, **kwargs)

    return decorated


def optional_login(f):
    """可选登录的装饰器（有 token 则解析，没有也不阻止）"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if token:
            payload = decode_token(token)
            if payload:
                # 可选登录不强制校验用户状态，避免影响公开读取接口
                g.user_id = payload.get("user_id")
                g.user_role = payload.get("role")

        return f(*args, **kwargs)

    return decorated


def _extract_token() -> str:
    """从请求头中提取 JWT 令牌"""
    # 优先从 Authorization 头提取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # 其次从查询参数提取
    token = request.args.get("token")
    if token:
        return token

    # 最后从 Cookie 提取
    token = request.cookies.get("access_token")
    return token
