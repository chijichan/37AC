# services/message_handlers.py
"""消息处理器 - 提供各种 TCP 消息类型的异步处理函数"""

import base64
import json
import os
import time

import pymysql

from common.crypto import verify_node_token
from config.base import DB_CONFIG
from config.log_config import get_logger
from services import channel_service
from services.node_manager import node_manager, get_db_connection
from services.protocol.json_protocol import json_protocol
from services.async_processor import async_processor
from services.sse_bus import sse_bus

logger = get_logger("message_handlers")


def async_handle_register(conn, addr, msg):
    """处理注册消息；成功返回 True，失败返回 False。"""
    node_id = msg["data"].get("node_id")
    token = msg["data"].get("token")
    max_tasks = msg["data"].get("max_tasks", 5)
    capabilities = msg["data"].get("capabilities", '["local"]')
    # 节点上报的识别模型列表（默认 37ac 本地模型）
    raw_models = msg["data"].get("models") or ["37ac"]
    if isinstance(raw_models, str):
        try:
            models = json.loads(raw_models)
        except Exception:
            models = ["37ac"]
    else:
        models = list(raw_models)
    if not models:
        models = ["37ac"]
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
        return False

    conn_db = get_db_connection()
    if not conn_db:
        register_ack = {
            "type": "register_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "数据库连接失败",
        }
        json_protocol.send_json(conn, register_ack)
        return False

    try:
        cursor = conn_db.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT id, name, token, capabilities, status, addr, is_active, created_at, updated_at
            FROM nodes
            WHERE id = %s AND is_active = 1
        """
        cursor.execute(query, (node_id,))
        result = cursor.fetchone()

        if result and verify_node_token(token, result.get("token")):
            if node_id in node_manager.nodes:
                # 节点已注册（重复注册/重连场景）：
                # 1) 重置任务计数与状态，防止上次会话残留计数导致节点被误判繁忙
                # 2) 更新 socket 指向当前连接，避免任务发送到已失效的旧连接
                # 3) 清理旧分配记录，旧任务不再允许从该连接回传
                with node_manager.lock:
                    node = node_manager.nodes[node_id]
                    node["current_tasks"] = 0
                    node["status"] = "idle"
                    node["socket"] = conn
                    if 0 < max_tasks <= 100:
                        node["max_tasks"] = int(max_tasks)
                    node["capabilities"] = capabilities
                    node["models"] = models
                    node["llm_enabled"] = bool(llm_enabled)
                    node["llm_timeout_sec"] = int(llm_timeout_sec or 0)
                    node["assigned_tasks"] = set()
                node_manager.update_db_node_capabilities(node_id, capabilities)
                register_ack = {
                    "type": "register_ack",
                    "timestamp": int(time.time()),
                    "status": "success",
                    "message": f"节点已注册，最大任务数: {node_manager.get_node_max_tasks(node_id)}",
                    "data": {
                        "max_tasks": max_tasks,
                        "capabilities": capabilities,
                        "models": node_manager.get_model_list(),
                    },
                }
                json_protocol.send_json(conn, register_ack)
                return True

            if max_tasks <= 0 or max_tasks > 100:
                max_tasks = 5

            node_manager.register_node(
                node_id, addr, conn, max_tasks, capabilities,
                models=models, llm_enabled=llm_enabled, llm_timeout_sec=llm_timeout_sec,
            )
            node_manager.update_db_node_status(node_id, "online", addr=addr)
            node_manager.update_db_node_capabilities(node_id, capabilities)
            node_manager.set_node_idle(node_id)

            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "success",
                "message": f"节点注册成功，最大任务数: {max_tasks}，能力: {capabilities}",
                "data": {
                    "max_tasks": max_tasks,
                    "capabilities": capabilities,
                    "models": node_manager.get_model_list(),
                },
            }
            json_protocol.send_json(conn, register_ack)
            logger.info("注册成功: node_id=%s, addr=%s, max_tasks=%s, capabilities=%s, llm_enabled=%s, llm_timeout=%s",
                        node_id, addr, max_tasks, capabilities, llm_enabled, llm_timeout_sec)
            return True
        else:
            register_ack = {
                "type": "register_ack",
                "timestamp": int(time.time()),
                "status": "error",
                "message": "节点未激活或凭证无效",
            }
            json_protocol.send_json(conn, register_ack)
            return False
    except Exception as e:
        logger.error("处理注册时出错: %s", e)
        register_ack = {
            "type": "register_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "服务器内部错误",
        }
        try:
            json_protocol.send_json(conn, register_ack)
        except Exception:
            pass
        return False
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
    if not node_manager.update_heartbeat(node_id):
        heartbeat_ack = {
            "type": "heartbeat_ack",
            "timestamp": int(time.time()),
            "status": "error",
            "message": "节点未注册",
        }
        json_protocol.send_json(conn, heartbeat_ack)
        return
    heartbeat_ack = {
        "type": "heartbeat_ack",
        "timestamp": int(time.time()),
        "status": "success",
        "message": "心跳已更新",
    }
    json_protocol.send_json(conn, heartbeat_ack)


def async_handle_task_result(conn, addr, msg):
    """异步处理任务结果消息（仅接受已分配给该节点的任务）。"""
    node_id = msg["data"].get("node_id")
    task_id = msg["data"].get("task_id")
    result = msg["data"].get("result")

    if not node_id or not task_id:
        logger.warning("任务结果缺少 node_id 或 task_id")
        return
    if not node_manager.is_task_assigned(node_id, task_id):
        logger.warning(
            "收到未授权/未知任务结果: node_id=%s, task_id=%s", node_id, task_id
        )
        return

    # 多通道：节点回来的可能是 "<父id>:<通道>"，结果要合并进父任务行
    parent_id, channel = channel_service.split_task_id(task_id)

    def process_task_result():
        try:
            conn = get_db_connection()
            if not conn:
                logger.error("任务结果保存失败: 数据库连接失败 task_id=%s", task_id)
                return
            with conn.cursor() as cursor:
                # 1) 读出父任务已有的 result（多通道要按通道合并，不能互相覆盖）
                payload = {}
                try:
                    cursor.execute("SELECT result FROM task_results WHERE task_id = %s", (parent_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                except Exception as read_err:
                    logger.debug("读取已有任务结果失败 task_id=%s: %s", parent_id, read_err)
                if not isinstance(payload, dict):
                    payload = {}

                # 2) 判定通道并合并（后缀 → 节点上报的 channel → 该节点分配记录 → 请求的通道 → 推断）
                target = channel_service.resolve_result_channel(
                    parent_id,
                    task_id,
                    payload,
                    reported_channel=msg["data"].get("channel"),
                    assigned_tasks=node_manager.get_assigned_tasks(node_id),
                    inferred_type=(result or {}).get("recognition_type"),
                )
                if not target:
                    # 判不出来就丢弃：宁可这条通道继续等，也不能把结果塞进别的通道
                    logger.warning(
                        "无法判定结果的通道，已丢弃: node_id=%s task_id=%s requested=%s recognition=%s",
                        node_id, task_id, payload.get("requested_channels"),
                        (result or {}).get("recognition_type"),
                    )
                    return
                if channel_service.is_duplicate_channel_result(payload, target, result):
                    logger.warning(
                        "重复的通道结果，已忽略: task_id=%s channel=%s（节点重试/网络重发）",
                        parent_id, target,
                    )
                    return
                channel_service.merge_channel_result(payload, target, result)
                channel = target

                status = channel_service.overall_status(payload) or "completed"
                sql = """
                    INSERT INTO task_results (task_id, result, status, node_id)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        result = VALUES(result),
                        status = VALUES(status),
                        node_id = VALUES(node_id),
                        updated_at = CURRENT_TIMESTAMP
                """
                try:
                    cursor.execute(sql, (parent_id, json.dumps(payload, ensure_ascii=False), status, node_id))
                except pymysql.err.OperationalError as sql_err:
                    # 兜底：task_results.node_id 列尚未迁移时（1054 Unknown column），
                    # 退回旧 SQL，避免因为迁移没跑而丢结果
                    if sql_err.args and sql_err.args[0] == 1054:
                        logger.warning("task_results.node_id 列不存在，退回旧写法（请执行数据库迁移）")
                        cursor.execute(
                            "INSERT INTO task_results (task_id, result, status) VALUES (%s, %s, %s) "
                            "ON DUPLICATE KEY UPDATE result = VALUES(result), status = VALUES(status), "
                            "updated_at = CURRENT_TIMESTAMP",
                            (parent_id, json.dumps(payload, ensure_ascii=False), status),
                        )
                    else:
                        raise
            conn.commit()
            logger.info("任务结果已保存: task_id=%s channel=%s status=%s", parent_id, channel, status)

            # DB 写入成功后才从 pending_tasks 移除，避免竞态导致任务丢失
            from services.task_manager import task_manager
            task_manager.mark_task_completed(task_id)

            # 推送到 SSE 事件总线（按父任务 id 推送，前端只订阅一次）
            sse_bus.publish(parent_id, {
                "status": "completed" if status == "completed" else status,
                "message": "任务完成，结果已返回" if status == "completed" else "部分通道已完成",
                "task_id": parent_id,
                "channel": channel or fallback,
                "channel_status": {
                    c: channel_service.channel_status(payload, c)
                    for c in (payload.get("requested_channels") or [])
                },
                # 旧字段：顶层 characters（主通道），老前端零改动
                "result": payload.get("characters") or [],
                # 新字段：完整的分通道结果 —— 前端可以在 partial 时立刻渲染已完成的通道，
                # 不必等其余通道（例如 37ac 比 llm 快时先出结果）
                "channel_results": payload,
            })
        except Exception as e:
            logger.error("异步保存失败: %s", e)
        finally:
            if "conn" in locals() and conn:
                conn.close()
            # 无论 DB 保存是否成功，节点任务计数和分配记录都必须清理：
            # 节点已完成该任务（结果已回传），否则计数泄漏会导致
            # current_tasks 虚高、节点被误判为繁忙而不再接收新任务
            if node_id:
                node_manager.complete_task(node_id, task_id)
                node_manager.decrement_task_count(node_id)
                logger.info("节点 %s 任务计数已减少，task_id=%s", node_id, task_id)

    async_processor.submit_task(process_task_result)


def async_handle_image_response(conn, addr, msg):
    """节点回传的补拉图片（需求3 后半）：唤醒等待中的请求方。"""
    data = msg.get("data") or {}
    request_id = data.get("request_id")
    if not request_id:
        logger.warning("image_response 缺少 request_id，已忽略")
        return
    from services import image_refetch
    image_refetch.resolve(request_id, data)


def async_handle_unknown_message(conn, addr, msg):
    """异步处理未知消息类型"""
    json_protocol.send_json(conn, {
        "type": "msg",
        "status": "error",
        "message": "未知消息类型",
    })
