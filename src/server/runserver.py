# runserver.py
"""服务启动入口 - 初始化日志、TCP服务、Flask Web服务"""

import os
from AC_web import app
import threading
from services.listen_service import start_tcp_server
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

    # === 启动 TCP 服务 ===
    # Flask 启用 reloader 时会先创建一个父进程再 fork 子进程
    # 只在子进程 (WERKZEUG_RUN_MAIN=true) 或单进程模式下启动 TCP
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not TSAC_DEBUG:
        tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
        tcp_thread.start()
        logger.info("TCP 节点管理服务已启动")
    else:
        logger.info("reloader 父进程，TCP 服务将由子进程接管")

    # === 启动 Flask Web 服务 ===
    logger.info("[启动] Flask Web 服务启动中...")
    app.run(WEB_HOST, WEB_PORT, TSAC_DEBUG)
