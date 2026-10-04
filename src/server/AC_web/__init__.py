"""
The flask application package.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# 在读取环境变量前先加载 .env，避免 runserver 先导入本包时
# config.base 的 load_dotenv() 尚未执行，导致 ALLOWED_ORIGINS 读不到。
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)

# 限制上传体大小为 10MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# CORS 配置（**默认收紧**）
# 前端（如 PHP 站点）通过 JS 跨域直连 Flask 时，必须显式配置允许的来源：
#   ALLOWED_ORIGINS=http://your-host:8000,http://127.0.0.1:8000
# 未配置时不添加任何跨域响应头（仅同源可用）。
# 开发期确实要放开所有来源，才设置 CORS_ALLOW_ALL=True（生产不要用）。
allowed_origins = (os.getenv("ALLOWED_ORIGINS", "") or "").strip()
allow_all = (os.getenv("CORS_ALLOW_ALL", "False") or "").strip().lower() == "true"
if allowed_origins and allowed_origins != "*":
    _origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
    CORS(app, origins=_origins)
    app.logger.info("CORS 白名单已启用: %s", _origins)
elif allow_all or allowed_origins == "*":
    CORS(app, origins="*")
    app.logger.warning(
        "CORS 已放开为所有来源（CORS_ALLOW_ALL=True / ALLOWED_ORIGINS=*）—— 仅建议开发环境使用"
    )
else:
    app.logger.warning(
        "未配置 ALLOWED_ORIGINS：不添加跨域响应头（仅同源可用）。"
        "需要前端跨域请配置来源白名单，例如 ALLOWED_ORIGINS=http://your-host:8000"
    )

# 注册路由蓝图
from routes.upload_routes import upload_bp
from routes.dashboard_routes import dashboard_bp
from routes.node_routes import node_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.api_key_routes import api_key_bp
from routes.model_routes import model_bp

app.register_blueprint(upload_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(node_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_key_bp)
app.register_blueprint(model_bp)

# 响应信封收口：给所有 JSON 响应补 success / code（只加字段，不动旧字段），
# 并把 Flask 默认的 HTML 错误页换成同款 JSON（见 utils/api_response.py）
from utils.api_response import install as install_api_response

install_api_response(app)


# 维护模式下始终放行的路径前缀（登录/刷新令牌、后台管理、静态资源）
_MAINTENANCE_ALLOWED_PREFIXES = ("/auth", "/admin", "/static")


@app.before_request
def _maintenance_gate():
    """维护模式（后台「系统设置」maintenance_mode=1）下拒绝普通请求。

    - CORS 预检、登录接口、后台管理接口始终放行，保证管理员能进去关掉开关；
    - 携带有效管理员令牌的请求也放行，便于后台页面继续调用接口；
    - 读取设置失败时按「非维护模式」处理，避免数据库抖动导致整站 503。
    """
    from flask import request, jsonify

    if request.method == "OPTIONS":
        return None

    path = request.path or "/"
    if path.startswith(_MAINTENANCE_ALLOWED_PREFIXES):
        return None

    try:
        from services import settings_service
        if settings_service.get_setting("maintenance_mode", "0") != "1":
            return None
    except Exception:
        return None

    try:
        from middleware.auth_middleware import _extract_token, _verify_access_token
        payload, _error, _status = _verify_access_token(_extract_token())
        if payload and payload.get("role") == "admin":
            return None
    except Exception:
        pass

    from utils.api_response import CODE_MAINTENANCE_MODE

    return jsonify({
        "success": False,
        "code": CODE_MAINTENANCE_MODE,
        "message": "系统维护中，请稍后再试",
        "maintenance": True,
    }), 503
