# services/node_service.py

import base64
import errno
import os
import re
import socket
import struct
import threading
import time
import uuid
from pathlib import Path
from prediction.predictor import predict_image, predict_image_llm
from common.constants import ALLOWED_IMAGE_EXTENSIONS as _ALLOWED_IMAGE_EXTENSIONS
from common.protocol import node_json_protocol
from config.log_config import get_logger
from config.base import (
    LOCAL_PORT,
    TCP_HOST,
    TCP_PORT,
    NODE_ID,
    TOKEN,
    HEARTBEAT_INTERVAL_SEC,
    HEARTBEAT_RESPONSE_TIMEOUT_SEC,
    HEARTBEAT_MISS_LIMIT,
    RECONNECT_DELAY_SEC,
    MAX_TASKS,
    IMAGE_PATH,
    LLM_RECOGNITION_ENABLED,
    LLM_TIMEOUT_SEC,
    LOCAL_TASK_TIMEOUT_SEC,
    CAPABILITIES,
)

logger = get_logger("node_service")

# JSON 协议已提取到 src/common/protocol.py，此处使用节点端实例
json_protocol = node_json_protocol

# 全局任务数据字典和锁，用于异步处理LLM任务
task_data = {}
task_data_lock = threading.Lock()


# === TCP 客户端主逻辑 ===
def start_node_service():
    # 配置参数已移至 config/base.py，通过 .env 文件加载
    # 请勿在此处硬编码任何敏感数据

    # === 全局变量（在函数内使用）===
    s = None
    heartbeat_missed_count = 0
    last_heartbeat_send_time = 0  # 上次心跳发送时间
    last_heartbeat_response_time = 0  # 上次心跳响应时间
    connection_alive = True  # 连接状态标志
    reconnect_attempts = 0
    tasks = []
    tasks_lock = threading.Lock()  # 保护 tasks 列表的线程安全
    pending_tasks = {}  # task_id -> {store, local_image_path, effective_type, start_time, timeout_sec}
    pending_tasks_lock = threading.Lock()  # 保护 pending_tasks 的线程安全
    consecutive_none_count = 0  # recv_json 连续返回 None 的计数，超过阈值触发重连

    def _safe_close(sock):
        """安全关闭 socket：SO_LINGER 立即中止 + shutdown，静默处理所有错误。
        避免重连时因 TIME_WAIT 导致 EADDRINUSE (WinError 10048)。"""
        if not sock:
            return
        try:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            except Exception:
                pass
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            sock.close()
        except Exception:
            pass

    def _cleanup_image(image_path):
        """安全删除推理临时图片文件"""
        if not image_path or not os.path.exists(image_path):
            return
        # 只允许删除 IMAGE_PATH 目录下的文件，防止误删或路径遍历
        try:
            real_path = Path(os.path.abspath(image_path))
            real_base = Path(os.path.abspath(IMAGE_PATH))
            if real_base not in real_path.parents and real_path != real_base:
                logger.warning("拒绝清理 IMAGE_PATH 外的文件: %s", image_path)
                return
        except Exception as e:
            logger.warning("路径校验失败 %s: %s", image_path, e)
            return
        try:
            os.remove(image_path)
            logger.debug("已清理临时图片: %s", image_path)
        except Exception as e:
            logger.warning("清理临时图片失败 %s: %s", image_path, e)

    def _safe_image_extension(filename):
        """从文件名中提取安全的图片扩展名，非法扩展名返回空字符串。"""
        if not filename or not isinstance(filename, str):
            return ""
        # 取最后一段扩展名并归一化
        ext = Path(filename).suffix.lower()
        # 额外过滤路径分隔符（Path.suffix 已移除路径，再做一次防御）
        ext = re.sub(r"[\\/]+", "", ext)
        if ext in _ALLOWED_IMAGE_EXTENSIONS:
            return ext
        return ""

    # === 连接并注册函数（辅助函数）===
    def connect_and_register():
        nonlocal s, reconnect_attempts
        try:
            logger.info("尝试连接服务器...")

            # 修改1：确保关闭之前的socket（_safe_close 快速释放端口）
            if s:
                try:
                    _safe_close(s)
                except Exception:
                    pass
                s = None

            # 修改2：创建新socket并绑定本地端口（支持重试+回退随机端口）
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            assigned_port = None
            bind_port = LOCAL_PORT if LOCAL_PORT else 0

            if bind_port != 0:
                max_bind_attempts = 5
                for attempt in range(1, max_bind_attempts + 1):
                    try:
                        s.bind(("", bind_port))
                        assigned_port = s.getsockname()[1]
                        logger.info("已绑定本地端口: %s", assigned_port)
                        break
                    except OSError as bind_err:
                        if getattr(bind_err, "winerror", None) == 10048 or getattr(bind_err, "errno", None) == errno.EADDRINUSE:
                            logger.warning(
                                "本地端口 %s 被占用 (尝试 %s/%s)：%s",
                                bind_port, attempt, max_bind_attempts, bind_err,
                            )
                            time.sleep(1)
                            continue
                        else:
                            logger.warning("本地端口绑定失败: %s（继续尝试连接）", bind_err)
                            break
                else:
                    # 多次重试仍失败，回退到随机端口
                    try:
                        s.bind(("", 0))
                        assigned_port = s.getsockname()[1]
                        logger.warning("回退：绑定到随机本地端口 %s", assigned_port)
                    except Exception as e:
                        logger.warning("随机端口绑定也失败: %s（继续尝试连接）", e)
            else:
                try:
                    s.bind(("", 0))
                    assigned_port = s.getsockname()[1]
                    logger.info("未配置 LOCAL_PORT，使用随机本地端口: %s", assigned_port)
                except Exception as e:
                    logger.warning("随机端口绑定失败: %s（继续尝试连接）", e)

            s.connect((TCP_HOST, TCP_PORT))
            logger.info("已连接到服务器 %s:%s", TCP_HOST, TCP_PORT)

            # 重置状态
            nonlocal heartbeat_missed_count, last_heartbeat_send_time, last_heartbeat_response_time, consecutive_none_count
            heartbeat_missed_count = 0
            last_heartbeat_send_time = 0
            last_heartbeat_response_time = 0
            reconnect_attempts = 0
            consecutive_none_count = 0

            # 注册节点
            with tasks_lock:
                current_tasks = list(tasks)
            register_msg = {
                "type": "register",
                "timestamp": int(time.time()),
                "status": "ready",
                "data": {
                    "node_id": NODE_ID,
                    "token": TOKEN,
                    "tasks": current_tasks,
                    "max_tasks": MAX_TASKS,
                    "local_port": assigned_port,
                    "capabilities": CAPABILITIES,
                    # 附带 LLM 配置信息，供服务端决策任务重试间隔
                    "llm_enabled": LLM_RECOGNITION_ENABLED,
                    "llm_timeout_sec": LLM_TIMEOUT_SEC,
                },
            }
            json_protocol.send_json(s, register_msg)
            logger.info("已发送注册消息 %s:%s", TCP_HOST, TCP_PORT)

            return True
        except Exception as e:
            logger.error("连接或注册失败: %s", e)
            if s:
                try:
                    _safe_close(s)
                except Exception:
                    pass
                s = None
            return False

    # === 主循环 ===
    while True:
        # 初始连接
        if not connect_and_register():
            logger.error("初始连接失败，程序退出")
            return

        # === 心跳线程 ===
        def heartbeat_loop():
            nonlocal last_heartbeat_send_time, connection_alive
            while connection_alive:
                time.sleep(HEARTBEAT_INTERVAL_SEC)
                # 每次发送前捕获当前 socket，避免主线程重连置空 s 后
                # 心跳线程仍用 None 调用 sendall（NoneType 报错）。
                sock = s
                if sock is None or not connection_alive:
                    break
                try:
                    with tasks_lock:
                        current_tasks = list(tasks)
                    hb_msg = {
                        "type": "heartbeat",
                        "timestamp": int(time.time()),
                        "data": {
                            "node_id": NODE_ID,
                            "tasks": current_tasks,
                        },
                    }
                    json_protocol.send_json(sock, hb_msg)
                    last_heartbeat_send_time = time.time()
                    last_heartbeat_response_time = 0  # 重置，标记等待响应
                    logger.debug("发送心跳")
                except Exception as e:
                    logger.error("发送心跳异常: %s", e)
                    connection_alive = False
                    break

        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        # === 主接收循环 ====
        while connection_alive and s:
            # === 检查已完成的后台推理任务（非阻塞，local/LLM 统一处理） ===
            with pending_tasks_lock:
                pending_snapshot = list(pending_tasks.items())
            for tid, info in pending_snapshot:
                elapsed = time.time() - info["start_time"]
                timeout_sec = info.get("timeout_sec", LLM_TIMEOUT_SEC)
                if "value" in info["store"] or elapsed >= timeout_sec:
                    if "value" in info["store"]:
                        result = info["store"]["value"]
                    else:
                        logger.warning("推理任务 %s 等待超时 (%ds)", tid, timeout_sec)
                        result = {"success": False, "class_probs": [], "error": f"inference timeout after {timeout_sec} seconds"}
                    result["recognition_type"] = info["effective_type"]

                    response_msg = {
                        "type": "task_result",
                        "timestamp": int(time.time()),
                        "data": {
                            "node_id": NODE_ID,
                            "task_id": tid,
                            "result": result,
                            "processed_image_path": info["local_image_path"],
                        },
                    }
                    try:
                        json_protocol.send_json(s, response_msg)
                        logger.info("已返回推理任务 %s 的结果 (%s)", tid, info["effective_type"])
                    except Exception as send_err:
                        logger.error("发送推理任务结果失败: %s", send_err)
                    with tasks_lock:
                        if tid in tasks:
                            tasks.remove(tid)
                    with pending_tasks_lock:
                        pending_tasks.pop(tid, None)
                    # 清理临时图片文件
                    _cleanup_image(info["local_image_path"])

            # === 心跳超时检测 ===
            current_time = time.time()

            # 修正的超时检测逻辑：只在发送心跳后未收到响应时才计时
            if last_heartbeat_send_time > 0 and last_heartbeat_response_time == 0:
                # 已经发送心跳但未收到响应
                time_since_last_send = current_time - last_heartbeat_send_time
                if time_since_last_send > HEARTBEAT_RESPONSE_TIMEOUT_SEC:
                    if heartbeat_missed_count < HEARTBEAT_MISS_LIMIT:
                        heartbeat_missed_count += 1
                        logger.warning(
                            "⚠️ 心跳响应超时！(%s/%s) 上次发送: %.1fs 前",
                            heartbeat_missed_count, HEARTBEAT_MISS_LIMIT, time_since_last_send,
                        )
                    if heartbeat_missed_count >= HEARTBEAT_MISS_LIMIT:
                        logger.error(
                            "❗ 心跳连续丢失 %s 次，超过最大限制，准备断开并重连...",
                            heartbeat_missed_count,
                        )
                        connection_alive = False  # 标记连接失效
                        break  # 跳出主循环，触发重连逻辑

            # === 接收消息 ===
            try:
                # 设置接收超时，避免永久阻塞
                s.settimeout(1.0)  # 1秒超时
                msg = json_protocol.recv_json(s)
                s.settimeout(None)  # 恢复阻塞模式

                if msg is None:
                    # 连续 None 累计，超过阈值则标记连接失效以触发重连
                    consecutive_none_count += 1
                    if consecutive_none_count >= 10:
                        logger.warning(
                            "recv_json 连续返回 None %s 次，判定连接异常，触发重连",
                            consecutive_none_count,
                        )
                        connection_alive = False
                        break
                    continue

                # 成功收到消息，重置连续 None 计数
                consecutive_none_count = 0

                msg_type = msg.get("type")
                msg_data = msg.get("data", {})
                logger.debug("收到消息类型: %s", msg_type)

                # === 心跳响应处理 ====
                if msg_type == "heartbeat_ack":
                    logger.debug("收到心跳响应: %s", msg.get('message', ''))
                    heartbeat_missed_count = 0  # 重置丢失计数
                    last_heartbeat_response_time = time.time()  # 记录响应时间
                    last_heartbeat_send_time = 0  # 重置发送时间，准备下一次发送

                # === 注册响应 ===
                elif msg_type == "register_ack":
                    status = msg.get("status")
                    message = msg.get("message")
                    logger.info("注册结果: %s: %s", status, message)
                    if status != "success":
                        # 注册失败（如服务端数据库不可用）时立即触发重连，
                        # 而不是继续 recv 空数据直到累计 10 次 None。
                        logger.warning("注册未成功（%s），准备重连...", message)
                        connection_alive = False
                        break

                # === 任务状态响应 ===
                elif msg_type == "status_update_ack":
                    status = msg.get("status")
                    message = msg.get("message")
                    task_id = msg_data.get("task_id")
                    logger.info("任务状态更新: 任务ID: %s, 动作: %s", task_id, message)

                # === 任务处理 ===
                elif msg_type == "task":
                    try:
                        task_id = msg_data.get("task_id")
                        image_filename = msg_data.get("image_filename")
                        image_size = msg_data.get("image_size")
                        image_data_b64 = msg_data.get("image_data")
                        timestamp = msg.get("timestamp")
                        # 识别方式类型：local / llm / auto，默认 local
                        recognition_type = msg_data.get("recognition_type", "local")

                        if not all([task_id, image_filename, image_data_b64]):
                            logger.warning("任务数据不完整")
                            continue

                        logger.info(
                            "收到带图片任务: %s, 文件名: %s, 识别方式: %s, 大小: %s 字节, 时间戳: %s",
                            task_id, image_filename, recognition_type, image_size, timestamp,
                        )

                        # 更新当前任务列表和计数
                        with tasks_lock:
                            tasks.append(task_id)

                        # 解码 base64 图片数据
                        try:

                            image_bytes = base64.b64decode(image_data_b64)

                            # 验证解码后的大小
                            if len(image_bytes) != image_size:
                                logger.warning(
                                    "图片大小不匹配: 期望=%s, 实际=%s",
                                    image_size, len(image_bytes),
                                )

                            # 保存图片（使用 UUID 作为磁盘文件名，防止路径遍历）
                            os.makedirs(IMAGE_PATH, exist_ok=True)
                            safe_ext = _safe_image_extension(image_filename)
                            local_image_filename = f"{uuid.uuid4().hex}{safe_ext}"
                            local_image_path = os.path.join(IMAGE_PATH, local_image_filename)
                            with open(local_image_path, "wb") as f:
                                f.write(image_bytes)
                            logger.info("图片已保存到: %s", local_image_path)

                            # 根据 recognition_type 选择推理方式
                            # 优先使用节点配置的环境变量开关，兼容服务端指定类型
                            effective_type = recognition_type
                            if recognition_type == "auto":
                                effective_type = "llm" if LLM_RECOGNITION_ENABLED else "local"
                            elif recognition_type == "llm" and not LLM_RECOGNITION_ENABLED:
                                logger.warning("任务要求 LLM 识别但节点未启用，回退到本地模型")
                                effective_type = "local"

                            logger.info("推理方式: %s", effective_type)

                            # 统一将推理提交到后台线程执行（local / LLM 均异步），
                            # 主循环不阻塞，可继续接收新任务；完成结果由上方 pending_tasks 检查回传
                            store = {}
                            timeout_sec = LLM_TIMEOUT_SEC if effective_type == "llm" else LOCAL_TASK_TIMEOUT_SEC

                            def _run_inference(
                                _store=store,
                                _image_path=local_image_path,
                                _effective_type=effective_type,
                            ):
                                try:
                                    if _effective_type == "llm":
                                        _store["value"] = predict_image_llm(_image_path)
                                    else:
                                        _store["value"] = predict_image(_image_path)
                                except Exception as exc:
                                    logger.error("%s 推理失败: %s", _effective_type, exc, exc_info=True)
                                    _store["value"] = {
                                        "success": False,
                                        "class_probs": [],
                                        "error": f"{_effective_type} inference failed: {exc}",
                                    }

                            threading.Thread(target=_run_inference, daemon=True).start()
                            with pending_tasks_lock:
                                pending_tasks[task_id] = {
                                    "store": store,
                                    "local_image_path": local_image_path,
                                    "effective_type": effective_type,
                                    "start_time": time.time(),
                                    "timeout_sec": timeout_sec,
                                }
                            logger.info("推理任务 %s 已提交到后台 (%s)，主循环继续监听", task_id, effective_type)
                            # 不阻塞主循环，由 pending_tasks 检查处理结果
                            continue

                        except Exception as decode_error:
                            logger.error("图片数据解码失败: %s", decode_error)
                            error_msg = {
                                "type": "task_result",
                                "timestamp": int(time.time()),
                                "data": {
                                    "node_id": NODE_ID,
                                    "task_id": task_id,
                                    "result": None,
                                    "error": f"图片数据解码失败: {decode_error}",
                                },
                            }
                            json_protocol.send_json(s, error_msg)
                            with tasks_lock:
                                if task_id in tasks:
                                    tasks.remove(task_id)
                            _cleanup_image(local_image_path)

                    except Exception as e:
                        logger.error("处理带图片任务出错: %s", e)
                        error_msg = {
                            "type": "task_result",
                            "timestamp": int(time.time()),
                            "data": {
                                "node_id": NODE_ID,
                                "task_id": "unknown",
                                "result": None,
                                "error": f"处理任务出错: {e}",
                            },
                        }
                        json_protocol.send_json(s, error_msg)

                # === 其它消息 ===
                elif msg_type in ["msg", "error"]:
                    status = msg.get("status")
                    message = msg.get("message")
                    logger.info("服务端消息: %s - %s", status, message)

                else:
                    logger.warning("未知消息类型: %s", msg_type)

            except socket.timeout:
                # 接收超时是正常的，继续循环检查其他条件
                continue
            except (ConnectionError, OSError, struct.error) as e:
                logger.error("主循环连接异常: %s", e)
                connection_alive = False
                break
            except Exception as e:
                logger.error("主循环未预期异常: %s", e, exc_info=True)
                connection_alive = False
                break

        # === 连接异常处理 ===
        logger.info("连接异常，准备重连...")
        if s:
            try:
                _safe_close(s)
            except Exception:
                pass
            s = None

        # 增加重连延迟和最大尝试次数
        reconnect_attempts += 1
        if reconnect_attempts > 5:  # 最多尝试5次
            logger.error("重连尝试次数过多，退出程序")
            return

        time.sleep(RECONNECT_DELAY_SEC)
        connection_alive = True  # 重置连接状态
        heartbeat_missed_count = 0
        last_heartbeat_send_time = 0
        last_heartbeat_response_time = 0
        consecutive_none_count = 0

        # 清理未完成的后台推理任务及其临时图片文件
        with pending_tasks_lock:
            for info in pending_tasks.values():
                _cleanup_image(info.get("local_image_path"))
            pending_tasks.clear()

        # 清空任务列表（旧任务 ID 在重连后已失效）
        with tasks_lock:
            tasks.clear()

        # 外层 while True 会自动调用 connect_and_register() 重新连接
        # 无需在此处再次调用，避免重复连接


# # ======================
# # === 启动入口 ===
# # ======================
# if __name__ == '__main__':
#     start_node_service()
