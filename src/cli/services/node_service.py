# services/node_service.py

import socket
import threading
import json
import time
import os
import struct
import errno
import base64
from prediction.predictor import predict_image, predict_image_llm
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
)

logger = get_logger("node_service")


class JsonProtocol:
    """JSON 消息发送和接收类，使用自定义消息头长度前缀协议"""

    def __init__(self):
        self.send_header = "node"
        self.expected_headers = ["server"]  # 只期待服务端发来的 "server@" 标记
        self._recv_buffer = b""  # 保存 recv 未消费完的溢出数据

    def send_json(self, sock, msg_dict):
        """发送一条 JSON 消息到 socket"""
        try:
            json_str = json.dumps(msg_dict)
            json_bytes = json_str.encode("utf-8")

            content_length = len(json_bytes)
            header_str = f"{self.send_header}@{content_length}"
            header_bytes = header_str.encode("utf-8")

            full_message = header_bytes + json_bytes
            sock.sendall(full_message)

            logger.debug(
                f"[send_json] 发送成功: 头部='{header_str}', 内容长度={content_length}"
            )

        except Exception as e:
            logger.error(f"[send_json] 发送失败: {e}")
            raise

    def recv_json(self, sock):
        """从 socket 接收一条完整的 JSON 消息"""
        try:
            # 1. 查找消息标记
            found_marker, found_header, buffer = self._find_message_marker(sock)
            if not found_marker:
                return None

            # 2. 解析内容长度
            content_length, content_start = self._parse_content_length(
                found_marker, buffer
            )
            if content_length is None:
                return None

            # 3. 接收完整内容
            data = self._receive_full_content(
                sock, buffer, content_start, content_length
            )
            if data is None:
                return None

            # 4. 解码并返回JSON
            return self._decode_json(data, found_header)

        except (ConnectionError, ValueError, struct.error) as e:
            logger.debug(
                f"[recv_json] 接收 JSON 失败 (期望标记: {self.expected_headers}): {e}"
            )
            return None
        # socket.timeout 不在此处捕获，由主循环 except socket.timeout 统一处理（不计入 None 计数）

    def _find_message_marker(self, sock):
        """查找消息标记（带最大迭代保护，防止垃圾数据导致无限循环）"""
        expected_markers = [
            f"{header}@".encode("utf-8") for header in self.expected_headers
        ]
        # 从余留缓冲区开始，避免上次未消费完的数据丢失
        buffer = self._recv_buffer
        self._recv_buffer = b""
        max_marker_len = max(len(marker) for marker in expected_markers)
        max_iterations = 50  # 防止垃圾数据导致无限循环
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            chunk = sock.recv(1024)
            if not chunk:
                return None, None, None

            buffer += chunk

            # 检查所有可能的标记
            for marker in expected_markers:
                marker_pos = buffer.find(marker)
                if marker_pos != -1:
                    buffer = buffer[marker_pos:]
                    found_header = marker[:-1].decode("utf-8")
                    return marker, found_header, buffer

            # 检查缓冲区是否过大
            if len(buffer) > max_marker_len * 2:
                logger.debug(
                    f"[recv_json] 未找到期望标记 {self.expected_headers}，清空缓冲区重新搜索"
                )
                buffer = b""

        logger.warning(
            f"[recv_json] 连续 {max_iterations} 次未找到期望标记 {self.expected_headers}，放弃并返回 None"
        )
        return None, None, None

    def _parse_content_length(self, marker, buffer):
        """解析内容长度"""
        length_start = len(marker)
        num_buffer = b""

        for i in range(length_start, len(buffer)):
            char_byte = buffer[i : i + 1]
            try:
                char = char_byte.decode("utf-8")
                if char.isdigit():
                    num_buffer += char_byte
                else:
                    break
            except UnicodeDecodeError:
                break

        if not num_buffer:
            logger.error(
                f"[recv_json] 无法解析长度数字，找到标记: '{marker[:-1].decode('utf-8')}@'"
            )
            return None, None

        content_length = int(num_buffer.decode("utf-8"))
        content_start = length_start + len(num_buffer)

        logger.debug(
            f"[recv_json] 解析到内容长度: {content_length}, 起始位置: {content_start}"
        )
        return content_length, content_start

    def _receive_full_content(self, sock, buffer, content_start, content_length):
        """接收完整内容，余留数据存入 _recv_buffer 供下次使用"""
        data = buffer[content_start:]

        while len(data) < content_length:
            remaining = content_length - len(data)
            part = sock.recv(min(remaining, 4096))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 保存本次未消费完的溢出数据，防止丢失后续消息头
        self._recv_buffer = data[content_length:]
        return data[:content_length]

    def _decode_json(self, data, found_header):
        """解码JSON并添加来源信息"""
        text = data.decode("utf-8")
        result = json.loads(text)
        result["_source_header"] = found_header
        return result


# 全局 JSON 协议实例
json_protocol = JsonProtocol()

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
    last_heartbeat_send_time = 0  # 重命名为发送时间
    last_heartbeat_response_time = 0  # 响应时间
    connection_alive = True  # 连接状态标志
    reconnect_attempts = 0
    tasks = []
    pending_llm_tasks = {}  # task_id -> {store, local_image_path, effective_type, start_time}
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

    # === 连接并注册函数（辅助函数）===
    def connect_and_register():
        nonlocal s, reconnect_attempts
        try:
            logger.info("[节点] 尝试连接服务器...")

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
                        logger.info(f"[节点] 已绑定本地端口: {assigned_port}")
                        break
                    except OSError as bind_err:
                        if getattr(bind_err, "winerror", None) == 10048 or getattr(bind_err, "errno", None) == errno.EADDRINUSE:
                            logger.warning(
                                f"[节点] 本地端口 {bind_port} 被占用 (尝试 {attempt}/{max_bind_attempts})：{bind_err}"
                            )
                            time.sleep(1)
                            continue
                        else:
                            logger.warning(f"[节点] 本地端口绑定失败: {bind_err}（继续尝试连接）")
                            break
                else:
                    # 多次重试仍失败，回退到随机端口
                    try:
                        s.bind(("", 0))
                        assigned_port = s.getsockname()[1]
                        logger.warning(f"[节点] 回退：绑定到随机本地端口 {assigned_port}")
                    except Exception as e:
                        logger.warning(f"[节点] 随机端口绑定也失败: {e}（继续尝试连接）")
            else:
                try:
                    s.bind(("", 0))
                    assigned_port = s.getsockname()[1]
                    logger.info(f"[节点] 未配置 LOCAL_PORT，使用随机本地端口: {assigned_port}")
                except Exception as e:
                    logger.warning(f"[节点] 随机端口绑定失败: {e}（继续尝试连接）")

            s.connect((TCP_HOST, TCP_PORT))
            logger.info(f"[节点] 已连接到服务器 {TCP_HOST}:{TCP_PORT}")

            # 重置状态
            nonlocal heartbeat_missed_count, last_heartbeat_send_time, last_heartbeat_response_time, consecutive_none_count
            heartbeat_missed_count = 0
            last_heartbeat_send_time = 0
            last_heartbeat_response_time = 0
            reconnect_attempts = 0
            consecutive_none_count = 0

            # 注册节点
            register_msg = {
                "type": "register",
                "timestamp": int(time.time()),
                "status": "ready",
                "data": {
                    "node_id": NODE_ID,
                    "token": TOKEN,
                    "tasks": tasks,
                    "max_tasks": MAX_TASKS,
                    "local_port": assigned_port,
                },
            }
            json_protocol.send_json(s, register_msg)
            logger.info(f"[节点] 已发送注册消息 {TCP_HOST}:{TCP_PORT}")

            return True
        except Exception as e:
            logger.error(f"[节点] 连接或注册失败: {e}")
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
            logger.error("[节点] 初始连接失败，程序退出")
            return

        # === 心跳线程 ===
        def heartbeat_loop():
            nonlocal last_heartbeat_send_time, connection_alive
            while connection_alive and s:
                time.sleep(HEARTBEAT_INTERVAL_SEC)
                try:
                    hb_msg = {
                        "type": "heartbeat",
                        "timestamp": int(time.time()),
                        "data": {
                            "node_id": NODE_ID,
                            "tasks": tasks,
                        },
                    }
                    json_protocol.send_json(s, hb_msg)
                    last_heartbeat_send_time = time.time()
                    logger.debug("[节点] 发送心跳")
                except Exception as e:
                    logger.error(f"[心跳线程] 发送心跳异常: {e}")
                    connection_alive = False
                    break

        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        # === 主接收循环 ====
        while connection_alive and s:
            # === 检查已完成的 LLM 任务（非阻塞） ===
            for tid in list(pending_llm_tasks.keys()):
                info = pending_llm_tasks[tid]
                elapsed = time.time() - info["start_time"]
                if "value" in info["store"] or elapsed >= LLM_TIMEOUT_SEC:
                    if "value" in info["store"]:
                        result = info["store"]["value"]
                    else:
                        logger.warning("[节点] LLM 任务 %s 等待超时 (%ds)", tid, LLM_TIMEOUT_SEC)
                        result = {"success": False, "label": "", "confidence": 0.0, "class_probs": [], "error": f"LLM inference timeout after {LLM_TIMEOUT_SEC} seconds"}
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
                        logger.info("[节点] 已返回 LLM 任务 %s 的推理结果", tid)
                    except Exception as send_err:
                        logger.error("[节点] 发送 LLM 任务结果失败: %s", send_err)
                    tasks.remove(tid)
                    del pending_llm_tasks[tid]

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
                            f"[节点] ⚠️ 心跳响应超时！({heartbeat_missed_count}/{HEARTBEAT_MISS_LIMIT}) "
                            f"上次发送: {time_since_last_send:.1f}s 前"
                        )
                    if heartbeat_missed_count >= HEARTBEAT_MISS_LIMIT:
                        logger.error(
                            f"[节点] ❗ 心跳连续丢失 {heartbeat_missed_count} 次，超过最大限制，准备断开并重连..."
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
                            f"[节点] recv_json 连续返回 None {consecutive_none_count} 次，判定连接异常，触发重连"
                        )
                        connection_alive = False
                        break
                    continue

                # 成功收到消息，重置连续 None 计数
                consecutive_none_count = 0

                msg_type = msg.get("type")
                msg_data = msg.get("data", {})
                logger.info(f"[节点] 收到消息类型: {msg_type}")

                # === 心跳响应处理 ====
                if msg_type == "heartbeat_ack":
                    logger.info(f"[节点] 收到心跳响应: {msg.get('message', '')}")
                    heartbeat_missed_count = 0  # 重置丢失计数
                    last_heartbeat_response_time = time.time()  # 记录响应时间
                    last_heartbeat_send_time = 0  # 重置发送时间，准备下一次发送

                # === 注册响应 ===
                elif msg_type == "register_ack":
                    status = msg.get("status")
                    message = msg.get("message")
                    logger.info(f"[注册结果] {status}: {message}")

                # === 任务状态响应 ===
                elif msg_type == "status_update_ack":
                    status = msg.get("status")
                    message = msg.get("message")
                    task_id = msg_data.get("task_id")
                    logger.info(f"[任务状态更新] 任务ID: {task_id}, 动作: {message}")

                # === 任务处理 ===
                elif msg_type == "task":
                    try:
                        task_id = msg_data.get("task_id")
                        image_filename = msg_data.get("image_filename")
                        image_size = msg_data.get("image_size")
                        image_data_b64 = msg_data.get("image_data")
                        timestamp = msg_data.get("timestamp")
                        # 识别方式类型：local / llm / auto，默认 local
                        recognition_type = msg_data.get("recognition_type", "local")

                        if not all([task_id, image_filename, image_data_b64]):
                            logger.warning("[节点] 任务数据不完整")
                            continue

                        logger.info(
                            f"[节点] 收到带图片任务: {task_id}, 文件名: {image_filename}, "
                            f"识别方式: {recognition_type}, "
                            f"大小: {image_size} 字节, 时间戳: {timestamp}"
                        )

                        # 更新当前任务列表和计数
                        tasks.append(task_id)

                        # 解码 base64 图片数据
                        try:

                            image_bytes = base64.b64decode(image_data_b64)

                            # 验证解码后的大小
                            if len(image_bytes) != image_size:
                                logger.warning(
                                    f"[节点] 图片大小不匹配: 期望={image_size}, 实际={len(image_bytes)}"
                                )

                            # 保存图片
                            os.makedirs(IMAGE_PATH, exist_ok=True)
                            local_image_path = os.path.join(IMAGE_PATH, image_filename)
                            with open(local_image_path, "wb") as f:
                                f.write(image_bytes)
                            logger.info(f"[节点] 图片已保存到: {local_image_path}")

                            # 根据 recognition_type 选择推理方式
                            # 优先使用节点配置的环境变量开关，兼容服务端指定类型
                            effective_type = recognition_type
                            if recognition_type == "auto":
                                effective_type = "llm" if LLM_RECOGNITION_ENABLED else "local"
                            elif recognition_type == "llm" and not LLM_RECOGNITION_ENABLED:
                                logger.warning(
                                    f"[节点] 任务要求 LLM 识别但节点未启用，回退到本地模型"
                                )
                                effective_type = "local"

                            logger.info(f"[节点] 推理方式: {effective_type}")
                            if effective_type == "llm":
                                store = {}
                                def _run_llm():
                                    try:
                                        store["value"] = predict_image_llm(local_image_path)
                                    except Exception as exc:
                                        logger.error("[节点] LLM inference failed: %s", exc, exc_info=True)
                                        store["value"] = {"success": False, "label": "", "confidence": 0.0, "class_probs": [], "error": f"LLM inference failed: {exc}"}

                                threading.Thread(target=_run_llm, daemon=True).start()
                                pending_llm_tasks[task_id] = {
                                    "store": store,
                                    "local_image_path": local_image_path,
                                    "effective_type": effective_type,
                                    "start_time": time.time(),
                                }
                                logger.info("[节点] LLM 任务 %s 已提交到后台，主循环继续监听", task_id)
                                # 不阻塞主循环，由 pending_llm_tasks 检查处理结果
                                continue
                            else:
                                result = predict_image(local_image_path)

                            # 在结果中标明识别方式
                            result["recognition_type"] = effective_type

                            # 返回结果
                            response_msg = {
                                "type": "task_result",
                                "timestamp": int(time.time()),
                                "data": {
                                    "node_id": NODE_ID,
                                    "task_id": task_id,
                                    "result": result,
                                    "processed_image_path": local_image_path,
                                },
                            }
                            json_protocol.send_json(s, response_msg)
                            logger.info(f"[节点] 已返回任务 {task_id} 的推理结果")
                            tasks.remove(task_id)

                        except Exception as decode_error:
                            logger.error(f"[节点] 图片数据解码失败: {decode_error}")
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
                            # json_protocol.send_json(s, status_update_decrement)
                            tasks.remove(task_id)

                    except Exception as e:
                        logger.error(f"[节点] 处理带图片任务出错: {e}")
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
                    logger.info(f"[节点] 服务端消息: {status} - {message}")

                else:
                    logger.warning(f"[节点] 未知消息类型: {msg_type}")

            except socket.timeout:
                # 接收超时是正常的，继续循环检查其他条件
                continue
            except Exception as e:
                logger.error(f"[节点] 主循环异常: {e}")
                connection_alive = False
                break

        # === 连接异常处理 ===
        logger.info("[节点] 连接异常，准备重连...")
        if s:
            try:
                _safe_close(s)
            except Exception:
                pass
            s = None

        # 增加重连延迟和最大尝试次数
        reconnect_attempts += 1
        if reconnect_attempts > 5:  # 最多尝试5次
            logger.error("[节点] 重连尝试次数过多，退出程序")
            return

        time.sleep(RECONNECT_DELAY_SEC)
        connection_alive = True  # 重置连接状态
        heartbeat_missed_count = 0
        last_heartbeat_send_time = 0
        last_heartbeat_response_time = 0
        consecutive_none_count = 0
        pending_llm_tasks.clear()  # 清空未完成的 LLM 任务

        # 外层 while True 会自动调用 connect_and_register() 重新连接
        # 无需在此处再次调用，避免重复连接


# # ======================
# # === 启动入口 ===
# # ======================
# if __name__ == '__main__':
#     start_node_service()
