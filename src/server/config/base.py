# config/base.py
"""基础配置 - 数据库、服务器、JWT 等（从环境变量读取）"""

import sys
import os
from pathlib import Path

# 将 src/ 加入 sys.path，使 common 公共包可被导入
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

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
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    # 连接超时：避免 MySQL 不可达时长时间阻塞节点注册/鉴权流程
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
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
LOGS_PATH.mkdir(parents=True, exist_ok=True)

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

# - 图片缓存与临时文件（需求3/4）
#   tmp：在途/短期原图（任务完成或超时后按 TTL 清理）
#   cache：留存副本（压缩后的 JPEG，供前端回看）
# 下列值都是**默认值**，后台「系统设置」里的同名键可覆盖（见 services/settings_service.py）
IMAGE_TMP_PATH = Path(os.getenv("IMAGE_TMP_DIR", str(ROOT_PATH / "saves" / "tmp")))
IMAGE_CACHE_PATH = Path(os.getenv("IMAGE_CACHE_DIR", str(ROOT_PATH / "saves" / "cache")))
IMAGE_TMP_MAX_MB = int(os.getenv("IMAGE_TMP_MAX_MB", "2048"))
IMAGE_CACHE_MAX_MB = int(os.getenv("IMAGE_CACHE_MAX_MB", "2048"))
IMAGE_TMP_TTL_SEC = int(os.getenv("IMAGE_TMP_TTL_SEC", "3600"))
IMAGE_CACHE_TTL_SEC = int(os.getenv("IMAGE_CACHE_TTL_SEC", "604800"))
# 压缩：最长边大于该值时压缩（0 表示不压缩）
IMAGE_COMPRESS_MAX_SIDE = int(os.getenv("IMAGE_COMPRESS_MAX_SIDE", "512"))
IMAGE_COMPRESS_QUALITY = int(os.getenv("IMAGE_COMPRESS_QUALITY", "85"))
# 回收线程扫描间隔；tmp 中该秒数内的新文件不参与淘汰（保护在途任务）
IMAGE_CLEAN_INTERVAL_SEC = int(os.getenv("IMAGE_CLEAN_INTERVAL_SEC", "300"))
IMAGE_TMP_PROTECT_SEC = int(os.getenv("IMAGE_TMP_PROTECT_SEC", "300"))
# 服务端清理图片后，是否允许向处理该任务的节点补拉
IMAGE_NODE_REFETCH = os.getenv("IMAGE_NODE_REFETCH", "True").lower() == "true"
