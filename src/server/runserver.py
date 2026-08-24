# runserver.py
"""服务启动入口 - 初始化日志、TCP服务、Flask Web服务"""

import os
import socket
import subprocess
import sys
from AC_web import app
import threading
from services.listen_service import start_tcp_server
from config.base import WEB_HOST, WEB_PORT, TCP_PORT, TSAC_DEBUG
from config.log_config import init_logging, get_logger


def _is_port_in_use(host: str, port: int) -> bool:
    """尝试绑定端口判断是否已被占用（跨平台）。

    能成功 bind 说明端口空闲；抛出 OSError（Windows 10048 / EADDRINUSE）
    说明已有进程监听。

    注意：这里不能设置 SO_REUSEADDR —— Windows 下该选项允许重复绑定到
    已占用端口，会导致检测失效（漏报）。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def _find_pids_listening(ports: set) -> set:
    """返回正在监听指定端口的进程 PID 集合。"""
    pids = set()
    try:
        import psutil
    except ImportError:
        return pids

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for conn in proc.net_connections(kind="inet"):
                if (
                    conn.status == psutil.CONN_LISTEN
                    and conn.laddr
                    and conn.laddr.port in ports
                ):
                    pids.add(proc.pid)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return pids


def _kill_pids(pids: set) -> list:
    """按 PID 终止进程，返回成功终止的 PID 列表。"""
    killed = []
    for pid in pids:
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.kill()
            proc.wait(timeout=5)
            killed.append(pid)
            continue
        except Exception:
            # psutil 权限不足等场景，交给系统命令兜底
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                subprocess.run(
                    ["kill", "-9", str(pid)],
                    capture_output=True,
                    check=False,
                )
            killed.append(pid)
    return killed


def _kill_port_processes(ports: set) -> list:
    """终止监听指定端口的进程，返回已终止的 PID 列表。"""
    pids = _find_pids_listening(ports)
    if not pids:
        return []
    return _kill_pids(pids)


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
    logger.info("  TCP 监听:  0.0.0.0:%s", TCP_PORT)
    logger.info("=" * 80)

    # === 端口占用检测（reloader 子进程不重复检查） ===
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        check_ports = {
            WEB_PORT,  # Flask HTTP
            TCP_PORT,  # TCP 节点管理
        }
        in_use = sorted(
            p for p in check_ports
            if _is_port_in_use("0.0.0.0", p) or _is_port_in_use(WEB_HOST, p)
        )
        if in_use:
            port_str = ", ".join(str(p) for p in in_use)
            if not sys.stdin.isatty():
                logger.error(
                    "端口 %s 已被占用，可能已有服务端在运行；"
                    "非交互环境请先停止旧进程再启动",
                    port_str,
                )
                sys.exit(1)

            print()
            try:
                answer = input(
                    f"检测到端口 {port_str} 已被占用，可能已有服务端在运行。\n"
                    f"是否杀掉已有进程并启动新程序？(y/N): "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                answer = "n"  # 无输入/中断一律视为取消
            if answer in ("y", "yes"):
                killed = _kill_port_processes(set(in_use))
                if not killed:
                    logger.error("未能自动停止占用端口的进程，请手动处理后再启动")
                    sys.exit(1)
                logger.info("已停止旧服务端进程: %s", ", ".join(map(str, killed)))
                # 确认端口已释放
                still_in_use = [
                    p for p in in_use
                    if _is_port_in_use("0.0.0.0", p) or _is_port_in_use(WEB_HOST, p)
                ]
                if still_in_use:
                    logger.error(
                        "端口 %s 仍被占用，可能权限不足或进程未退出，请手动处理",
                        ", ".join(str(p) for p in still_in_use),
                    )
                    sys.exit(1)
            else:
                logger.info("用户取消启动，退出。如需启动请先停止旧服务端")
                sys.exit(0)

    # === 检测调试器 ===
    # sys.gettrace() 在调试器 (debugpy) 下返回非 None，正常运行为 None
    in_debugger = sys.gettrace() is not None
    # 调试器下禁用 reloader，否则 Werkzeug 父进程 sys.exit(3) 会被 debugpy 捕获报错
    use_reloader = TSAC_DEBUG and not in_debugger

    # === 启动 TCP 服务 ===
    # Flask 启用 reloader 时会先创建一个父进程再 fork 子进程
    # 只在子进程 (WERKZEUG_RUN_MAIN=true) 或单进程模式下启动 TCP
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not use_reloader:
        tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
        tcp_thread.start()
        logger.info("TCP 节点管理服务已启动")
    else:
        logger.info("reloader 父进程，TCP 服务将由子进程接管")

    # === 启动 Flask Web 服务 ===
    logger.info("Flask Web 服务启动中...")
    if in_debugger:
        logger.info("检测到调试器，已禁用 auto-reloader")
    # threaded=True：Werkzeug 开发服务器默认单线程，一个 SSE/长请求会阻塞
    # 其他所有 HTTP 请求，导致无法同时接收多个上传任务，必须开启多线程
    app.run(WEB_HOST, WEB_PORT, TSAC_DEBUG, threaded=True, use_reloader=use_reloader)
