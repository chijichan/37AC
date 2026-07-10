"""任务分发器 - 将任务分发给 TCP 节点"""

import os
import base64
import time

from config.log_config import get_logger
from services.node_manager import node_manager
from services.protocol.json_protocol import json_protocol
from services.task_manager import task_manager

logger = get_logger("task_dispatcher")

# 图片大小限制（10MB）
MAX_IMAGE_SIZE = 1024 * 1024 * 10


def dispatch_task(image_path: str, image_data, task_id: str,
                  register_pending: bool = True,
                  recognition_type: str = "local"):
    """优先通过 TCP 将 image_file（图片二进制）发送给节点。

    Args:
        image_path: 图片服务器本地路径
        image_data: 二进制或 file-like 对象
        task_id: 唯一任务 ID
        register_pending: 是否注册到任务管理器
        recognition_type: 识别方式类型
                          "local"  – 本地 ResNet 模型（默认）
                          "llm"    – 第三方大模型 API（如 DeepSeek）
                          "auto"   – 由节点根据自身配置自动选择
    """
    response = {
        "type": "dispatch_task",
        "timestamp": int(time.time()),
        "status": "pending",
        "message": "任务正在分发",
        "data": {"task_id": task_id},
    }

    # 根据识别能力类型获取匹配的空闲节点
    node_id, node_info = node_manager.get_idle_node_by_capability(recognition_type)
    if not node_id:
        # 降级：如果没有匹配能力的空闲节点，尝试获取任意空闲节点
        node_id, node_info = node_manager.get_idle_node()
        if not node_id:
            response["message"] = "没有空闲节点"
            response["status"] = "waiting"
            return response
        logger.warning(
            "没有支持 %s 能力的空闲节点，降级分发到任意节点 node_id=%s",
            recognition_type, node_id
        )

    socket_obj = node_info.get("socket")
    if not socket_obj:
        node_manager.set_node_idle(node_id)
        response["message"] = "节点未连接"
        response["status"] = "failed"
        return response

    try:
        image_filename = os.path.basename(image_path)

        # 处理不同类型的 image_data
        if hasattr(image_data, "read"):
            image_bytes = image_data.read()
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            image_bytes = str(image_data).encode("utf-8")

        # 检查图片大小限制
        if len(image_bytes) > MAX_IMAGE_SIZE:
            logger.error("图片过大: %s 字节，超过10MB限制", len(image_bytes))
            node_manager.set_node_idle(node_id)
            response["message"] = "图片文件过大"
            response["status"] = "failed"
            return response

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        task_msg = {
            "type": "task",
            "timestamp": int(time.time()),
            "data": {
                "task_id": task_id,
                "image_filename": image_filename,
                "image_size": len(image_bytes),
                "image_data": image_base64,
                "recognition_type": recognition_type,
            },
        }

        json_protocol.send_json(socket_obj, task_msg)

        logger.info(
            "任务已发送: task_id=%s, 图片=%s, 大小=%s字节, 识别方式=%s",
            task_id, image_filename, len(image_bytes), recognition_type
        )

        node_manager.set_node_busy(node_id)
        node_manager.increment_task_count(node_id)
        response["message"] = "任务已分发到节点"
        response["status"] = "dispatched"
        response["data"]["node_id"] = node_id

        if register_pending:
            task_manager.register_task(task_id, image_path, recognition_type=recognition_type)

        return response

    except Exception as e:
        logger.error("发送任务失败: %s", e)
        node_manager.set_node_idle(node_id)
        response["message"] = str(e)
        response["status"] = "failed"
        return response
