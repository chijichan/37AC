# runserver.py
"""服务启动入口 - 初始化日志、TCP服务、Flask Web服务"""

from AC_web import app
import threading
from services.tcp_service import start_tcp_server
from config.base import WEB_HOST, WEB_PORT, TSAC_DEBUG
from config.log_config import init_logging, get_logger

# ======================
# === 主程序入口 ===
# ======================
if __name__ == "__main__":
    # === 初始化统一日志系统 ===
    init_logging()
    logger = get_logger("runserver")
    logger.info("=" * 80)
    logger.info("  37AC 服务端启动中...")
    logger.info("  Flask 监听: %s:%s, DEBUG=%s", WEB_HOST, WEB_PORT, TSAC_DEBUG)
    logger.info("  TCP 监听:  0.0.0.0:13137")
    logger.info("=" * 80)

    # === 启动 TCP 服务（监听 13137，接收节点连接）===
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()

    # === 启动 Flask Web 服务 ===
    logger.info("[启动] Flask Web 服务启动中...")
    app.run(WEB_HOST, WEB_PORT, TSAC_DEBUG)
