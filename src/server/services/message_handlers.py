"""消息处理器 - 提供各种 TCP 消息类型的异步处理函数"""

import json
import time
import os
import base64
import pymysql

from config.base import DB_CONFIG
from config.log_config import get_logger
from services.node_manager import node_manager, get_db_connection
from services.protocol.json_protocol import json_protocol
from services.async_processor import async_processor

logger = get_logger("message_handlers")


def async_handle_register(conn, addr, msg):
    """异步处理注册消息"""
    node_id = msg["data"].get("node_id")
    token = msg["data"].get("token")
    max_tasks = msg["data"].get("max_tasks", 5)

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
            if node_id in node_manager.nodes:
                register_ack = {
                    "type": "register_ack",
                    "timestamp": int(time.time()),
                    "status": "success",
                    "message": f"节点已注册，最大任务数: {node_manager.get_node_max_tasks(node_id)}",
                    "data": {"max_tasks": max_tasks},
                }
                json_protocol.send_json(conn, register_ack)
                return

            if max_tasks <= 0 or max_tasks > 100:
                max_tasks = 5

            node_manager.register_node(node_id, addr, conn, max_tasks)
            node_manager.update_db_node_status(node_id, "online", addr=addr)
            node_manager.set_node_idle(node_id)

            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "success",
                "message": f"节点注册成功，最大任务数: {max_tasks}",
                "data": {"max_tasks": max_tasks},
            }
            json_protocol.send_json(conn, register_ack)
            logger.info("注册成功: node_id=%s, addr=%s, max_tasks=%s", node_id, addr, max_tasks)
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
    """异步处理任务结果消息"""
    node_id = msg["data"].get("node_id")
    task_id = msg["data"].get("task_id")
    result = msg["data"].get("result")

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

            if node_id:
                node_manager.decrement_task_count(node_id)
                logger.info("节点 %s 任务计数已减少，task_id=%s", node_id, task_id)
        except Exception as e:
            logger.error("异步保存失败: %s", e)
        finally:
            if "conn" in locals() and conn:
                conn.close()

    async_processor.submit_task(process_task_result)
    from services.task_manager import task_manager
    task_manager.mark_task_completed(task_id)


def async_handle_unknown_message(conn, addr, msg):
    """异步处理未知消息类型"""
    conn.sendall(
        json.dumps({"type": "msg", "status": "error", "message": "未知消息类型"}).encode("utf-8")
    )
