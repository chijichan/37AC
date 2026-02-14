# runserver.py
import os
from AC_web import app
import threading
from services.tcp_services import start_tcp_server
import config

# ======================
# === 主程序入口 ===
# ======================
if __name__ == "__main__":
    # === 启动 TCP 服务（监听 13137，接收节点连接）===
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()
    print(f"[✅] TCP 服务已启动（监听 {config.TCP_PORT}，用于节点连接、注册、心跳）")

    # === 启动 Flask Web 服务 ===
    app.run(config.WEB_HOST, config.WEB_PORT, config.TSAC_DEBUG)
