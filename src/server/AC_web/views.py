# views.py
import os
import uuid
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from AC_web import app
import threading
from config import *
from services.tcp_service import get_db_connection, node_manager

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
@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html", title="首页", year=datetime.now().year)


@app.route("/contact")
def contact():
    return render_template(
        "contact.html", title="联系我们", year=datetime.now().year, message=""
    )


@app.route("/about")
def about():
    return render_template(
        "about.html", title="关于我们", year=datetime.now().year, message=""
    )


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
            # return jsonify(
            #     {"status": "waiting", "task_id": task_id, "error": "没有空闲节点"}
            # )

        threading.Thread(target=dispatch, daemon=True).start()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "status": "queued",
                    "task_id": task_id,
                    "message": "图片已上传，等待推理...",
                }
            )

    return render_template("upload.html", title="上传图片", year=datetime.now().year)


@app.route("/task-result/<task_id>", methods=["GET"])
def get_task_result(task_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT result, status FROM task_results WHERE task_id = %s"
            cursor.execute(sql, (task_id,))
            row = cursor.fetchone()  # 返回的是元组 (result, status)

        if row:
            # ✅ 用索引访问元组：row[0] 是 result，row[1] 是 status
            result_json_str = row[0]  # result 是 JSON 格式的字符串
            status = row[1]

            # 如果 result 是 JSON 字符串，可以反序列化为 Python 字典（可选）
            try:
                result = json.loads(
                    result_json_str
                )  # 转为字典，如 {'label': '猫', 'confidence': 95.0}
            except json.JSONDecodeError:
                result = {
                    "raw_result": result_json_str
                }  # 如果不是合法 JSON，原样返回字符串

            return jsonify(
                {
                    "status": "success",
                    "task_id": task_id,
                    "result": result,  # 可能是字典或原始字符串
                    "status": status,  # 如 'completed'
                }
            )

        else:
            return (
                jsonify(
                    {"status": "pending", "task_id": task_id, "message": "结果尚未返回"}
                ),
                202,
            )

    except Exception as e:
        return jsonify({"status": "error", "message": f"查询失败: {e}"}), 500

    finally:
        if "conn" in locals():
            conn.close()


@app.route("/node/get-nodes", methods=["GET"])
def node_info():
    try:
        # 从节点管理器获取实时节点信息
        nodes_info = []

        # 获取节点管理器的锁来确保线程安全
        with node_manager.lock:
            for node_id, node_data in node_manager.nodes.items():
                nodes_info.append(
                    {
                        "node_id": node_id,
                        "status": node_data.get("status", "unknown"),
                        "last_heartbeat": node_data.get("last_heartbeat", 0),
                        "addr": f"{node_data.get('addr', ('Unknown', 0))[0]}:{node_data.get('addr', ('Unknown', 0))[1]}",
                        "has_socket": node_data.get("socket") is not None,
                    }
                )

        # 按节点状态分类统计
        idle_nodes = [node for node in nodes_info if node["status"] == "idle"]
        busy_nodes = [node for node in nodes_info if node["status"] == "busy"]

        return jsonify(
            {
                "status": "success",
                "summary": {
                    "total_nodes": len(nodes_info),
                    "idle_nodes": len(idle_nodes),
                    "busy_nodes": len(busy_nodes),
                    "online_nodes": len(idle_nodes) + len(busy_nodes),
                },
                "nodes": nodes_info,
                "idle_nodes_list": [
                    node["node_id"] for node in idle_nodes
                ],  # 专门返回空闲节点ID列表
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": f"查询失败: {e}"}), 500


# 另外添加一个专门获取空闲节点ID的接口
@app.route("/node/get-idle-nodes", methods=["GET"])
def get_idle_nodes():
    """专门获取当前可用的空闲节点ID列表"""
    try:
        idle_nodes = []

        with node_manager.lock:
            for node_id, node_data in node_manager.nodes.items():
                # 检查节点是否为空闲状态且在线
                if (
                    node_data.get("status") == "idle"
                    and node_data.get("socket") is not None
                ):

                    idle_nodes.append(
                        {
                            "node_id": node_id,
                            "addr": f"{node_data.get('addr', ('Unknown', 0))[0]}:{node_data.get('addr', ('Unknown', 0))[1]}",
                            "last_heartbeat": node_data.get("last_heartbeat", 0),
                        }
                    )

        return jsonify(
            {"status": "success", "count": len(idle_nodes), "idle_nodes": idle_nodes}
        )

    except Exception as e:
        return jsonify({"status": "error", "message": f"查询失败: {e}"}), 500


# 添加节点状态详情接口
@app.route("/node/status", methods=["GET"])
def node_status():
    """获取详细的节点状态信息"""
    try:
        with node_manager.lock:
            total_nodes = len(node_manager.nodes)
            idle_count = sum(
                1
                for node in node_manager.nodes.values()
                if node.get("status") == "idle" and node.get("socket") is not None
            )
            busy_count = sum(
                1
                for node in node_manager.nodes.values()
                if node.get("status") == "busy" and node.get("socket") is not None
            )

            return jsonify(
                {
                    "status": "success",
                    "total_nodes": total_nodes,
                    "idle_nodes": idle_count,
                    "busy_nodes": busy_count,
                    "available_nodes": idle_count,
                }
            )

    except Exception as e:
        return jsonify({"status": "error", "message": f"查询失败: {e}"}), 500
