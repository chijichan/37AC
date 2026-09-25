# services/image_refetch.py
"""图片补拉（需求3 后半）。

服务端临时文件被回收后，前端仍可能来取图；此时向**处理过该任务的节点**要一份原图：

    GET /tasks/<id>/image 本地未命中
        -> request_from_node(node_id, task_id)
             TCP 发 image_request {request_id, task_id}
             <- 节点回 image_response {request_id, task_id, image_data(base64), image_size, ...}
        超时 / 节点离线 / 节点也已清理 -> {"success": False, "message": ...}

开关：IMAGE_NODE_REFETCH（默认 true）。节点侧保留时长由 IMAGE_RETAIN_SEC 决定（默认 900s）。
"""

import base64
import threading
import time
import uuid

from config.base import IMAGE_NODE_REFETCH
from config.log_config import get_logger
from services.node_manager import node_manager
from services.protocol.json_protocol import json_protocol

logger = get_logger("image_refetch")

DEFAULT_TIMEOUT = 8.0
_MAX_PENDING = 64

_lock = threading.Lock()
_pending = {}          # request_id -> {"event": Event, "payload": dict|None}


def enabled() -> bool:
    """补拉是否启用（.env 的 IMAGE_NODE_REFETCH）。"""
    return bool(IMAGE_NODE_REFETCH)


def resolve(request_id, payload) -> bool:
    """收到 image_response 时由 message_handlers 调用，唤醒等待方。"""
    with _lock:
        entry = _pending.get(request_id)
    if not entry:
        logger.warning("收到未知的 image_response: request_id=%s", request_id)
        return False
    entry["payload"] = payload
    entry["event"].set()
    return True


def _node_socket(node_id):
    try:
        info = node_manager.nodes.get(node_id) or {}
        return info.get("socket")
    except Exception:
        return None


def request_from_node(node_id, task_id, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """向节点补拉图片。

    Returns:
        {"success": True, "data": {"bytes": b"...", "filename": "..."}}
        或 {"success": False, "message": "..."}
    """
    if not enabled():
        return {"success": False, "message": "补拉未启用（IMAGE_NODE_REFETCH=false）"}
    if not node_id:
        return {"success": False, "message": "不知道该任务由哪个节点处理"}

    socket_obj = _node_socket(node_id)
    if socket_obj is None:
        return {"success": False, "message": "节点不在线，无法补拉"}

    request_id = uuid.uuid4().hex
    entry = {"event": threading.Event(), "payload": None}
    with _lock:
        if len(_pending) >= _MAX_PENDING:
            return {"success": False, "message": "补拉请求过多，请稍后再试"}
        _pending[request_id] = entry

    try:
        sent = json_protocol.send_json(socket_obj, {
            "type": "image_request",
            "timestamp": int(time.time()),
            "data": {"request_id": request_id, "task_id": task_id},
        })
        if not sent:
            return {"success": False, "message": "补拉请求发送失败"}

        if not entry["event"].wait(max(1.0, float(timeout))):
            return {"success": False, "message": "节点响应超时"}
        payload = entry["payload"] or {}
    except Exception as e:
        logger.error("补拉请求异常 task_id=%s: %s", task_id, e)
        return {"success": False, "message": f"补拉请求异常: {e}"}
    finally:
        with _lock:
            _pending.pop(request_id, None)

    if payload.get("error"):
        return {"success": False, "message": str(payload["error"])}

    raw = payload.get("image_data")
    if not raw:
        return {"success": False, "message": "节点未返回图片数据"}
    try:
        data = base64.b64decode(raw)
    except Exception as e:
        return {"success": False, "message": f"图片解码失败: {e}"}

    size = payload.get("image_size")
    if size and int(size) != len(data):
        logger.warning("补拉图片大小不一致: 声明=%s 实际=%s", size, len(data))

    logger.info("补拉成功: task_id=%s, %d 字节, 节点=%s", task_id, len(data), node_id)
    return {
        "success": True,
        "data": {"bytes": data, "filename": payload.get("image_filename") or f"{task_id}.jpg"},
    }


def pending_count() -> int:
    with _lock:
        return len(_pending)
