# routes/upload_routes.py
"""上传和任务查询路由"""

import uuid
import json
import threading
from datetime import datetime
from flask import (
    request,
    jsonify,
    Blueprint,
    Response,
)
from services.node_manager import get_db_connection
from services.task_dispatcher import dispatch_task
from services.api_key_service import verify_api_key
from services.sse_bus import sse_bus
from middleware.rate_limiter import rate_limit

upload_bp = Blueprint("upload", __name__)


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

        if "file" not in request.files:
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".jfif")):
            return jsonify({"success": False, "message": "请上传 png/jpg/jpeg 格式的图片"}), 400

        image_data = file.read()
        image_filename = file.filename or f"{uuid.uuid4()}.jpg"

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
            print(f"[调度结果] 任务 {task_id}: {result}")

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
                    print(f"[调度结果] 保存失败记录出错: {e}")
                finally:
                    if conn:
                        conn.close()
                return

            if status == "waiting":
                # 任务进入等待队列，task_manager 会重试，推送等待通知
                sse_bus.publish(task_id, {
                    "status": "waiting",
                    "message": "没有空闲节点，任务已进入等待队列，节点上线后自动分发",
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
                print(f"[API Key] 更新任务记录失败: {e}")
            finally:
                if conn:
                    conn.close()

        # === 流式响应模式：先订阅 SSE，再启动 dispatch 线程 ===
        if wants_stream:
            # 先订阅（确保 dispatch 线程 publish 时队列已就绪）
            q = sse_bus.subscribe(task_id)

            threading.Thread(target=dispatch, daemon=True).start()

            def generate():
                # 先发一个 queued 事件
                yield f"data: {json.dumps({'status': 'queued', 'message': '任务已提交，等待推理...', 'task_id': task_id, 'recognition_type': recognition_type}, ensure_ascii=False)}\n\n"

                try:
                    for event in sse_bus.iter_events(task_id, q, timeout=120):
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
        json_response["status"] = "error"
        json_response["message"] = f"查询失败: {str(e)}"
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
