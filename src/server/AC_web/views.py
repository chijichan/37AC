# views.py
import os
import uuid
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from AC_web import app
import threading
from config import IMAGE_PATH
from services.tcp_service import get_db_connection

# ======================
# === 配置项 ===
# ======================
# to /config.py


# ======================
# === 工具函数：保存上传的图片 ===
# ======================
def save_uploaded_file(file):
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
        filepath = os.path.join(IMAGE_PATH, filename)
        file.save(filepath)
        return filepath
    return None


# ======================
# === 原有路由 ===
# ======================
# 即将弃用
# @app.route("/")
# @app.route("/home")
# def home():
#     return render_template("index.html", title="首页", year=datetime.now().year)


# @app.route("/contact")
# def contact():
#     return render_template(
#         "contact.html", title="联系我们", year=datetime.now().year, message=""
#     )


# @app.route("/about")
# def about():
#     return render_template(
#         "about.html", title="关于我们", year=datetime.now().year, message=""
#     )


# ======================
# === 上传与调度路由 ===
# ======================
@app.route("/upload", methods=["GET", "POST"])
def upload_and_predict():
    if request.method == "POST":
        if "file" not in request.files:
            flash("没有选择文件")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("没有选择文件")
            return redirect(request.url)

        image_data = file.read()
        file.seek(0)  # 如果后续还需要保存一份到磁盘，可以重置指针

        filepath = save_uploaded_file(file)
        if not filepath:
            flash("请上传 png/jpg/jpeg 格式的图片")
            return redirect(request.url)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 启动一个线程去分发任务（非阻塞）
        def dispatch():
            from services.tcp_service import dispatch_task

            result = dispatch_task(filepath, image_data, task_id)
            print(f"[调度结果] 任务 {task_id}: {result}")

        threading.Thread(target=dispatch, daemon=True).start()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "type": "dispatch_task",
                    "timestamp": int(datetime.now().timestamp()),
                    "data": {
                        "status": "queued",
                        "task_id": task_id,
                        "message": "图片已上传，等待推理...",
                    },
                }
            )

    return render_template("upload.html", title="上传图片", year=datetime.now().year)


@app.route("/tasks/<task_id>", methods=["GET"])
def get_task_result(task_id):
    try:
        conn = get_db_connection()
        json_response = {
            "type": "task_result",
            "timestamp": int(datetime.now().timestamp()),
            "data": {
                "status": "pending",
                "task_id": task_id,
                "result": [],
                "message": "结果尚未返回",
            },
        }

        with conn.cursor() as cursor:
            sql = "SELECT result, status FROM task_results WHERE task_id = %s"
            cursor.execute(sql, (task_id,))
            row = cursor.fetchone()  # 返回的是元组 (result, status)

        if row:
            result_json_str = row[0]  # result 是 JSON 格式的字符串
            status = row[1]

            try:
                result = json.loads(
                    result_json_str
                )  # 转为字典，如 {'label': '猫', 'confidence': 95.0}
            except json.JSONDecodeError:
                result = {
                    "raw_result": result_json_str
                }  # 如果不是合法 JSON，原样返回字符串

            return (
                jsonify(
                    {
                        "type": "task_result",
                        "timestamp": int(datetime.now().timestamp()),
                        "data": {
                            "status": status,
                            "task_id": task_id,
                            "result": result,
                            "message": "任务完成，结果已返回",
                        },
                    }
                ),
                200,
            )

        else:
            return (
                jsonify(json_response),
                202,
            )

    except Exception as e:
        json_response["data"]["status"] = "error"
        json_response["data"]["message"] = f"查询失败: {str(e)}"
        return jsonify(json_response), 500

    finally:
        if "conn" in locals():
            conn.close()
