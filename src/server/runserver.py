# runserver.py
from AC_web import app
import threading
from services.tcp_service import start_tcp_server
from config import WEB_HOST, WEB_PORT, TSAC_DEBUG

# ======================
# === 主程序入口 ===
# ======================
if __name__ == "__main__":
    # === 启动 TCP 服务（监听 13137，接收节点连接）===
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()

    # === 启动 Flask Web 服务 ===
    app.run(WEB_HOST, WEB_PORT, TSAC_DEBUG)
