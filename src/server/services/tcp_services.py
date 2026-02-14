# services/tcp_services.py

import socket
import threading
import logging
import json
import time
from datetime import datetime
import pymysql
from pymysql import Error
from config import *
import struct

# =============================================
# 0. 日志配置
# =============================================
logger = logging.getLogger("tcp_server_logger")
if TSAC_DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
logger.setLevel(log_level)

file_handler = logging.FileHandler(LOGS_PATH / "/tcp_server_logger.log")
console_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


# 节点管理器
class NodeManager:
    def __init__(self):
        self.nodes = {}  # node_id -> dict
        self.lock = threading.Lock()

    def register_node(self, node_id, addr, socket_obj=None, max_tasks=None):
        """注册节点，支持动态设置最大任务数"""
        with self.lock:
            # 如果没有指定max_tasks，使用默认值5
            if max_tasks is None:
                max_tasks = 5

            self.nodes[node_id] = {
                "addr": addr,
                "socket": socket_obj,
                "last_heartbeat": time.time(),
                "status": "idle",  # idle 或 busy
                "max_tasks": max_tasks,  # 最大任务处理数
                "current_tasks": 0,  # 当前任务计数
            }
            logger.info(
                f"[节点注册] 节点 {node_id} ({addr}) 已注册，状态：空闲，最大任务数：{max_tasks}"
            )
            return True

    def update_heartbeat(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["last_heartbeat"] = time.time()
                return True
            return False

    def set_node_busy(self, node_id):
        """设置节点为忙碌状态 - 只有当任务数达到最大值时才设为busy"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                # 只有当当前任务数 >= 最大任务数时才设为busy
                if node["current_tasks"] >= node["max_tasks"]:
                    node["status"] = "busy"
                    logger.debug(
                        f"[节点状态] 节点 {node_id} 任务数已满({node['current_tasks']}/{node['max_tasks']})，状态设为忙碌"
                    )
                return True
            return False

    def set_node_idle(self, node_id):
        """设置节点为空闲状态"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["status"] = "idle"
                return True
            return False

    def increment_task_count(self, node_id):
        """增加节点的任务计数，并在达到最大值时自动设为忙碌"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node["current_tasks"] += 1
                logger.debug(
                    f"[任务计数] 节点 {node_id} 任务数增加: {node['current_tasks']-1} -> {node['current_tasks']}/{node['max_tasks']}"
                )

                # 如果达到或超过最大任务数，自动设为忙碌
                if node["current_tasks"] >= node["max_tasks"]:
                    node["status"] = "busy"
                    logger.info(
                        f"[节点状态] 节点 {node_id} 任务数达到上限({node['current_tasks']}/{node['max_tasks']})，自动设为忙碌"
                    )

                return True
            return False

    def decrement_task_count(self, node_id):
        """减少节点的任务计数，并在低于最大值时自动设为空闲"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if node["current_tasks"] > 0:
                    node["current_tasks"] -= 1
                    logger.debug(
                        f"[任务计数] 节点 {node_id} 任务数减少: {node['current_tasks']+1} -> {node['current_tasks']}/{node['max_tasks']}"
                    )

                    # 如果从忙碌状态变为非满负荷，自动设为空闲
                    if (
                        node["status"] == "busy"
                        and node["current_tasks"] < node["max_tasks"]
                    ):
                        node["status"] = "idle"
                        logger.info(
                            f"[节点状态] 节点 {node_id} 任务数低于上限({node['current_tasks']}/{node['max_tasks']})，自动设为空闲"
                        )

                return True
            return False

    def get_node_current_tasks(self, node_id):
        """获取节点当前任务数量"""
        with self.lock:
            if node_id in self.nodes:
                return self.nodes[node_id]["current_tasks"]
        return 0

    def get_node_max_tasks(self, node_id):
        """获取节点最大任务处理能力"""
        with self.lock:
            if node_id in self.nodes:
                return self.nodes[node_id]["max_tasks"]
        return 0

    def get_node_load_info(self, node_id):
        """获取节点的负载信息"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                return {
                    "current_tasks": node["current_tasks"],
                    "max_tasks": node["max_tasks"],
                    "load_percentage": (
                        (node["current_tasks"] / node["max_tasks"]) * 100
                        if node["max_tasks"] > 0
                        else 0
                    ),
                    "status": node["status"],
                }
        return None

    def get_available_nodes(self):
        """获取所有可用的节点（有socket连接的节点）"""
        available_nodes = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if info.get("socket") is not None:
                    available_nodes.append(
                        {
                            "node_id": node_id,
                            "addr": f"{info['addr'][0]}:{info['addr'][1]}",
                            "status": info["status"],
                            "max_tasks": info["max_tasks"],
                            "current_tasks": info["current_tasks"],
                            "load_percentage": (
                                (info["current_tasks"] / info["max_tasks"]) * 100
                                if info["max_tasks"] > 0
                                else 0
                            ),
                        }
                    )
        return available_nodes

    def get_idle_node(self):
        with self.lock:
            for node_id, info in self.nodes.items():
                if info["status"] == "idle" and info.get("socket") is not None:
                    return node_id, info
        return None, None

    def get_idle_nodes(self):
        """获取空闲节点（有socket连接且任务数未满）"""
        idle_nodes = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if (
                    info.get("socket") is not None
                    and info["status"] == "idle"
                    and info["current_tasks"] < info["max_tasks"]
                ):
                    idle_nodes.append(
                        {
                            "node_id": node_id,
                            "addr": f"{info['addr'][0]}:{info['addr'][1]}",
                            "max_tasks": info["max_tasks"],
                            "current_tasks": info["current_tasks"],
                            "load_percentage": (
                                (info["current_tasks"] / info["max_tasks"]) * 100
                                if info["max_tasks"] > 0
                                else 0
                            ),
                        }
                    )
        return idle_nodes

    def get_node_socket(self, node_id):
        with self.lock:
            node = self.nodes.get(node_id)
            if node and node.get("socket"):
                return node["socket"]
        return None

    def cleanup_nodes(self, timeout=30):
        current_time = time.time()
        to_remove = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if current_time - info["last_heartbeat"] > timeout:
                    logger.info(f"[节点清理] 节点 {node_id} 超时未心跳，将被移除")
                    self.update_db_node_status(node_id, "offline")
                    to_remove.append(node_id)
            for node_id in to_remove:
                del self.nodes[node_id]

    def show_all_nodes(self):
        with self.lock:
            logger.debug("\n" + "=" * 80)
            logger.debug("[节点监控] 当前所有节点信息:")
            logger.debug("=" * 80)
            for node_id, info in self.nodes.items():
                addr = info.get("addr", ("Unknown", 0))
                ip, port = addr
                status = info.get("status", "N/A")
                last_hb = info.get("last_heartbeat", "N/A")
                max_tasks = info.get("max_tasks", "N/A")
                current_tasks = info.get("current_tasks", "N/A")

                ts_str = (
                    datetime.fromtimestamp(last_hb).strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(last_hb, (int, float))
                    else str(last_hb)
                )

                load_percent = (
                    (current_tasks / max_tasks * 100)
                    if max_tasks != "N/A" and max_tasks > 0
                    else 0
                )

                logger.debug(
                    f"     节点ID: {node_id} | 地址: {ip}:{port} | 状态: {status} | "
                    f"最大任务数: {max_tasks} | 当前任务: {current_tasks} | "
                    f"负载: {load_percent:.1f}% | 最后心跳: {ts_str}"
                )
            logger.debug("=" * 80 + "\n")

    def update_db_node_status(self, node_id, status):
        try:
            conn = get_db_connection()
            if not conn:
                logger.error(f"[数据库] 无法连接数据库，无法更新节点 {node_id} 状态")
                return False
            with conn.cursor() as cursor:
                sql = "UPDATE nodes SET status = %s, updated_at = NOW() WHERE id = %s"
                cursor.execute(sql, (status, node_id))
            conn.commit()
            logger.debug(f"[数据库] 节点 {node_id} 状态更新为 {status}")
            return True
        except Exception as e:
            logger.error(f"[数据库] 更新节点状态失败: {e}")
            return False
        finally:
            if "conn" in locals() and conn:
                conn.close()


# =============================================
# 3. 全局节点管理器
# =============================================
node_manager = NodeManager()


# =============================================
# 4. 数据库工具
# =============================================
def get_db_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB] 数据库连接失败: {e}")
        return None


# 工具函数：自定义消息头长度前缀协议
def send_json(sock, msg_dict, header="server"):
    """
    发送一条 JSON 消息到 socket，使用自定义消息头的长度前缀协议
    格式: <消息头>@<内容长度><JSON内容>

    Args:
        sock: socket对象
        msg_dict: 要发送的字典数据
        header: 消息头标识，默认为"server"
    """
    try:
        json_str = json.dumps(msg_dict)
        json_bytes = json_str.encode("utf-8")

        # 计算总长度（消息头 + @ + 数字长度 + 实际内容长度）
        content_length = len(json_bytes)
        header_str = f"{header}@{content_length}"
        header_bytes = header_str.encode("utf-8")

        # 组合发送：header + json_bytes
        full_message = header_bytes + json_bytes
        sock.sendall(full_message)

        logger.debug(
            f"[send_json] 发送成功: 头部='{header_str}', 内容长度={content_length}"
        )

    except Exception as e:
        logger.error(f"[send_json] 发送失败: {e}")
        raise


def recv_json(sock, expected_headers=["node"]):
    """
    从 socket 接收一条完整的 JSON 消息（自定义消息头长度前缀协议）
    格式: <消息头>@<内容长度><JSON内容>

    Args:
        sock: socket对象
        expected_headers: 期望的消息头列表，默认为["server"]
    """
    if expected_headers is None:
        expected_headers = ["server"]
    elif isinstance(expected_headers, str):
        expected_headers = [expected_headers]

    try:
        # 构建所有可能的标记
        expected_markers = [f"{header}@".encode("utf-8") for header in expected_headers]

        # 1. 先接收直到找到任意一个期望的标记
        buffer = b""
        marker_found = False
        found_marker = None
        found_header = None

        while not marker_found:
            chunk = sock.recv(1024)
            if not chunk:
                return None

            buffer += chunk

            # 查找所有期望的标记
            for marker in expected_markers:
                marker_pos = buffer.find(marker)
                if marker_pos != -1:
                    # 移除标记前的无效数据
                    buffer = buffer[marker_pos:]
                    marker_found = True
                    found_marker = marker
                    found_header = marker[:-1].decode("utf-8")  # 去掉@符号
                    break

            if (
                not marker_found
                and len(buffer) > max(len(marker) for marker in expected_markers) * 2
            ):
                # 如果没有找到任何期望标记，清空缓冲区重新开始
                logger.warning(
                    f"[recv_json] 未找到期望标记 {expected_headers}，清空缓冲区重新搜索"
                )
                buffer = b""

        if not marker_found:
            logger.error(f"[recv_json] 未找到任何期望标记: {expected_headers}")
            return None

        # 2. 提取长度数字部分
        length_start = len(found_marker)
        num_buffer = b""

        # 从标记后面开始读取数字
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
            logger.error(f"[recv_json] 无法解析长度数字，找到标记: '{found_header}@'")
            return None

        content_length = int(num_buffer.decode("utf-8"))
        content_start = length_start + len(num_buffer)

        logger.debug(
            f"[recv_json] 解析到内容长度: {content_length}, 起始位置: {content_start}, "
            f"找到标记: '{found_header}', 期望标记: {expected_headers}"
        )

        # 3. 提取完整的内容数据
        data = buffer[content_start:]

        # 如果缓冲区数据不足，继续接收
        while len(data) < content_length:
            remaining = content_length - len(data)
            part = sock.recv(min(remaining, 4096))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 4. 解码并解析 JSON
        text = data[:content_length].decode("utf-8")
        result = json.loads(text)

        # 可以添加来源信息
        result["_source_header"] = found_header
        return result

    except (
        ConnectionError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        struct.error,
    ) as e:
        logger.error(f"[recv_json] 接收 JSON 失败 (期望标记: {expected_headers}): {e}")
        return None


# =============================================
# 6. 任务分发（供外部调用，如 views.py）
# =============================================
def dispatch_task(image_path: str, image_data, task_id: str):
    """
    优先通过 TCP 将 image_file（图片二进制）发送给节点，
    同时保留将图片保存到 ./uploads/ 的逻辑（备用）
    """
    # === 可选：备份逻辑 ===
    # 如果您想把图片也保存到服务端的 ./uploads/，可以取消下面的注释

    import os

    uploads_dir = "./uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    backup_image_path = os.path.join(uploads_dir, os.path.basename(image_path))
    with open(backup_image_path, "wb") as f:
        if hasattr(image_data, "read"):  # 比如 request.files 的 FileStorage 对象
            f.write(image_data.read())
        else:  # 如果是二进制数据，比如 bytes
            f.write(image_data)
    logger.info(f"[服务端] 图片已备份到本地: {backup_image_path}")

    # === 优先：通过 TCP 传输图片给节点 ===
    node_id, node_info = node_manager.get_idle_node()
    if not node_id:
        return {"status": "waiting", "task_id": task_id, "message": "没有空闲节点"}

    socket_obj = node_info.get("socket")
    if not socket_obj:
        node_manager.set_node_idle(node_id)
        return {"status": "failed", "task_id": task_id, "error": "节点未连接"}

    try:
        # 1. 构造任务消息头部（JSON）
        image_filename = os.path.basename(
            image_path
        )  # 如 '6a67fa40-de07-41d6-a21f-2a8479d7747e.jpg'

        task_msg = {
            "type": "task",
            "task_id": task_id,
            "has_image": True,
            "image_filename": image_filename,  # 告诉节点图片保存时的文件名
            "image_size": len(image_data),
        }

        # 2. 发送任务消息 JSON
        send_json(socket_obj, task_msg)
        # socket_obj.sendall(json.dumps(task_msg).encode('utf-8'))

        # 3. 发送图片二进制数据
        socket_obj.sendall(image_data)

        # 4. 标记节点为忙碌
        node_manager.set_node_busy(node_id)

        return {"status": "dispatched", "task_id": task_id, "node_id": node_id}

    except Exception as e:
        node_manager.set_node_idle(node_id)
        return {"status": "failed", "task_id": task_id, "error": str(e)}

    """
    【已废弃】现在任务由用户直接连接节点发送，此方法仅作备用
    保留基本功能用于兼容现有代码
    """
    logger.warning("[任务分发] dispatch_task 方法已废弃，任务现在由用户直接发送到节点")

    # 简单的备用逻辑：随机选择一个可用节点
    available_nodes = node_manager.get_available_nodes()
    if not available_nodes:
        return {"status": "waiting", "task_id": task_id, "message": "没有可用节点"}

    # 这里只是示例，实际使用中可能不需要这个功能
    return {"status": "deprecated", "message": "请直接使用节点API"}


# =============================================
# 7. TCP 服务端核心逻辑
# =============================================
def handle_client(conn, addr):
    print(f"[TCP] 新连接来自: {addr}")
    node_id = None

    try:
        while True:
            msg = recv_json(
                conn
            )  # ✅ 使用安全的 recv_json()，替代 conn.recv + json.loads
            if msg is None:
                break  # 客户端断开或数据错误

            msg_type = msg.get("type")

            if msg_type == "register":
                node_id = msg.get("node_id")
                token = msg.get("token")
                max_tasks = msg.get("max_tasks", 5)  # 获取节点上报的最大任务数，默认为5

                if not node_id or not token:
                    register_ack = {
                        "type": "register_ack",
                        "status": "error",
                        "message": "node_id 和 token 必须提供",
                    }
                    send_json(conn, register_ack)
                    continue

                conn_db = get_db_connection()
                if not conn_db:
                    register_ack = {
                        "type": "register_ack",
                        "status": "error",
                        "message": "数据库错误",
                    }
                    send_json(conn, register_ack)
                    continue

                try:
                    cursor = conn_db.cursor(pymysql.cursors.DictCursor)
                    query = """
                        SELECT * FROM nodes 
                        WHERE id = %s AND token = %s AND is_active = 1
                    """
                    cursor.execute(query, (node_id, token))
                    result = cursor.fetchone()

                    if result:
                        # 使用节点上报的max_tasks注册节点
                        node_manager.register_node(node_id, addr, conn, max_tasks)
                        node_manager.update_db_node_status(node_id, "online")
                        node_manager.set_node_idle(node_id)

                        register_ack = {
                            "type": "register_ack",
                            "status": "success",
                            "message": f"节点注册成功，最大任务数: {max_tasks}",
                            "max_tasks": max_tasks,  # 在响应中也返回max_tasks
                        }
                        send_json(conn, register_ack)
                        print(
                            f"[注册成功] node_id={node_id}, addr={addr}, max_tasks={max_tasks}"
                        )
                    else:
                        register_ack = {
                            "type": "register_ack",
                            "status": "error",
                            "message": "节点未激活或凭证无效",
                        }
                        send_json(conn, register_ack)
                finally:
                    if conn_db:
                        cursor.close()
                        conn_db.close()

            elif msg_type == "heartbeat":
                if node_id:
                    node_manager.update_heartbeat(node_id)
                    heartbeat_ack = {
                        "type": "heartbeat_ack",
                        "status": "success",
                        "message": "心跳已更新",
                    }
                    send_json(conn, heartbeat_ack)
                else:
                    heartbeat_ack = {
                        "type": "heartbeat_ack",
                        "status": "error",
                        "message": "未注册的节点",
                    }
                    send_json(conn, heartbeat_ack)

            elif msg_type == "task_status_update":
                # 新增：处理节点主动上报的任务状态变化
                if not node_id:
                    status_update = {
                        "type": "status_update_ack",
                        "status": "error",
                        "message": "未注册的节点",
                    }
                    send_json(conn, status_update)
                    continue

                action = msg.get("action")  # "increment" 或 "decrement"
                task_id = msg.get("task_id")

                if action == "increment":
                    node_manager.increment_task_count(node_id)
                    status_update = {
                        "type": "status_update_ack",
                        "task_id": task_id,
                        "status": "success",
                        "message": "任务计数增加成功",
                        "current_tasks": node_manager.get_node_current_tasks(node_id),
                        "max_tasks": node_manager.get_node_max_tasks(node_id),
                    }
                elif action == "decrement":
                    node_manager.decrement_task_count(node_id)
                    status_update = {
                        "type": "status_update_ack",
                        "task_id": task_id,
                        "status": "success",
                        "message": "任务计数减少成功",
                        "current_tasks": node_manager.get_node_current_tasks(node_id),
                        "max_tasks": node_manager.get_node_max_tasks(node_id),
                    }
                else:
                    status_update = {
                        "type": "status_update_ack",
                        "status": "error",
                        "message": "无效的操作类型",
                    }

                send_json(conn, status_update)

            elif msg_type == "task_result":
                # 保留原有的任务结果处理逻辑，但现在主要由节点直接处理
                node_id = msg.get("node_id")
                task_id = msg.get("task_id")
                result = msg.get("result")

                print(f"[TCP服务端] 收到任务结果: task_id={task_id}, result={result}")

                try:
                    mysql_conn = get_db_connection()
                    with mysql_conn.cursor() as cursor:
                        sql = """
                        INSERT INTO task_results (task_id, result, status)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            result = VALUES(result),
                            status = VALUES(status),
                            updated_at = CURRENT_TIMESTAMP
                        """
                        cursor.execute(sql, (task_id, json.dumps(result), "completed"))
                    mysql_conn.commit()
                    print(f"[MySQL] 任务结果已保存: task_id={task_id}")

                    # 任务完成后，减少任务计数
                    if node_id:
                        node_manager.decrement_task_count(node_id)

                except Exception as e:
                    print(f"[MySQL] 保存任务结果失败: {e}")
                finally:
                    if mysql_conn:
                        mysql_conn.close()

            else:
                conn.sendall(
                    json.dumps(
                        {"type": "msg", "status": "error", "message": "未知消息类型"}
                    ).encode("utf-8")
                )

    except ConnectionResetError:
        print(f"[连接断开] {addr}")
    finally:
        if node_id:
            with node_manager.lock:
                if node_id in node_manager.nodes:
                    # 立即更新状态为离线并同步到数据库
                    node_manager.nodes[node_id]["status"] = "offline"
                    node_manager.update_db_node_status(node_id, "offline")
                    logger.info(
                        f"[节点下行检测] 节点 {node_id} 连接异常断开，立即标记为离线"
                    )

                    # 从内存中移除节点
                    del node_manager.nodes[node_id]
                    logger.info(f"[节点清理] 节点 {node_id} 已从内存中移除")

        try:
            conn.close()
        except:
            pass
        logging.info(f"[TCP] 连接关闭: {addr}")


# =============================================
# 8. 启动 TCP 服务
# =============================================
def start_tcp_server(host="0.0.0.0", port=TCP_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"[TCP] 服务启动，监听 {host}:{port}")

        def cleanup_loop():
            while True:
                time.sleep(30)
                node_manager.cleanup_nodes()

        threading.Thread(target=cleanup_loop, daemon=True).start()

        def monitor_nodes():
            monitor_counter = 0
            while True:
                time.sleep(5)
                monitor_counter += 1
                logger.debug(f"[MONITOR] 第 {monitor_counter} 次节点监控")
                node_manager.show_all_nodes()

        threading.Thread(target=monitor_nodes, daemon=True).start()

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()


# =============================================
# 9. 启动入口（测试用，可直接注释）
# =============================================
# if __name__ == '__main__':
#     start_tcp_server()
