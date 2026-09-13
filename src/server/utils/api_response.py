# utils/api_response.py
"""统一响应信封与机器可读错误码（灰度增量，不破坏既有字段）。

历史上有三套响应形态并存：
  A {success, message, data}             —— /auth、/users、/api-keys、/admin、/models
  B {type, timestamp, data|status|...}   —— /dashboard、/nodes、/upload、/tasks
  C {error}                              —— /dashboard 的异常分支

本模块在响应出口处**只做加法**，不改动、不删除任何已有字段：
  - success：B/C 形态缺失时按 HTTP 状态码补上（已有则保留原值）
  - code：机器可读错误码（端点可用 set_code() 覆盖默认推导值）
  - message：C 形态缺失时用 error 的值补上，便于客户端统一展示

另外把 Flask 默认的 HTML 错误页（404/405/413/500…）也换成同款 JSON 信封。
非 JSON、流式（SSE）、direct_passthrough 响应一律跳过。
"""

import json

from flask import current_app, g, jsonify

# ---------------------------------------------------------------
# 状态码 -> 默认 code
# ---------------------------------------------------------------
DEFAULT_CODES = {
    200: "OK",
    201: "CREATED",
    202: "ACCEPTED",
    204: "NO_CONTENT",
    400: "INVALID_PARAMS",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    503: "SERVICE_UNAVAILABLE",
}
ERROR_CODE = "ERROR"

# 通用码
CODE_OK = "OK"
CODE_CREATED = "CREATED"
CODE_ACCEPTED = "ACCEPTED"
CODE_INVALID_PARAMS = "INVALID_PARAMS"
CODE_UNAUTHORIZED = "UNAUTHORIZED"
CODE_FORBIDDEN = "FORBIDDEN"
CODE_NOT_FOUND = "NOT_FOUND"
CODE_RATE_LIMITED = "RATE_LIMITED"
CODE_INTERNAL_ERROR = "INTERNAL_ERROR"
CODE_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
CODE_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

# 业务码
CODE_AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
CODE_AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
CODE_AUTH_TOKEN_TYPE_INVALID = "AUTH_TOKEN_TYPE_INVALID"
CODE_AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
CODE_AUTH_REFRESH_INVALID = "AUTH_REFRESH_TOKEN_INVALID"
CODE_PERMISSION_DENIED = "PERMISSION_DENIED"
CODE_API_KEY_MISSING = "API_KEY_MISSING"
CODE_API_KEY_INVALID = "API_KEY_INVALID"
CODE_MAINTENANCE_MODE = "MAINTENANCE_MODE"
CODE_DB_UNAVAILABLE = "DB_UNAVAILABLE"

# HTTP 异常的中文提示（替换 Werkzeug 的英文 description）
HTTP_MESSAGES = {
    400: "请求参数错误",
    401: "未认证或认证已失效",
    403: "无权限访问",
    404: "接口不存在",
    405: "请求方法不允许",
    408: "请求超时",
    413: "请求体过大",
    415: "不支持的媒体类型",
    429: "请求过于频繁",
    500: "服务器内部错误",
    501: "功能未实现",
    503: "服务暂不可用",
}


def default_code(status_code: int) -> str:
    """按 HTTP 状态码推导默认 code。"""
    return DEFAULT_CODES.get(status_code, ERROR_CODE)


def set_code(code: str):
    """为本次请求指定返回 code（覆盖按状态码推导的默认值）。"""
    try:
        g.api_code = code
    except RuntimeError:  # 没有应用上下文时静默忽略
        pass


def normalize_payload(payload, status_code: int, code: str = None):
    """给响应体补齐 success / code / message。

    纯函数（不依赖 Flask 上下文），便于单测。
    返回 (payload, changed)。
    """
    if not isinstance(payload, dict):
        return payload, False

    changed = False

    if "success" not in payload:
        payload["success"] = 200 <= int(status_code) < 300
        changed = True

    if "code" not in payload:
        payload["code"] = code or default_code(int(status_code))
        changed = True

    if "message" not in payload and isinstance(payload.get("error"), str):
        payload["message"] = payload["error"]
        changed = True

    return payload, changed


def normalize_response(response):
    """after_request 钩子：对 JSON 响应做信封收口。"""
    # 流式响应（SSE）不能读 body，直接放行
    if response.direct_passthrough or response.is_streamed:
        return response
    if response.mimetype != "application/json":
        return response
    if response.status_code == 204:
        return response

    raw = response.get_data(as_text=True)
    if not raw:
        return response

    try:
        payload = json.loads(raw)
    except ValueError:
        return response

    payload, changed = normalize_payload(payload, response.status_code, getattr(g, "api_code", None))
    if not changed:
        return response

    # 用与 jsonify 相同的序列化器，保持转义/编码风格一致
    response.set_data(current_app.json.dumps(payload))
    return response


def _json_error(error):
    """把 Werkzeug 的 HTML 错误页换成统一 JSON 信封。"""
    from werkzeug.exceptions import HTTPException

    allow_header = None

    if isinstance(error, HTTPException):
        status_code = error.code or 500
        message = HTTP_MESSAGES.get(status_code) or error.description or "请求失败"
        try:
            allow_header = error.get_response().headers.get("Allow")
        except Exception:
            allow_header = None
    else:
        current_app.logger.exception("未捕获异常: %s", error)
        status_code, message = 500, HTTP_MESSAGES[500]

    response = jsonify({
        "success": False,
        "code": default_code(status_code),
        "message": message,
    })
    if allow_header:
        response.headers["Allow"] = allow_header
    return response, status_code


def install(app):
    """在 Flask 应用上安装信封收口与 JSON 错误处理。"""
    app.after_request(normalize_response)
    app.register_error_handler(Exception, _json_error)
    return app
