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

# CORS 配置
# 前端（localhost:8000）通过 JS 跨域直连 Flask（localhost:13138）完成登录等操作，
# 因此必须默认放行跨域；确需收紧时再在 .env 中配置 ALLOWED_ORIGINS 白名单。
allowed_origins = (os.getenv("ALLOWED_ORIGINS", "") or "").strip()
if allowed_origins:
    if allowed_origins == "*":
        CORS(app, origins="*")
    else:
        CORS(app, origins=[o.strip() for o in allowed_origins.split(",") if o.strip()])
else:
    CORS(app)  # 开发/默认环境回退为允许所有来源，保证登录等跨域请求可用

# 注册路由蓝图
from routes.upload_routes import upload_bp
from routes.dashboard_routes import dashboard_bp
from routes.node_routes import node_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.api_key_routes import api_key_bp

app.register_blueprint(upload_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(node_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_key_bp)
