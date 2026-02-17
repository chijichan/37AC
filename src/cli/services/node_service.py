# services/node_service.py

import socket
import threading
import json
import time
import os
import struct
import logging
from prediction.predictor import predict_image
from config import (
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
)

logger = logging.getLogger("node_service")


class JsonProtocol:
    """JSON 消息发送和接收类，使用自定义消息头长度前缀协议"""

    def __init__(self):
        self.send_header = "node"
        self.expected_headers = ["server", "user"]  # 在初始化时设置默认值

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

    def _find_message_marker(self, sock):
        """查找消息标记"""
        expected_markers = [
            f"{header}@".encode("utf-8") for header in self.expected_headers
        ]
        buffer = b""
        max_marker_len = max(len(marker) for marker in expected_markers)

        while True:
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
                logger.warning(
                    f"[recv_json] 未找到期望标记 {self.expected_headers}，清空缓冲区重新搜索"
                )
                buffer = b""

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
        """接收完整内容"""
        data = buffer[content_start:]

        while len(data) < content_length:
            remaining = content_length - len(data)
            part = sock.recv(min(remaining, 4096))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        return data[:content_length]

    def _decode_json(self, data, found_header):
        """解码JSON并添加来源信息"""
        text = data.decode("utf-8")
        result = json.loads(text)
        result["_source_header"] = found_header
        return result


# 全局 JSON 协议实例
json_protocol = JsonProtocol()


# === TCP 客户端主逻辑 ===
def start_node_service():
    # ===========================
    # === 配置参数 ===
    # ===========================
    # TCP_HOST = "154.9.253.170"  # 请根据实际情况设置或从环境变量获取
    # TCP_PORT = 13137  # 请根据实际情况设置或从环境变量获取
    # NODE_ID = 1  # 请根据实际情况设置
    # TOKEN = "a1ce075a-1ddb-430f-912c-747cc90d28fb"  # 请根据实际情况设置

    # # ===========================
    # # === 心跳超时与重连控制参数 ===
    # # ===========================
    # HEARTBEAT_INTERVAL_SEC = 10  # 心跳发送间隔（与线程一致）
    # HEARTBEAT_RESPONSE_TIMEOUT_SEC = 30  # 超过该时间未收到 heartbeat_ack 则认为超时
    # HEARTBEAT_MISS_LIMIT = 3  # 允许连续丢失 heartbeat_ack 的最大次数
    # RECONNECT_DELAY_SEC = 10  # 重连前等待时间（秒）
    # to config.py

    # === 全局变量（在函数内使用）===
    s = None
    heartbeat_missed_count = 0
    last_heartbeat_send_time = 0  # 重命名为发送时间
    last_heartbeat_response_time = 0  # 响应时间
    connection_alive = True  # 连接状态标志
    reconnect_attempts = 0
    current_tasks = 0
    tasks = []

    # === 连接并注册函数（辅助函数）===
    def connect_and_register():
        nonlocal s, reconnect_attempts
        try:
            logger.info("[节点] 尝试连接服务器...")

            # 修改1：确保关闭之前的socket
            if s:
                try:
                    s.close()
                except:
                    pass
                s = None

            # 修改2：创建新socket并（可选）绑定到本地端口
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许地址重用

            # 如果配置了 LOCAL_PORT（非 0/None），则尝试绑定到该端口；否则绑定到端口 0（由系统分配随机可用端口）
            try:
                if LOCAL_PORT:
                    s.bind(("", LOCAL_PORT))
                    logger.info(f"[节点] 已绑定本地端口: {LOCAL_PORT}")
                else:
                    s.bind(("", 0))
                    assigned_port = s.getsockname()[1]
                    logger.info(
                        f"[节点] 未配置 LOCAL_PORT，使用随机本地端口: {assigned_port}"
                    )
            except Exception as bind_err:
                logger.warning(f"[节点] 本地端口绑定失败: {bind_err}（继续尝试连接）")

            s.connect((TCP_HOST, TCP_PORT))
            logger.info(f"[节点] 已连接到服务器 {TCP_HOST}:{TCP_PORT}")

            # 重置状态
            nonlocal heartbeat_missed_count, last_heartbeat_send_time, last_heartbeat_response_time
            heartbeat_missed_count = 0
            last_heartbeat_send_time = 0
            last_heartbeat_response_time = 0
            reconnect_attempts = 0

            # 注册节点
            register_msg = {
                "type": "register",
                "node_id": NODE_ID,
                "token": TOKEN,
                "tasks": tasks,
                "max_tasks": MAX_TASKS,
                "current_tasks": current_tasks,
            }
            json_protocol.send_json(s, register_msg)
            logger.info(f"[节点] 已发送注册消息 {TCP_HOST}:{TCP_PORT}")

            return True
        except Exception as e:
            logger.error(f"[节点] 连接或注册失败: {e}")
            if s:
                try:
                    s.close()
                except:
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
                        "node_id": NODE_ID,
                        "tasks": tasks,
                        "current_tasks": current_tasks,
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
                    # 检查是否因为超时导致的None，如果是则继续循环
                    continue

                msg_type = msg.get("type")
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
                    task_id = msg.get("task_id")
                    logger.info(f"[任务状态更新] 任务ID: {task_id}, 动作: {message}")

                # === 任务处理 ===
                elif msg_type == "task":
                    try:
                        task_id = msg.get("task_id")
                        image_filename = msg.get("image_filename")
                        image_size = msg.get("image_size")
                        image_data_b64 = msg.get("image_data")
                        timestamp = msg.get("timestamp")

                        if not all([task_id, image_filename, image_data_b64]):
                            logger.warning("[节点] 任务数据不完整")
                            continue

                        logger.info(
                            f"[节点] 收到带图片任务: {task_id}, 文件名: {image_filename}, "
                            f"大小: {image_size} 字节, 时间戳: {timestamp}"
                        )

                        # 更新当前任务列表和计数
                        tasks.append(task_id)
                        current_tasks += 1

                        # 节点开始处理任务时
                        status_update_increment = {
                            "type": "task_status_update",
                            "action": "increment",
                            "task_id": task_id,
                        }
                        status_update_decrement = {
                            "type": "task_status_update",
                            "action": "decrement",
                            "task_id": task_id,
                        }
                        json_protocol.send_json(s, status_update_increment)

                        # 解码 base64 图片数据
                        try:
                            import base64

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

                            # 推理
                            result = predict_image(local_image_path)

                            # 返回结果
                            response_msg = {
                                "type": "task_result",
                                "node_id": NODE_ID,
                                "task_id": task_id,
                                "result": result,
                                "processed_image_path": local_image_path,
                            }
                            json_protocol.send_json(s, response_msg)
                            logger.info(f"[节点] 已返回任务 {task_id} 的推理结果")
                            tasks.remove(task_id)
                            current_tasks -= 1

                        except Exception as decode_error:
                            logger.error(f"[节点] 图片数据解码失败: {decode_error}")
                            error_msg = {
                                "type": "task_result",
                                "node_id": NODE_ID,
                                "task_id": task_id,
                                "result": None,
                                "error": f"图片数据解码失败: {decode_error}",
                            }
                            json_protocol.send_json(s, error_msg)
                            json_protocol.send_json(s, status_update_decrement)
                            tasks.remove(task_id)
                            current_tasks -= 1

                        # 节点完成任务
                        json_protocol.send_json(s, status_update_decrement)

                    except Exception as e:
                        logger.error(f"[节点] 处理带图片任务出错: {e}")
                        error_msg = {
                            "type": "task_result",
                            "node_id": NODE_ID,
                            "task_id": "unknown",
                            "result": None,
                            "error": f"处理任务出错: {e}",
                        }
                        json_protocol.send_json(s, error_msg)

                        # 节点完成任务
                        json_protocol.send_json(s, status_update_decrement)

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
                s.close()
            except:
                pass
            s = None

        # 修改5：增加重连延迟和最大尝试次数
        reconnect_attempts += 1
        if reconnect_attempts > 5:  # 最多尝试5次
            logger.error("[节点] 重连尝试次数过多，退出程序")
            return

        time.sleep(RECONNECT_DELAY_SEC)
        connection_alive = True  # 重置连接状态
        heartbeat_missed_count = 0
        last_heartbeat_send_time = 0
        last_heartbeat_response_time = 0

        # === 连接异常或心跳超时，断开并尝试重连 ===
        logger.info("[节点] 当前连接异常或心跳超时，尝试重新连接...")
        if s:
            try:
                s.close()
            except:
                pass
        s = None

        while True:
            try:
                logger.info("[节点] 尝试重新连接服务器...")
                if connect_and_register():
                    logger.info("[节点] 重连成功，继续运行...")
                    # 递归调用自己来重启服务
                    start_node_service()
                    break  # 如果递归返回，说明服务结束
                else:
                    logger.warning(
                        f"[节点] 重连失败，{RECONNECT_DELAY_SEC} 秒后重试..."
                    )
                    time.sleep(RECONNECT_DELAY_SEC)
            except Exception as e:
                logger.error(f"[节点] 重连异常: {e}，{RECONNECT_DELAY_SEC} 秒后重试...")
                time.sleep(RECONNECT_DELAY_SEC)


# # ======================
# # === 启动入口 ===
# # ======================
# if __name__ == '__main__':
#     start_node_service()
