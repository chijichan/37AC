"""任务分发器 - 将任务分发给 TCP 节点"""

import base64
import os
import time

from config.log_config import get_logger
from services.node_manager import node_manager
from services.protocol.json_protocol import json_protocol
from services.task_manager import task_manager

logger = get_logger("task_dispatcher")

# 图片大小限制（10MB）
MAX_IMAGE_SIZE = 1024 * 1024 * 10


def dispatch_task(image_path: str | None, image_data, task_id: str,
                  image_filename: str | None = None,
                  register_pending: bool = True,
                  recognition_type: str = "local"):
    """优先通过 TCP 将 image_file（图片二进制）发送给节点。

    Args:
        image_path: 图片服务器本地路径，不保存到磁盘时为 None
        image_data: 二进制或 file-like 对象
        task_id: 唯一任务 ID
        image_filename: 原始图片文件名，用于下发给节点
        register_pending: 是否注册到任务管理器
        recognition_type: 识别方式类型
                          "local"  – 本地 YOLO+ResNet 模型（默认）
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

    # 原子性地分配一个可用节点（锁内完成选择、socket 探测、任务计数增加）
    node_id, socket_obj = node_manager.allocate_node_for_task(recognition_type)
    if not node_id:
        response["message"] = "没有空闲节点"
        response["status"] = "waiting"
        # 携带预计重试间隔（秒），供前端展示等待倒计时
        response["retry_in"] = task_manager.get_retry_interval(recognition_type)
        # 即使没有空闲节点，也要注册 pending 任务，让 task_manager 重试
        if register_pending:
            task_manager.register_task(
                task_id,
                image_path,
                image_data=image_data if isinstance(image_data, bytes) else None,
                recognition_type=recognition_type,
            )
        return response

    try:
        image_filename = image_filename or (
            os.path.basename(image_path) if image_path else f"{task_id}.jpg"
        )

        # 处理不同类型的 image_data
        if hasattr(image_data, "read"):
            image_bytes = image_data.read()
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        else:
            logger.error("dispatch_task: 不支持的 image_data 类型 %s", type(image_data))
            response["message"] = "图片数据格式错误"
            response["status"] = "failed"
            return response

        # 检查图片大小限制
        if len(image_bytes) > MAX_IMAGE_SIZE:
            logger.error("图片过大: %s 字节，超过10MB限制", len(image_bytes))
            # 分配节点时已执行 current_tasks += 1，必须同步减少计数
            node_manager.decrement_task_count(node_id)
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

        # 发送前先记录任务归属，确保节点断线或发送失败仍可重试
        if register_pending:
            task_manager.register_task(
                task_id,
                image_path,
                image_data=image_bytes,
                recognition_type=recognition_type,
            )

        # 记录该任务已分配给此节点，用于回传结果时的归属校验
        node_manager.assign_task(node_id, task_id)

        json_protocol.send_json(socket_obj, task_msg)

        logger.info(
            "任务已发送: task_id=%s, 图片=%s, 大小=%s字节, 识别方式=%s",
            task_id, image_filename, len(image_bytes), recognition_type
        )

        response["message"] = "任务已分发到节点"
        response["status"] = "dispatched"
        response["data"]["node_id"] = node_id

        return response

    except Exception as e:
        logger.error("发送任务失败: %s", e)
        node_manager.complete_task(node_id, task_id)
        node_manager.decrement_task_count(node_id)
        response["message"] = str(e)
        response["status"] = "failed"
        return response
