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
from services.sse_bus import sse_bus

logger = get_logger("message_handlers")


def async_handle_register(conn, addr, msg):
    """异步处理注册消息"""
    node_id = msg["data"].get("node_id")
    token = msg["data"].get("token")
    max_tasks = msg["data"].get("max_tasks", 5)
    capabilities = msg["data"].get("capabilities", '["local"]')
    # 节点上报的 LLM 配置（用于任务重试间隔决策）
    llm_enabled = msg["data"].get("llm_enabled", False)
    llm_timeout_sec = msg["data"].get("llm_timeout_sec", 0)

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
            SELECT id, name, token, capabilities, status, addr, is_active, created_at, updated_at
            FROM nodes
            WHERE id = %s AND token = %s AND is_active = 1
        """
        cursor.execute(query, (node_id, token))
        result = cursor.fetchone()

        if result:
            if node_id in node_manager.nodes:
                # 节点已注册（重复注册/重连场景）：
                # 1) 重置任务计数与状态，防止上次会话残留计数导致节点被误判繁忙
                # 2) 更新 socket 指向当前连接，避免任务发送到已失效的旧连接
                node_manager.nodes[node_id]["current_tasks"] = 0
                node_manager.nodes[node_id]["status"] = "idle"
                node_manager.nodes[node_id]["socket"] = conn
                node_manager.nodes[node_id]["capabilities"] = capabilities
                node_manager.nodes[node_id]["llm_enabled"] = bool(llm_enabled)
                node_manager.nodes[node_id]["llm_timeout_sec"] = int(llm_timeout_sec or 0)
                node_manager.update_db_node_capabilities(node_id, capabilities)
                register_ack = {
                    "type": "register_ack",
                    "timestamp": int(time.time()),
                    "status": "success",
                    "message": f"节点已注册，最大任务数: {node_manager.get_node_max_tasks(node_id)}",
                    "data": {"max_tasks": max_tasks, "capabilities": capabilities},
                }
                json_protocol.send_json(conn, register_ack)
                return

            if max_tasks <= 0 or max_tasks > 100:
                max_tasks = 5

            node_manager.register_node(
                node_id, addr, conn, max_tasks, capabilities,
                llm_enabled=llm_enabled, llm_timeout_sec=llm_timeout_sec,
            )
            node_manager.update_db_node_status(node_id, "online", addr=addr)
            node_manager.update_db_node_capabilities(node_id, capabilities)
            node_manager.set_node_idle(node_id)

            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "success",
                "message": f"节点注册成功，最大任务数: {max_tasks}，能力: {capabilities}",
                "data": {"max_tasks": max_tasks, "capabilities": capabilities},
            }
            json_protocol.send_json(conn, register_ack)
            logger.info("注册成功: node_id=%s, addr=%s, max_tasks=%s, capabilities=%s, llm_enabled=%s, llm_timeout=%s",
                        node_id, addr, max_tasks, capabilities, llm_enabled, llm_timeout_sec)
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
            try:
                cursor.close()
            except Exception:
                pass
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
            if not conn:
                logger.error("任务结果保存失败: 数据库连接失败 task_id=%s", task_id)
                return
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

            # DB 写入成功后才从 pending_tasks 移除，避免竞态导致任务丢失
            from services.task_manager import task_manager
            task_manager.mark_task_completed(task_id)

            # 推送到 SSE 事件总线（实时通知前端）
            sse_bus.publish(task_id, {
                "status": "completed",
                "message": "任务完成，结果已返回",
                "task_id": task_id,
                "result": result,
            })
        except Exception as e:
            logger.error("异步保存失败: %s", e)
        finally:
            if "conn" in locals() and conn:
                conn.close()
            # 无论 DB 保存是否成功，节点任务计数都必须减少：
            # 节点已完成该任务（结果已回传），否则计数泄漏会导致
            # current_tasks 虚高、节点被误判为繁忙而不再接收新任务
            if node_id:
                node_manager.decrement_task_count(node_id)
                logger.info("节点 %s 任务计数已减少，task_id=%s", node_id, task_id)

    async_processor.submit_task(process_task_result)


def async_handle_unknown_message(conn, addr, msg):
    """异步处理未知消息类型"""
    json_protocol.send_json(conn, {
        "type": "msg",
        "status": "error",
        "message": "未知消息类型",
    })
