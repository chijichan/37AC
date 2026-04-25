"""
The flask application package.
"""

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
# CORS(app, origins=['https://www.322337.xyz'])
CORS(app)  # 允许所有来源访问

# 注册路由蓝图
from routes.upload_routes import upload_bp
from routes.dashboard_routes import dashboard_bp
from routes.node_routes import node_bp

app.register_blueprint(upload_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(node_bp)
