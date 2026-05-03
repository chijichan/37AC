# config/base.py
"""基础配置 - 数据库、服务器、JWT 等"""

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent

# MySQL 数据库配置（用于节点 Token 认证、后续可扩展更多配置）
DB_CONFIG = {
    "host": "154.9.253.170",  # 数据库地址
    "user": "37AC",  # 数据库用户名
    "password": "8LhdjGBYhPZRW72D",  # 请替换为你的真实数据库密码！
    "database": "37ac",  # 数据库名，确保已运行你提供的建表 SQL
    "charset": "utf8mb4",
    # 'cursorclass': pymysql.cursors.DictCursor
}

# FLASK web服务器配置
WEB_HOST = "127.0.0.1"
WEB_PORT = 13138

# 前端地址（用于构建密码重置等外链）
FRONTEND_URL = "http://127.0.0.1:8000"

# 全局配置
# - DEBUG 模式
TSAC_DEBUG = False

# - 服务端口
TCP_HOST = "0.0.0.0"
TCP_PORT = 13137

# 暂存
IMAGE_PATH = ROOT_PATH / "saves" / "uploads"
IMAGE_PATH.mkdir(exist_ok=True)

# - 日志配置
LOGS_PATH = ROOT_PATH / "saves" / "logs"
LOGS_PATH.mkdir(exist_ok=True)
monitor_counter = 0

# JWT 配置
JWT_SECRET = (
    "37AC-JWT-Secret-Key-2024-With-Extra-Length-For-SHA256"  # 生产环境请替换为强密钥
)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 访问令牌过期时间（秒），默认1小时
JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 刷新令牌过期时间（秒），默认30天
