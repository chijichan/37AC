"""节点管理器 - 管理 TCP 节点的注册、心跳、状态和负载"""

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

    def register_node(self, node_id, addr, socket_obj=None, max_tasks=None):
        """注册节点"""
        with self.lock:
            if max_tasks is None:
                max_tasks = 5

            self.nodes[node_id] = {
                "addr": addr,
                "socket": socket_obj,
                "last_heartbeat": time.time(),
                "status": "idle",
                "max_tasks": max_tasks,
                "current_tasks": 0,
            }
            self._logger.info(
                "节点 %s (%s) 已注册，状态：空闲，最大任务数：%s",
                node_id, f"{addr[0]}:{addr[1]}" if isinstance(addr, tuple) else str(addr), max_tasks
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
                        "load_percentage": (
                            (info["current_tasks"] / info["max_tasks"]) * 100
                            if info["max_tasks"] > 0 else 0
                        ),
                    })
        return idle_nodes

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


# 模块级全局实例
node_manager = NodeManager()
