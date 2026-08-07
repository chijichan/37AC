# routes/upload_routes.py
"""上传和任务查询路由"""

import uuid
import json
import threading
import os
from datetime import datetime
from pathlib import Path
from flask import (
    request,
    jsonify,
    Blueprint,
    Response,
)
from services.node_manager import get_db_connection, node_manager
from services.task_dispatcher import dispatch_task
from services.api_key_service import verify_api_key
from services.sse_bus import sse_bus
from services.task_manager import task_manager
from middleware.rate_limiter import rate_limit
from common.constants import ALLOWED_IMAGE_EXTENSIONS as _ALLOWED_IMAGE_EXTENSIONS
from config.log_config import get_logger

upload_bp = Blueprint("upload", __name__)
logger = get_logger("upload_routes")


def _safe_image_filename(filename):
    """清洗上传文件名，返回安全的文件名或 None。"""
    if not filename or not isinstance(filename, str):
        return None
    base = os.path.basename(filename)
    ext = Path(base).suffix.lower()
    name = Path(base).stem
    # 限制长度，防止日志/数据库异常
    name = name[:64]
    if ext in _ALLOWED_IMAGE_EXTENSIONS:
        return f"{name}{ext}"
    return None


def _detect_image_format(data):
    """通过文件魔数检测图片真实格式。"""
    if not data:
        return ""
    # PNG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    # JPEG
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    # WEBP
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def _require_api_key():
    """验证 API Key 中间件"""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return (
            None,
            jsonify(
                {
                    "success": False,
                    "message": "缺少 API Key，请在请求头中提供 X-API-Key",
                }
            ),
            401,
        )

    result = verify_api_key(api_key)
    if not result["success"]:
        return None, jsonify(result), 401

    return result["data"], None, None


@upload_bp.route("/upload", methods=["GET", "POST"])
@rate_limit
def upload_and_predict():
    if request.method == "POST":
        # 验证 API Key（从请求头获取）
        api_key_data, error_response, status_code = _require_api_key()
        if error_response:
            return error_response, status_code

        # 兼容 file / image 两种字段名（前端上传页使用 image，API 文档约定 file）
        uploaded_file = request.files.get("file") or request.files.get("image")
        if uploaded_file is None:
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        file = uploaded_file
        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        # 校验文件名与扩展名白名单
        safe_name = _safe_image_filename(file.filename)
        if not safe_name:
            return jsonify({"success": False, "message": "请上传 png/jpg/jpeg/webp 格式的图片"}), 400

        image_data = file.read()

        # 校验文件魔数（真实格式）
        detected_ext = _detect_image_format(image_data)
        if detected_ext not in (".png", ".jpg", ".jpeg", ".webp"):
            return jsonify({"success": False, "message": "文件内容不是有效的图片格式"}), 400

        image_filename = safe_name

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 从请求中获取识别方式（前端传入，默认 local）
        recognition_type = request.form.get("recognition_type", "local")
        if recognition_type not in ("local", "llm", "auto"):
            recognition_type = "local"

        # 判断客户端是否期望流式响应
        wants_stream = (
            request.accept_mimetypes.best == "text/event-stream"
            or request.headers.get("X-Stream-Response", "").lower() == "true"
        )

        # 定义分发函数（两种模式共用）
        def dispatch():
            result = dispatch_task(
                None,
                image_data,
                task_id,
                image_filename=image_filename,
                recognition_type=recognition_type,
            )
            logger.info("任务 %s 调度结果: %s", task_id, result)

            status = result.get("status")

            if status in ("failed", "error"):
                try:
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO task_results (task_id, result, status) "
                                "VALUES (%s, %s, %s) "
                                "ON DUPLICATE KEY UPDATE result=VALUES(result), status=VALUES(status)",
                                (task_id, json.dumps({"error": result.get("message", "分发失败")}),
                                 "failed"),
                            )
                            conn.commit()
                        sse_bus.publish(task_id, {
                            "status": "failed",
                            "message": result.get("message", "分发失败"),
                            "task_id": task_id,
                            "error": result.get("message", "分发失败"),
                            "result": [],
                        })
                except Exception as e:
                    logger.error("保存失败记录出错: %s", e)
                finally:
                    if conn:
                        conn.close()
                return

            if status == "waiting":
                # 任务进入等待队列，task_manager 会重试，推送等待通知
                # 携带 retry_in（预计重试秒数），供前端显示排队倒计时
                from services.task_manager import task_manager
                sse_bus.publish(task_id, {
                    "status": "waiting",
                    "message": "没有空闲节点，任务已进入等待队列，节点上线后自动分发",
                    "retry_in": result.get("retry_in") or task_manager.get_retry_interval(recognition_type),
                    "task_id": task_id,
                    "result": [],
                })
                # waiting 状态下 task_manager 已注册，无需更新 API Key
                return

            try:
                conn = get_db_connection()
                if conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE task_results SET user_id = %s, api_key_id = %s WHERE task_id = %s",
                            (api_key_data["user_id"], api_key_data["key_id"], task_id),
                        )
                        conn.commit()
            except Exception as e:
                logger.error("更新任务 API Key 记录失败: %s", e)
            finally:
                if conn:
                    conn.close()

        # === 流式响应模式：先订阅 SSE，再启动 dispatch 线程 ===
        if wants_stream:
            # 先订阅（确保 dispatch 线程 publish 时队列已就绪）
            q = sse_bus.subscribe(task_id)

            threading.Thread(target=dispatch, daemon=True).start()

            # SSE 等待超时按实际重试策略动态计算：
            # 重试间隔 × 最大重试次数 + 推理缓冲
            # 推理缓冲与 task_manager 决策一致：local 快路径 60s，llm 路径 180s
            retry_interval = task_manager.get_retry_interval(recognition_type)
            is_llm_path = (
                recognition_type == "llm"
                or (recognition_type == "auto" and node_manager.has_llm_enabled_nodes())
            )
            inference_buffer = 180 if is_llm_path else 60
            sse_timeout = retry_interval * 3 + inference_buffer

            def generate():
                # 先发一个 queued 事件
                yield f"data: {json.dumps({'status': 'queued', 'message': '任务已提交，等待推理...', 'task_id': task_id, 'recognition_type': recognition_type, 'timeout': sse_timeout}, ensure_ascii=False)}\n\n"

                try:
                    for event in sse_bus.iter_events(task_id, q, timeout=sse_timeout):
                        yield event
                finally:
                    sse_bus.unsubscribe(task_id, q)

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )

        # === 非流式模式：启动 dispatch 线程后返回 JSON ===
        threading.Thread(target=dispatch, daemon=True).start()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "type": "dispatch_task",
                    "timestamp": int(datetime.now().timestamp()),
                    "status": "queued",
                    "message": "图片已上传，等待推理...",
                    "task_id": task_id,
                    "recognition_type": recognition_type,
                }
            )

        return jsonify({
            "type": "dispatch_task",
            "timestamp": int(datetime.now().timestamp()),
            "status": "queued",
            "message": "图片已上传，等待推理...",
            "task_id": task_id,
            "recognition_type": recognition_type,
        })

    # GET 请求：返回 API 说明
    return jsonify({
        "type": "info",
        "message": "37AC 上传 API",
        "usage": {
            "method": "POST",
            "url": "/upload",
            "headers": {"X-API-Key": "your_api_key", "Accept": "text/event-stream"},
            "body": {"file": "image_file"},
            "streaming": "设置 Accept: text/event-stream 或 X-Stream-Response: true 获取流式响应",
        },
    }), 200


@upload_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task_result(task_id):
    json_response = {
        "type": "task_result",
        "timestamp": int(datetime.now().timestamp()),
        "status": "pending",
        "message": "结果尚未返回",
        "task_id": task_id,
        "result": [],
    }

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            json_response["status"] = "error"
            json_response["message"] = "数据库连接失败"
            return jsonify(json_response), 503

        with conn.cursor() as cursor:
            sql = "SELECT result, status FROM task_results WHERE task_id = %s"
            cursor.execute(sql, (task_id,))
            row = cursor.fetchone()

        conn.close()
        conn = None

        if row:
            result_json_str = row[0]
            status = row[1]

            try:
                result = json.loads(result_json_str)
            except json.JSONDecodeError:
                result = {"raw_result": result_json_str}

            return (
                jsonify(
                    {
                        "type": "task_result",
                        "timestamp": int(datetime.now().timestamp()),
                        "status": status,
                        "message": "任务完成，结果已返回",
                        "task_id": task_id,
                        "result": result,
                    }
                ),
                200,
            )

        else:
            return jsonify(json_response), 202

    except Exception as e:
        logger.error("查询任务结果失败: %s", e)
        json_response["status"] = "error"
        json_response["message"] = "查询任务结果失败"
        return jsonify(json_response), 500

    finally:
        if conn:
            conn.close()


@upload_bp.route("/tasks/<task_id>/stream", methods=["GET"])
def stream_task_result(task_id):
    """SSE 实时流端点 — 节点返回结果后即时推送到前端。"""
    def generate():
        q = sse_bus.subscribe(task_id)
        try:
            # 先检查是否已有结果
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT result, status FROM task_results WHERE task_id = %s",
                            (task_id,),
                        )
                        row = cursor.fetchone()
                    if row and row[1] and row[1] != "pending":
                        result = json.loads(row[0]) if row[0] else {}
                        error = result.get("error") if isinstance(result, dict) else None
                        yield f"data: {json.dumps({'status': 'completed', 'message': '任务已完成', 'task_id': task_id, 'result': result, 'error': error}, ensure_ascii=False)}\n\n"
                        return
                finally:
                    conn.close()

            # 阻塞等待 SSE 事件
            for event in sse_bus.iter_events(task_id, q, timeout=120):
                yield event
        finally:
            sse_bus.unsubscribe(task_id, q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Connection": "keep-alive",
        },
    )
