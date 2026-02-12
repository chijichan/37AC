from config import (
    DATASET_DIR,
    MODEL_SAVE_PATH,
    CLASSES_TXT_PATH,
    NUM_EPOCHS,
    BATCH_SIZE,
    IMAGE_SIZE,
    LEARNING_RATE,
    MODEL_LOAD_PATH,
    TCP_HOST,
    TCP_PORT,
    NODE_ID,
    TOKEN,
    HEARTBEAT_INTERVAL_SEC,  # 心跳发送间隔（与线程一致）
    HEARTBEAT_RESPONSE_TIMEOUT_SEC,  # 超过该时间未收到 heartbeat_ack 则认为超时
    HEARTBEAT_MISS_LIMIT,  # 允许连续丢失 heartbeat_ack 的最大次数
    RECONNECT_DELAY_SEC,  # 重连前等待时间（秒）
)
import socket
import threading
import json
import time
import os
from prediction.predictor import predict_image
import struct


# =============================================
# 5. 工具函数：JSON 长度前缀协议
# =============================================
def send_json(sock, msg_dict):
    """
    发送一条 JSON 消息到 socket，使用长度前缀协议
    """
    try:
        json_str = json.dumps(msg_dict)
        json_bytes = json_str.encode("utf-8")
        length_prefix = struct.pack(">I", len(json_bytes))  # 大端序 uint32，4 字节
        sock.sendall(length_prefix + json_bytes)
    except Exception as e:
        print(f"[send_json] 发送失败: {e}")
        raise


def recv_json(sock):
    """
    从 socket 接收一条完整的 JSON 消息（长度前缀协议）
    返回解析后的字典，如果失败或连接断开，返回 None
    """
    try:
        # 1. 接收 4 字节，表示 body 长度
        raw_len = sock.recv(4)
        if not raw_len:
            return None

        length = struct.unpack(">I", raw_len)[0]

        # 2. 按长度接收完整 body
        data = b""
        while len(data) < length:
            part = sock.recv(length - len(data))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 3. 解码并解析
        text = data.decode("utf-8")
        return json.loads(text)

    except (
        ConnectionError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        struct.error,
    ) as e:
        print(f"[recv_json] 接收 JSON 失败: {e}")
        return None


# ======================
# === TCP 客户端主逻辑 ===
# ======================
def start_node_service():
    # ===========================
    # === 配置参数 ===
    # ===========================
    TCP_HOST = "154.9.253.170"  # 请根据实际情况设置或从环境变量获取
    TCP_PORT = 13137  # 请根据实际情况设置或从环境变量获取
    NODE_ID = 1  # 请根据实际情况设置
    TOKEN = "a1ce075a-1ddb-430f-912c-747cc90d28fb"  # 请根据实际情况设置

    # ===========================
    # === 心跳超时与重连控制参数 ===
    # ===========================
    HEARTBEAT_INTERVAL_SEC = 10  # 心跳发送间隔（与线程一致）
    HEARTBEAT_RESPONSE_TIMEOUT_SEC = 30  # 超过该时间未收到 heartbeat_ack 则认为超时
    HEARTBEAT_MISS_LIMIT = 3  # 允许连续丢失 heartbeat_ack 的最大次数
    RECONNECT_DELAY_SEC = 10  # 重连前等待时间（秒）

    # ===========================
    # === 全局变量（在函数内使用）===
    # ===========================
    s = None
    heartbeat_missed_count = 0
    last_heartbeat_time = 0  # 上一次成功发送心跳的时间戳
    # last_heartbeat_sent_success = False

    # ===========================
    # === 连接并注册函数（辅助函数）===
    # ===========================
    def connect_and_register():
        nonlocal s
        try:
            print("[节点] 尝试连接服务器...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TCP_HOST, TCP_PORT))
            print(f"[节点] 已连接到服务器 {TCP_HOST}:{TCP_PORT}")

            # ==== 1. 注册节点 ====
            register_msg = {"type": "register", "node_id": NODE_ID, "token": TOKEN}
            send_json(s, register_msg)
            print(f"[节点] 已发送注册消息")

            # 重置心跳状态
            nonlocal heartbeat_missed_count, last_heartbeat_time
            heartbeat_missed_count = 0
            last_heartbeat_time = 0

            return True
        except Exception as e:
            print(f"[节点] 连接或注册失败: {e}")
            if s:
                s.close()
                s = None
            return False

    # ===========================
    # === 启动连接 ===
    # ===========================
    if not connect_and_register():
        print("[节点] 初始连接失败，程序退出")
        return

    # ===========================
    # === 心跳线程 ====
    # ===========================
    def heartbeat_loop():
        nonlocal last_heartbeat_time
        while True:
            time.sleep(HEARTBEAT_INTERVAL_SEC)
            try:
                hb_msg = {"type": "heartbeat"}
                send_json(s, hb_msg)
                print("[节点] 发送心跳")
                last_heartbeat_time = time.time()  # 记录发送时间
            except Exception as e:
                print(f"[心跳线程] 发送心跳异常，可能连接已断开: {e}")
                break  # 退出心跳线程

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    # ===========================
    # === 主接收循环 ====
    # ===========================
    while True:
        # ======================
        # === 心跳超时检测 ===
        # ======================
        current_time = time.time()
        if last_heartbeat_time > 0:
            time_since_last_heartbeat = current_time - last_heartbeat_time
            if time_since_last_heartbeat > HEARTBEAT_RESPONSE_TIMEOUT_SEC:
                if heartbeat_missed_count < HEARTBEAT_MISS_LIMIT:
                    heartbeat_missed_count += 1
                    print(
                        f"[节点] ⚠️ 心跳响应超时！({heartbeat_missed_count}/{HEARTBEAT_MISS_LIMIT}) 未收到 heartbeat_ack"
                    )
                if heartbeat_missed_count >= HEARTBEAT_MISS_LIMIT:
                    print(
                        f"[节点] ❗ 心跳连续丢失 {heartbeat_missed_count} 次，超过最大限制，准备断开并重连..."
                    )
                    break  # 跳出主循环，触发重连逻辑

        # ======================
        # === 接收服务端消息 ===
        # ======================
        try:
            msg = recv_json(s)
            if msg is None:
                print("[节点] 服务端连接中断或 JSON 解析失败")
                break

            msg_type = msg.get("type")
            print(f"[节点] 收到消息类型: {msg_type}")

            # =========================
            # === 心跳响应处理 ====
            # =========================
            if msg_type == "heartbeat_ack":
                print(f"[节点] 收到心跳响应: {msg.get('message', '')}")
                heartbeat_missed_count = 0  # 重置丢失计数
                last_heartbeat_time = 0  # 清空，表示已收到响应

            # =========================
            # === 注册响应 ===
            # =========================
            elif msg_type == "register_ack":
                status = msg.get("status")
                message = msg.get("message")
                print(f"[注册结果] {status}: {message}")

            # =========================
            # === 任务处理 ===
            # =========================
            elif msg_type == "task":
                try:
                    task_id = msg.get("task_id")
                    has_image = msg.get("has_image", False)
                    image_filename = msg.get("image_filename")
                    image_size = msg.get("image_size")

                    print(
                        f"[节点] 收到任务: {task_id}, 是否包含图片: {has_image}, 图片文件名: {image_filename}, 图片大小: {image_size} 字节"
                    )

                    if not task_id:
                        print("[节点] 任务ID缺失")
                        continue

                    if not has_image:
                        response_msg = {
                            "type": "task_result",
                            "node_id": NODE_ID,
                            "task_id": task_id,
                            "result": None,
                        }
                        send_json(s, response_msg)
                        continue

                    if not image_filename or image_size is None:
                        error_msg = {
                            "type": "task_result",
                            "task_id": task_id,
                            "result": None,
                            "error": "服务端未提供图片文件名或图片大小",
                        }
                        send_json(s, error_msg)
                        continue

                    # 接收图片二进制
                    print(f"[节点] 开始接收图片数据，大小: {image_size} 字节")
                    image_data = b""
                    received = 0
                    while received < image_size:
                        part = s.recv(min(4096, image_size - received))
                        if not part:
                            raise ConnectionError("连接中断，未能接收完整图片")
                        image_data += part
                        received += len(part)

                    print(f"[节点] 图片数据接收完成，共 {len(image_data)} 字节")

                    # 保存图片
                    os.makedirs("uploads", exist_ok=True)
                    local_image_path = os.path.join("uploads", image_filename)
                    with open(local_image_path, "wb") as f:
                        f.write(image_data)
                    print(f"[节点] 图片已保存到: {local_image_path}")

                    # 推理
                    result = predict_image(local_image_path)

                    # 返回结果
                    response_msg = {
                        "type": "task_result",
                        "node_id": NODE_ID,
                        "task_id": task_id,
                        "result": result,
                    }
                    send_json(s, response_msg)
                    print(f"[节点] 已返回任务 {task_id} 的推理结果")

                except Exception as e:
                    error_msg = {
                        "type": "task_result",
                        "task_id": "unknown",
                        "result": None,
                        "error": f"处理任务出错: {e}",
                    }
                    send_json(s, error_msg)
                    print(f"[节点] 处理任务出错: {e}")

            # =========================
            # === 其它消息 ===
            # =========================
            elif msg_type in ["msg", "error"]:
                status = msg.get("status")
                message = msg.get("message")
                print(f"[节点] 服务端消息: {status} - {message}")

            else:
                print(f"[节点] 未知消息类型: {msg_type}")

        except Exception as e:
            print(f"[节点] 主循环异常: {e}")
            break

    # ===========================
    # === 连接异常或心跳超时，断开并尝试重连 ===
    # ===========================
    print("[节点] 当前连接异常或心跳超时，尝试重新连接...")
    if s:
        s.close()
    time.sleep(RECONNECT_DELAY_SEC)

    while True:
        try:
            print("[节点] 尝试重新连接服务器...")
            if connect_and_register():
                print("[节点] 重连成功，继续运行...")
                break  # 重连并注册成功，重新进入主循环
            else:
                print(f"[节点] 重连失败，{RECONNECT_DELAY_SEC} 秒后重试...")
                time.sleep(RECONNECT_DELAY_SEC)
        except Exception as e:
            print(f"[节点] 重连异常: {e}，{RECONNECT_DELAY_SEC} 秒后重试...")
            time.sleep(RECONNECT_DELAY_SEC)


# # ======================
# # === 启动入口 ===
# # ======================
# if __name__ == '__main__':
#     start_node_service()
