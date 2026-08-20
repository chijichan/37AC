"""TCP 监听服务 - 提供 TCP 服务器核心逻辑，接收节点连接并处理消息"""

import os
import socket
import threading
import json
import time
from config.log_config import get_logger

# 从拆分后的子模块导入
from services.node_manager import node_manager
from services.task_manager import task_manager
from services.async_processor import message_type_processor as message_processor
from services.protocol.json_protocol import json_protocol
from services.message_handlers import (
    async_handle_register,
    async_handle_heartbeat,
    async_handle_task_result,
    async_handle_unknown_message,
)
from config.base import TCP_PORT

logger = get_logger("listen_service")


# TCP 服务端核心逻辑
def handle_client(conn, addr):
    logger.info("新连接来自: %s:%s", addr[0], addr[1])
    node_id = None
    authenticated = False

    try:
        while True:
            msg = json_protocol.recv_json(conn)
            if msg is None:
                break  # 客户端断开或数据错误

            msg_type = msg.get("type")

            if msg_type == "register":
                # 注册改为同步处理：只有认证成功后才允许后续消息
                candidate_node_id = msg["data"].get("node_id")
                if async_handle_register(conn, addr, msg):
                    node_id = candidate_node_id
                    authenticated = True
                else:
                    # 注册失败，async_handle_register 已发送错误 ACK，直接关闭连接
                    break

            elif msg_type == "heartbeat":
                # 异步处理心跳消息
                if not authenticated or not node_id:
                    heartbeat_ack = {
                        "type": "heartbeat_ack",
                        "timestamp": int(time.time()),
                        "status": "error",
                        "message": "未注册的节点",
                    }
                    json_protocol.send_json(conn, heartbeat_ack)
                else:
                    message_processor.submit_message_task(
                        "heartbeat", async_handle_heartbeat, conn, addr, msg, node_id
                    )

            elif msg_type == "task_result":
                # 只接受已认证连接且 node_id 与当前连接一致的任务结果
                if not authenticated or not node_id:
                    error_msg = {
                        "type": "error",
                        "timestamp": int(time.time()),
                        "status": "error",
                        "message": "未注册的节点",
                    }
                    json_protocol.send_json(conn, error_msg)
                    break

                msg_node_id = msg.get("data", {}).get("node_id")
                if msg_node_id != node_id:
                    logger.warning(
                        "任务结果 node_id 不匹配: 连接=%s, 消息=%s", node_id, msg_node_id
                    )
                    error_msg = {
                        "type": "error",
                        "timestamp": int(time.time()),
                        "status": "error",
                        "message": "任务结果 node_id 与当前连接不匹配",
                    }
                    json_protocol.send_json(conn, error_msg)
                    break

                # 异步处理任务结果消息
                message_processor.submit_message_task(
                    "task_result", async_handle_task_result, conn, addr, msg
                )

            else:
                # 异步处理未知消息类型
                message_processor.submit_message_task(
                    "default", async_handle_unknown_message, conn, addr, msg
                )

    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ConnectionError, OSError):
        logger.info("连接断开: %s:%s", addr[0], addr[1])
    except Exception as e:
        logger.error("handle_client 未预期异常 %s:%s: %s", addr[0], addr[1], e, exc_info=True)
    finally:
        if authenticated and node_id:
            # 仅当当前连接仍是该节点在内存中的活动连接时才移除，
            # 避免旧连接断开时误删已重连成功的新连接。
            info = node_manager.nodes.get(node_id)
            if info and info.get("socket") is conn:
                try:
                    node_manager.remove_node(node_id)
                except Exception as e:
                    logger.warning("remove_node 异常 %s: %s", node_id, e)

        try:
            conn.close()
        except Exception as e:
            logger.warning("关闭连接异常 %s:%s: %s", addr[0], addr[1], e)
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
