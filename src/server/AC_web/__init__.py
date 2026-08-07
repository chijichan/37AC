"""
The flask application package.
"""

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# 限制上传体大小为 10MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# CORS 配置
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins:
    CORS(app, origins=[o.strip() for o in allowed_origins.split(",") if o.strip()])
else:
    CORS(app)  # 开发环境回退为允许所有来源

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
