# services/listen_service.py

import os
import socket
import threading
import json
import time
from datetime import datetime
import pymysql
from pymysql import Error
from config.base import DB_CONFIG, TCP_PORT
import struct
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from config.log_config import get_logger

# =============================================
# 日志配置 - 使用统一日志系统
# =============================================
logger = get_logger("listen_service")


# 异步处理器
class AsyncTaskProcessor:
    """异步任务处理器"""

    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = Queue()
        self.result_queue = Queue()

        # 启动后台处理线程
        self.start_background_processor()

    def start_background_processor(self):
        """启动后台任务处理器"""

        def process_tasks():
            while True:
                try:
                    task_func, args, kwargs = self.task_queue.get(timeout=1)
                    future = self.executor.submit(task_func, *args, **kwargs)
                    self.result_queue.put(future)
                except:
                    continue

        processor_thread = threading.Thread(target=process_tasks, daemon=True)
        processor_thread.start()

    def submit_task(self, func, *args, **kwargs):
        """提交任务到异步处理器"""
        self.task_queue.put((func, args, kwargs))
        return True


class MessageTypeProcessor:
    """按消息类型分类的异步处理器"""

    def __init__(self):
        # 为每个消息类型创建独立的线程池
        self.processors = {
            "register": ThreadPoolExecutor(max_workers=3),
            "heartbeat": ThreadPoolExecutor(max_workers=15),
            "task_result": ThreadPoolExecutor(max_workers=5),
            "default": ThreadPoolExecutor(max_workers=3),
        }

        # 消息队列用于处理特定类型的消息
        self.message_queues = {
            "register": Queue(),
            "heartbeat": Queue(),
            "task_result": Queue(),
            "default": Queue(),
        }

        # 启动各消息类型的处理循环
        self._start_message_processors()

    def _start_message_processors(self):
        """启动各消息类型的后台处理循环"""
        for msg_type in self.message_queues.keys():
            self._start_single_message_processor(msg_type)

    def _start_single_message_processor(self, msg_type):
        """启动单个消息类型的处理循环"""

        def message_processor():
            queue = self.message_queues[msg_type]
            processor = self.processors[msg_type]

            while True:
                try:
                    task_func, args, kwargs = queue.get(timeout=1)
                    processor.submit(task_func, *args, **kwargs)
                except:
                    continue

        thread = threading.Thread(target=message_processor, daemon=True)
        thread.start()

    def submit_message_task(self, msg_type, func, *args, **kwargs):
        """提交消息处理任务"""
        if msg_type in self.message_queues:
            self.message_queues[msg_type].put((func, args, kwargs))
        else:
            self.message_queues["default"].put((func, args, kwargs))


# 初始化异步处理器
async_processor = AsyncTaskProcessor(max_workers=10)
message_processor = MessageTypeProcessor()


# 节点管理器
class NodeManager:
    def __init__(self):
        self.nodes = {}  # node_id -> dict
        self.lock = threading.Lock()
        self._logger = get_logger("NodeManager")

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
            self._logger.info(
                "节点 %s (%s) 已注册，状态：空闲，最大任务数：%s",
                node_id, f"{addr[0]}:{addr[1]}" if isinstance(addr, tuple) else str(addr), max_tasks
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
                    self._logger.debug(
                        "节点 %s 任务数已满(%s/%s)，状态设为忙碌",
                        node_id, node["current_tasks"], node["max_tasks"]
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
                old_count = node["current_tasks"]
                node["current_tasks"] += 1
                self._logger.debug(
                    "节点 %s 任务数增加: %s -> %s/%s",
                    node_id, old_count, node["current_tasks"], node["max_tasks"]
                )

                # 如果达到或超过最大任务数，自动设为忙碌
                if node["current_tasks"] >= node["max_tasks"]:
                    node["status"] = "busy"
                    self._logger.info(
                        "节点 %s 任务数达到上限(%s/%s)，自动设为忙碌",
                        node_id, node["current_tasks"], node["max_tasks"]
                    )

                return True
            return False

    def decrement_task_count(self, node_id):
        """减少节点的任务计数，并在低于最大值时自动设为空闲"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if node["current_tasks"] > 0:
                    old_count = node["current_tasks"]
                    node["current_tasks"] -= 1
                    self._logger.debug(
                        "节点 %s 任务数减少: %s -> %s/%s",
                        node_id, old_count, node["current_tasks"], node["max_tasks"]
                    )

                    # 如果从忙碌状态变为非满负荷，自动设为空闲
                    if node["status"] == "busy" and node["current_tasks"] < node["max_tasks"]:
                        node["status"] = "idle"
                        self._logger.info(
                            "节点 %s 任务数低于上限(%s/%s)，自动设为空闲",
                            node_id, node["current_tasks"], node["max_tasks"]
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
                    self._logger.info("节点 %s 超时未心跳，将被移除", node_id)
                    self.update_db_node_status(node_id, "offline")
                    to_remove.append(node_id)
            for node_id in to_remove:
                del self.nodes[node_id]

    def show_all_nodes(self):
        with self.lock:
            self._logger.debug("当前所有节点信息:")
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

                self._logger.debug(
                    "节点ID: %-20s | 地址: %s:%s | 状态: %s | 任务: %s/%s | 负载: %.1f%% | 心跳: %s",
                    node_id, ip, port, status, current_tasks, max_tasks, load_percent, ts_str
                )

    def update_db_node_status(self, node_id, status, addr=None):
        try:
            conn = get_db_connection()
            if not conn:
                self._logger.error("无法连接数据库，无法更新节点 %s 状态", node_id)
                return False
            with conn.cursor() as cursor:
                sql = "UPDATE nodes SET status = %s, updated_at = NOW()"
                params = [status]
                if addr is not None:
                    sql += ", addr = %s"
                    if isinstance(addr, tuple):
                        params.append(f"{addr[0]}:{addr[1]}")
                    else:
                        params.append(str(addr))
                sql += " WHERE id = %s"
                params.append(node_id)
                cursor.execute(sql, tuple(params))
            conn.commit()
            self._logger.debug("节点 %s 状态更新为 %s", node_id, status)
            return True
        except Exception as e:
            self._logger.error("更新节点状态失败: %s", e)
            return False
        finally:
            if "conn" in locals() and conn:
                conn.close()


# 全局节点管理器
node_manager = NodeManager()


class TaskManager:
    def __init__(self):
        self.pending_tasks = {}
        self.lock = threading.Lock()
        self.check_interval = 2
        self.max_retries = 3
        self._logger = get_logger("TaskManager")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def register_task(self, task_id, image_path, max_retries=None):
        if max_retries is None:
            max_retries = self.max_retries

        now = time.time()
        with self.lock:
            entry = self.pending_tasks.get(task_id)
            if entry is None:
                self.pending_tasks[task_id] = {
                    "image_path": image_path,
                    "attempts": 1,
                    "max_retries": max_retries,
                    "last_dispatch": now,
                    "next_retry": now + 10,
                }
            else:
                entry["image_path"] = image_path
                entry["attempts"] = 1
                entry["max_retries"] = max_retries
                entry["last_dispatch"] = now
                entry["next_retry"] = now + 10

    def mark_task_completed(self, task_id):
        with self.lock:
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]

    def _monitor_loop(self):
        while True:
            time.sleep(self.check_interval)
            now = time.time()
            to_retry = []

            with self.lock:
                for task_id, entry in list(self.pending_tasks.items()):
                    if now >= entry["next_retry"]:
                        to_retry.append((task_id, entry.copy()))

            for task_id, entry in to_retry:
                if self._is_task_completed(task_id):
                    self.mark_task_completed(task_id)
                    continue

                if entry["attempts"] >= entry["max_retries"]:
                    self._logger.warning(
                        "任务 %s 达到最大重试次数 (%s)，停止重试",
                        task_id, entry["max_retries"]
                    )
                    self.mark_task_completed(task_id)
                    continue

                self._retry_task(task_id, entry)

    def _is_task_completed(self, task_id):
        try:
            conn = get_db_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM task_results WHERE task_id = %s",
                    (task_id,),
                )
                row = cursor.fetchone()
            if row and row[0] and row[0] != "pending":
                return True
        except Exception:
            pass
        finally:
            if "conn" in locals() and conn:
                conn.close()
        return False

    def _retry_task(self, task_id, entry):
        image_path = entry["image_path"]
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
        except Exception as e:
            self._logger.error("读取重试图片失败: %s", e)
            self.mark_task_completed(task_id)
            return

        response = dispatch_task(
            image_path,
            image_data,
            task_id,
            register_pending=False,
        )

        now = time.time()
        with self.lock:
            current = self.pending_tasks.get(task_id)
            if not current:
                return
            current["attempts"] = current.get("attempts", 0) + 1
            current["last_dispatch"] = now
            current["next_retry"] = now + 10

        self._logger.info(
            "任务 %s 第 %s 次重试，结果: %s",
            task_id, entry["attempts"] + 1, response.get("status")
        )


# 全局任务管理器
task_manager = TaskManager()


# 数据库工具
def get_db_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Error as e:
        logger.error("数据库连接失败: %s", e)
        return None


class JsonProtocol:
    """JSON 消息发送和接收类，使用自定义消息头长度前缀协议"""

    def __init__(self):
        self.send_header = "server"
        self.expected_headers = ["node"]  # 在初始化时设置默认值

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
                "发送成功: 头部='%s', 内容长度=%s", header_str, content_length
            )

        except Exception as e:
            logger.error("发送失败: %s", e)
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
                "接收 JSON 失败 (期望标记: %s): %s", self.expected_headers, e
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
                    "未找到期望标记 %s，清空缓冲区重新搜索", self.expected_headers
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
                "无法解析长度数字，找到标记: '%s@'", marker[:-1].decode("utf-8")
            )
            return None, None

        content_length = int(num_buffer.decode("utf-8"))
        content_start = length_start + len(num_buffer)

        logger.debug(
            "解析到内容长度: %s, 起始位置: %s", content_length, content_start
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


# 异步处理函数
def async_handle_register(conn, addr, msg):
    """异步处理注册消息"""
    node_id = msg["data"].get("node_id")
    token = msg["data"].get("token")
    max_tasks = msg["data"].get("max_tasks", 5)

    # 参数检查（新增：验证max_tasks是否为有效数字）
    if not node_id or not token or not isinstance(max_tasks, (int, float)):
        register_ack = {
            "type": "register_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "node_id、token和max_tasks必须提供且有效",
        }
        json_protocol.send_json(conn, register_ack)
        return

    conn_db = get_db_connection()
    if not conn_db:
        register_ack = {
            "type": "register_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "数据库连接失败",
        }
        json_protocol.send_json(conn, register_ack)
        return

    try:
        cursor = conn_db.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT id, name, token, status, addr, is_active, created_at, updated_at
            FROM nodes
            WHERE id = %s AND token = %s AND is_active = 1
        """
        cursor.execute(query, (node_id, token))
        result = cursor.fetchone()

        if result:
            # 修复1：添加节点状态验证
            if node_id in node_manager.nodes:
                register_ack = {
                    "type": "register_ack",
                    "timestamp": int(time.time()),
                    "status": "success",
                    "message": f"节点已注册，最大任务数: {node_manager.get_node_max_tasks(node_id)}",
                    "data": {
                        "max_tasks": max_tasks,
                    },
                }
                json_protocol.send_json(conn, register_ack)
                return

            # 修复2：添加max_tasks范围验证
            if max_tasks <= 0 or max_tasks > 100:  # 假设最大任务数不超过100
                max_tasks = 5  # 使用默认值

            # 使用节点上报的max_tasks注册节点，并同步数据库中的地址与状态
            node_manager.register_node(node_id, addr, conn, max_tasks)
            node_manager.update_db_node_status(node_id, "online", addr=addr)
            node_manager.set_node_idle(node_id)

            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "success",
                "message": f"节点注册成功，最大任务数: {max_tasks}",
                "data": {
                    "max_tasks": max_tasks,
                },
            }
            json_protocol.send_json(conn, register_ack)
            logger.info(
                "注册成功: node_id=%s, addr=%s, max_tasks=%s", node_id, addr, max_tasks
            )
        else:
            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "error",
                "message": "节点未激活或凭证无效",
            }
            json_protocol.send_json(conn, register_ack)
    except Exception as e:
        logger.error("处理注册时出错: %s", e)
        register_ack = {
            "type": "register_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "服务器内部错误",
        }
        json_protocol.send_json(conn, register_ack)
    finally:
        if "cursor" in locals():
            cursor.close()
        if conn_db:
            conn_db.close()


def async_handle_heartbeat(conn, addr, msg, node_id):
    """异步处理心跳消息"""
    node_manager.update_heartbeat(node_id)
    heartbeat_ack = {
        "type": "heartbeat_ack",
        "timestamp": int(time.time()),
        "status": "success",
        "message": "心跳已更新",
    }
    json_protocol.send_json(conn, heartbeat_ack)


def async_handle_task_result(conn, addr, msg):
    """异步处理任务结果消息 - 整合了数据库保存和任务计数减少"""
    node_id = msg["data"].get("node_id")
    task_id = msg["data"].get("task_id")
    result = msg["data"].get("result")

    # 定义完整的异步处理任务
    def process_task_result():
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO task_results (task_id, result, status)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        result = VALUES(result),
                        status = VALUES(status),
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (task_id, json.dumps(result), "completed"))
            conn.commit()
            logger.info("任务结果已保存: task_id=%s", task_id)

            # 如果有node_id，减少任务计数
            if node_id:
                node_manager.decrement_task_count(node_id)
                logger.info("节点 %s 任务计数已减少，task_id=%s", node_id, task_id)

        except Exception as e:
            logger.error("异步保存失败: %s", e)
        finally:
            if "conn" in locals() and conn:
                conn.close()

    # 提交完整的处理任务到异步处理器
    async_processor.submit_task(process_task_result)
    task_manager.mark_task_completed(task_id)


def async_handle_unknown_message(conn, addr, msg):
    """异步处理未知消息类型"""
    conn.sendall(
        json.dumps(
            {"type": "msg", "status": "error", "message": "未知消息类型"}
        ).encode("utf-8")
    )


# 任务分发（供外部调用，如 views.py）
def dispatch_task(
    image_path: str, image_data, task_id: str, register_pending: bool = True
):
    """
    优先通过 TCP 将 image_file（图片二进制）发送给节点，
    使用统一的 JSON 协议，避免粘包问题
    """

    dispatch_task_response = {
        "type": "dispatch_task",
        "timestamp": int(time.time()),
        "status": "pending",
        "message": "任务正在分发",
        "data": {
            "task_id": task_id,
        },
    }

    node_id, node_info = node_manager.get_idle_node()
    if not node_id:
        dispatch_task_response["message"] = "没有空闲节点"
        dispatch_task_response["status"] = "waiting"
        return dispatch_task_response

    socket_obj = node_info.get("socket")
    if not socket_obj:
        node_manager.set_node_idle(node_id)
        dispatch_task_response["message"] = "节点未连接"
        dispatch_task_response["status"] = "failed"
        return dispatch_task_response

    try:
        image_filename = os.path.basename(image_path)

        # 关键修改：将图片数据编码为 base64 放入 JSON 中
        import base64

        # 处理不同类型的 image_data
        if hasattr(image_data, "read"):
            # FileStorage 对象，需要先读取
            image_bytes = image_data.read()
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            # 其他类型，尝试转换为 bytes
            image_bytes = str(image_data).encode("utf-8")

        # 检查图片大小限制（10MB）
        MAX_IMAGE_SIZE = 1024 * 1024 * 10  # 10MB
        if len(image_bytes) > MAX_IMAGE_SIZE:
            logger.error(
                "图片过大: %s 字节，超过10MB限制", len(image_bytes)
            )
            node_manager.set_node_idle(node_id)
            dispatch_task_response["message"] = "图片文件过大"
            dispatch_task_response["status"] = "failed"
            return dispatch_task_response

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        task_msg = {
            "type": "task",
            "timestamp": int(time.time()),
            "data": {
                "task_id": task_id,
                "image_filename": image_filename,
                "image_size": len(image_bytes),
                "image_data": image_base64,
            },
        }

        json_protocol.send_json(socket_obj, task_msg)

        logger.info(
            "任务已发送: task_id=%s, 图片=%s, 大小=%s字节, base64大小=%s字节",
            task_id, image_filename, len(image_bytes), len(image_base64)
        )

        node_manager.set_node_busy(node_id)
        node_manager.increment_task_count(node_id)
        dispatch_task_response["message"] = "任务已分发到节点"
        dispatch_task_response["status"] = "dispatched"
        dispatch_task_response["data"]["node_id"] = node_id

        if register_pending and dispatch_task_response["status"] != "failed":
            task_manager.register_task(task_id, image_path)

        return dispatch_task_response

    except Exception as e:
        logger.error("发送任务失败: %s", e)
        node_manager.set_node_idle(node_id)
        dispatch_task_response["message"] = str(e)
        dispatch_task_response["status"] = "failed"
        dispatch_task_response["data"]["task_id"] = task_id
        return dispatch_task_response


# TCP 服务端核心逻辑
def handle_client(conn, addr):
    logger.info("新连接来自: %s:%s", addr[0], addr[1])
    node_id = None

    try:
        while True:
            msg = json_protocol.recv_json(conn)
            if msg is None:
                break  # 客户端断开或数据错误

            msg_type = msg.get("type")

            if msg_type == "register":
                node_id = msg["data"].get("node_id")
                # 异步处理注册消息
                message_processor.submit_message_task(
                    "register", async_handle_register, conn, addr, msg
                )

            elif msg_type == "heartbeat":
                # 异步处理心跳消息
                if node_id:
                    message_processor.submit_message_task(
                        "heartbeat", async_handle_heartbeat, conn, addr, msg, node_id
                    )
                else:
                    heartbeat_ack = {
                        "type": "heartbeat_ack",
                        "timestamp": int(time.time()),
                        "status": "error",
                        "message": "未注册的节点",
                    }
                    json_protocol.send_json(conn, heartbeat_ack)

            elif msg_type == "task_result":
                # 异步处理任务结果消息
                message_processor.submit_message_task(
                    "task_result", async_handle_task_result, conn, addr, msg
                )

            else:
                # 异步处理未知消息类型
                message_processor.submit_message_task(
                    "default", async_handle_unknown_message, conn, addr, msg
                )

    except ConnectionResetError:
        logger.info("连接断开: %s:%s", addr[0], addr[1])
    finally:
        if node_id:
            with node_manager.lock:
                if node_id in node_manager.nodes:
                    # 立即更新状态为离线并同步到数据库
                    node_manager.nodes[node_id]["status"] = "offline"
                    node_manager.update_db_node_status(node_id, "offline")
                    logger.info(
                        "节点 %s 连接异常断开，立即标记为离线", node_id
                    )

                    # 从内存中移除节点
                    del node_manager.nodes[node_id]
                    logger.info("节点 %s 已从内存中移除", node_id)

        try:
            conn.close()
        except:
            pass
        logger.info("连接关闭: %s:%s", addr[0], addr[1])


# 启动 TCP 服务
def start_tcp_server(host="0.0.0.0", port=TCP_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        logger.info("TCP 服务启动，监听 %s:%s", host, port)

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
                logger.debug("第 %s 次节点监控", monitor_counter)
                node_manager.show_all_nodes()

        threading.Thread(target=monitor_nodes, daemon=True).start()

        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()
