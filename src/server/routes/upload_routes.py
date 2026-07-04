# routes/upload_routes.py
"""上传和任务查询路由"""

import uuid
import json
import threading
from datetime import datetime
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Blueprint,
    g,
    Response,
)
from services.node_manager import get_db_connection
from services.task_dispatcher import dispatch_task
from services.file_service import save_uploaded_file
from services.api_key_service import verify_api_key
from services.sse_bus import sse_bus
from middleware.auth_middleware import login_required

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
def upload_and_predict():
    if request.method == "POST":
        # 验证 API Key（从请求头获取）
        api_key_data, error_response, status_code = _require_api_key()
        if error_response:
            return error_response, status_code

        if "file" not in request.files:
            flash("没有选择文件")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("没有选择文件")
            return redirect(request.url)

        image_data = file.read()
        file.seek(0)

        filepath = save_uploaded_file(file)
        if not filepath:
            flash("请上传 png/jpg/jpeg 格式的图片")
            return redirect(request.url)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 启动一个线程去分发任务（非阻塞）
        def dispatch():
            result = dispatch_task(filepath, image_data, task_id)
            print(f"[调度结果] 任务 {task_id}: {result}")

            # 保存 API Key 使用记录到 task_results
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

        threading.Thread(target=dispatch, daemon=True).start()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "type": "dispatch_task",
                    "timestamp": int(datetime.now().timestamp()),
                    "status": "queued",
                    "message": "图片已上传，等待推理...",
                    "task_id": task_id,
                }
            )

    return render_template("upload.html", title="上传图片", year=datetime.now().year)


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
    """SSE 实时流端点 — 节点返回结果后即时推送到前端。

    前端用法（JavaScript）:
        const es = new EventSource("/tasks/<task_id>/stream");
        es.onmessage = (e) => { const data = JSON.parse(e.data); ... };
        es.onerror = () => { es.close(); /* 可回退到轮询 /tasks/<task_id> */ };
    """
    def generate():
        q = sse_bus.subscribe(task_id)
        try:
            # 先检查是否已有结果（竞态：结果在订阅前就已到达）
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
                        result = json.loads(row[0]) if row[0] else []
                        yield f"data: {json.dumps({'status': 'completed', 'message': '任务已完成', 'task_id': task_id, 'result': result}, ensure_ascii=False)}\n\n"
                        return
                finally:
                    conn.close()

            # 阻塞等待 SSE 事件（最长 60 秒）
            for event in sse_bus.iter_events(task_id, q, timeout=60):
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
