# config/base.py
"""基础配置 - 数据库、服务器、JWT 等（从环境变量读取）"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件（位于项目根目录）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROOT_PATH = Path(__file__).resolve().parent.parent

# MySQL 数据库配置（从环境变量读取）
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": os.getenv("DB_CHARSET"),
}

# FLASK web服务器配置
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "13138"))

# 前端地址（用于构建密码重置等外链）
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000")

# 全局配置
# - DEBUG 模式
TSAC_DEBUG = os.getenv("TSAC_DEBUG", "False").lower() == "true"

# - 服务端口
TCP_HOST = os.getenv("TCP_HOST", "0.0.0.0")
TCP_PORT = int(os.getenv("TCP_PORT", "13137"))

# - 日志配置
LOGS_PATH = ROOT_PATH / "saves" / "logs"
LOGS_PATH.mkdir(exist_ok=True)

# JWT 配置（从环境变量读取，不提供硬编码默认值）
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000"))

# 任务重试配置
TASK_RETRY_INTERVAL_LOCAL = int(os.getenv("TASK_RETRY_INTERVAL_LOCAL", "10"))
TASK_RETRY_INTERVAL_LLM = int(os.getenv("TASK_RETRY_INTERVAL_LLM", "90"))
TASK_MAX_RETRIES = int(os.getenv("TASK_MAX_RETRIES", "3"))

# 限流配置
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "1"))
