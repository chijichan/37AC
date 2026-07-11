"""节点管理器 - 管理 TCP 节点的注册、心跳、状态和负载"""

import json
import time
import threading
import socket
from datetime import datetime

import pymysql

from config.base import DB_CONFIG
from config.log_config import get_logger

logger = get_logger("NodeManager")


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        return None


class NodeManager:
    """节点管理器，管理所有 TCP 节点的生命周期和状态"""

    def __init__(self):
        self.nodes = {}  # node_id -> dict
        self.lock = threading.Lock()
        self._logger = get_logger("NodeManager")

    def register_node(self, node_id, addr, socket_obj=None, max_tasks=None, capabilities=None):
        """注册节点"""
        with self.lock:
            if max_tasks is None:
                max_tasks = 5
            if capabilities is None:
                capabilities = '["local"]'  # 默认仅支持本地 YOLO+ResNet 模型

            self.nodes[node_id] = {
                "addr": addr,
                "socket": socket_obj,
                "last_heartbeat": time.time(),
                "status": "idle",
                "max_tasks": max_tasks,
                "current_tasks": 0,
                "capabilities": capabilities,
            }
            self._logger.info(
                "节点 %s (%s) 已注册，状态：空闲，最大任务数：%s，能力：%s",
                node_id, f"{addr[0]}:{addr[1]}" if isinstance(addr, tuple) else str(addr),
                max_tasks, capabilities
            )
            return True

    def update_heartbeat(self, node_id):
        """更新节点心跳时间"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["last_heartbeat"] = time.time()
                return True
            return False

    def set_node_busy(self, node_id):
        """设置节点为忙碌状态"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if node["current_tasks"] >= node["max_tasks"]:
                    node["status"] = "busy"
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
        """增加节点任务计数"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                old_count = node["current_tasks"]
                node["current_tasks"] += 1
                if node["current_tasks"] >= node["max_tasks"]:
                    node["status"] = "busy"
                return True
            return False

    def decrement_task_count(self, node_id):
        """减少节点任务计数"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if node["current_tasks"] > 0:
                    node["current_tasks"] -= 1
                    if node["status"] == "busy" and node["current_tasks"] < node["max_tasks"]:
                        node["status"] = "idle"
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
                        if node["max_tasks"] > 0 else 0
                    ),
                    "status": node["status"],
                }
            return None

    def get_available_nodes(self):
        """获取所有可用节点"""
        available_nodes = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if info.get("socket") is not None:
                    available_nodes.append({
                        "node_id": node_id,
                        "addr": f"{info['addr'][0]}:{info['addr'][1]}",
                        "status": info["status"],
                        "max_tasks": info["max_tasks"],
                        "current_tasks": info["current_tasks"],
                        "capabilities": info.get("capabilities", '["local"]'),
                        "load_percentage": (
                            (info["current_tasks"] / info["max_tasks"]) * 100
                            if info["max_tasks"] > 0 else 0
                        ),
                    })
        return available_nodes

    def get_idle_node(self):
        """获取一个空闲节点"""
        with self.lock:
            for node_id, info in self.nodes.items():
                if info["status"] == "idle" and info.get("socket") is not None:
                    return node_id, info
        self._logger.debug(
            "get_idle_node() 未找到空闲节点，当前节点数=%d", len(self.nodes)
        )
        return None, None

    def get_idle_nodes(self):
        """获取所有空闲节点"""
        idle_nodes = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if (info.get("socket") is not None
                        and info["status"] == "idle"
                        and info["current_tasks"] < info["max_tasks"]):
                    idle_nodes.append({
                        "node_id": node_id,
                        "addr": f"{info['addr'][0]}:{info['addr'][1]}",
                        "max_tasks": info["max_tasks"],
                        "current_tasks": info["current_tasks"],
                        "capabilities": info.get("capabilities", '["local"]'),
                        "load_percentage": (
                            (info["current_tasks"] / info["max_tasks"]) * 100
                            if info["max_tasks"] > 0 else 0
                        ),
                    })
        return idle_nodes

    def get_idle_node_by_capability(self, recognition_type):
        """根据识别能力获取一个匹配的空闲节点。

        Args:
            recognition_type: 识别方式类型
                              "local" – 需要支持本地 YOLO+ResNet 模型推理的节点
                              "llm"   – 需要支持第三方大模型推理的节点
                              "auto"  – 任意可用节点均可

        Returns:
            (node_id, node_info) or (None, None)
        """
        with self.lock:
            for node_id, info in self.nodes.items():
                has_socket = info.get("socket") is not None
                is_idle = info["status"] == "idle"
                has_capacity = info["current_tasks"] < info["max_tasks"]
                node_caps = info.get("capabilities", '["local"]')
                try:
                    caps_list = json.loads(node_caps)
                except Exception:
                    caps_list = ["local"]
                caps_match = recognition_type == "auto" or recognition_type in caps_list

                if has_socket and is_idle and has_capacity and caps_match:
                    return node_id, info

            # DEBUG: 记录所有节点诊断信息
            self._logger.debug(
                "get_idle_node_by_capability(%s) 未找到匹配节点，当前节点数=%d",
                recognition_type, len(self.nodes)
            )
            for nid, ninfo in self.nodes.items():
                self._logger.debug(
                    "  节点 %s: socket=%s, status=%s, tasks=%s/%s, caps=%s",
                    nid,
                    "有" if ninfo.get("socket") is not None else "无",
                    ninfo.get("status"),
                    ninfo.get("current_tasks"),
                    ninfo.get("max_tasks"),
                    ninfo.get("capabilities"),
                )

        return None, None

    def get_node_socket(self, node_id):
        """获取节点的 socket 对象"""
        with self.lock:
            node = self.nodes.get(node_id)
            if node and node.get("socket"):
                return node["socket"]
        return None

    def cleanup_nodes(self, timeout=30):
        """清理超时节点"""
        current_time = time.time()
        to_remove = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if current_time - info["last_heartbeat"] > timeout:
                    self._logger.info("节点 %s 超时未心跳，将被移除", node_id)
                    self.update_db_node_status(node_id, "offline")
                    to_remove.append((node_id, info))
            for node_id, info in to_remove:
                # 关闭 socket 连接，触发 handle_client 线程退出
                sock = info.get("socket")
                if sock:
                    try:
                        sock.settimeout(0.1)
                        sock.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    try:
                        sock.close()
                    except Exception:
                        pass
                del self.nodes[node_id]

    def show_all_nodes(self):
        """打印所有节点信息"""
        with self.lock:
            self._logger.debug("当前所有节点信息:")
            for node_id, info in self.nodes.items():
                addr = info.get("addr", ("Unknown", 0))
                ip, port = addr
                status = info.get("status", "N/A")
                last_hb = info.get("last_heartbeat", "N/A")
                max_tasks = info.get("max_tasks", "N/A")
                current_tasks = info.get("current_tasks", "N/A")
                capabilities = info.get("capabilities", '["local"]')

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
                    "节点ID: %-20s | 地址: %s:%s | 状态: %s | 任务: %s/%s | 负载: %.1f%% | 能力: %s | 心跳: %s",
                    node_id, ip, port, status, current_tasks, max_tasks, load_percent, capabilities, ts_str
                )

    def update_db_node_status(self, node_id, status, addr=None):
        """更新节点在数据库中的状态"""
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
    def update_db_node_capabilities(self, node_id, capabilities):
        """更新节点在数据库中的能力标识"""
        try:
            conn = get_db_connection()
            if not conn:
                self._logger.error("无法连接数据库，无法更新节点 %s 能力", node_id)
                return False
            with conn.cursor() as cursor:
                sql = "UPDATE nodes SET capabilities = %s, updated_at = NOW() WHERE id = %s"
                cursor.execute(sql, (capabilities, node_id))
            conn.commit()
            self._logger.debug("节点 %s 能力更新为 %s", node_id, capabilities)
            return True
        except Exception as e:
            self._logger.error("更新节点能力失败: %s", e)
            return False
        finally:
            if "conn" in locals() and conn:
                conn.close()

    def remove_node(self, node_id):
        """从内存中移除节点并设置离线状态（线程安全）"""
        with self.lock:
            if node_id not in self.nodes:
                return False
            info = self.nodes[node_id]
            self.update_db_node_status(node_id, "offline")
            self._logger.info("节点 %s 已标记为离线", node_id)
            del self.nodes[node_id]
            self._logger.info("节点 %s 已从内存中移除", node_id)
            return True

# 模块级全局实例
node_manager = NodeManager()
