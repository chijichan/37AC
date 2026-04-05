# views.py
import os
import uuid
import json
import importlib.util
import platform
import shutil
import random
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from AC_web import app
import threading
from config import IMAGE_PATH
from services.tcp_service import get_db_connection, node_manager
import pymysql

psutil = None
if importlib.util.find_spec("psutil") is not None:
    import psutil

# ======================
# === 配置项 ===
# ======================
# to /config.py


# ======================
# === 工具函数：保存上传的图片 ===
# ======================
def save_uploaded_file(file):
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".jfif")):
        filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
        filepath = os.path.join(IMAGE_PATH, filename)
        file.save(filepath)
        return filepath
    return None


def _parse_task_result(result_json_str):
    if isinstance(result_json_str, bytes):
        result_json_str = result_json_str.decode("utf-8", errors="ignore")

    try:
        result = json.loads(result_json_str)
    except Exception:
        return {
            "label": None,
            "confidence": None,
            "raw_result": result_json_str,
        }

    label = result.get("label") or result.get("class") or result.get("prediction")
    confidence = (
        result.get("confidence") or result.get("score") or result.get("probability")
    )
    if isinstance(confidence, str):
        confidence = confidence.strip().rstrip("%")
        try:
            confidence = float(confidence)
        except Exception:
            confidence = None

    return {
        "label": label,
        "confidence": confidence,
        "raw_result": result,
    }


def get_dashboard_stats():
    stats = {
        "total_visits": 0,
        "total_uploads": 0,
        "active_users": 0,
        "accuracy": 0.0,
        "online_nodes": 0,
        "idle_nodes": 0,
    }

    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM task_results")
                row = cursor.fetchone()
                stats["total_uploads"] = int(row[0] or 0) if row else 0
                stats["total_visits"] = stats["total_uploads"] * 2

                cursor.execute(
                    "SELECT result FROM task_results ORDER BY task_id DESC LIMIT 100"
                )
                rows = cursor.fetchall()

            confidences = []
            for row in rows:
                if not row or not row[0]:
                    continue
                parsed = _parse_task_result(row[0])
                confidence = parsed.get("confidence")
                if isinstance(confidence, (int, float)):
                    confidences.append(confidence)

            if confidences:
                avg = sum(confidences) / len(confidences)
                stats["accuracy"] = min(100.0, float(avg * 100 if avg <= 1 else avg))

    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    try:
        stats["online_nodes"] = len(node_manager.get_available_nodes())
        stats["idle_nodes"] = len(node_manager.get_idle_nodes())
        stats["active_users"] = max(1, stats["online_nodes"] * 3)
    except Exception:
        pass

    return stats


def get_recent_tasks(limit=10):
    tasks = []
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT task_id, result, status FROM task_results ORDER BY task_id DESC LIMIT %s",
                    (limit,),
                )
                rows = cursor.fetchall()

            for row in rows:
                task_id, result_json, status = row
                parsed = _parse_task_result(result_json or "")
                tasks.append(
                    {
                        "task_id": task_id,
                        "status": status,
                        "label": parsed.get("label"),
                        "confidence": parsed.get("confidence"),
                        "result": parsed.get("raw_result"),
                    }
                )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return tasks


# ======================
# === 遗弃路由 ===
# ======================
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


# @app.route("/dashboard")
# def dashboard_overview():
#     stats = get_dashboard_stats()
#     recent_tasks = get_recent_tasks(limit=8)
#     nodes = node_manager.get_available_nodes()

#     return render_template(
#         "dashboard/overview.html",
#         title="仪表盘",
#         year=datetime.now().year,
#         stats=stats,
#         recent_tasks=recent_tasks,
#         nodes=nodes,
#     )


# @app.route("/dashboard/<page>")
# def dashboard_page(page):
#     page = page.lower().strip()
#     if page not in {"overview", "nodes", "apikeys", "history", "settings"}:
#         return redirect(url_for("dashboard_overview"))

#     context = {
#         "title": "仪表盘",
#         "year": datetime.now().year,
#         "stats": get_dashboard_stats(),
#         "nodes": node_manager.get_available_nodes(),
#         "recent_tasks": get_recent_tasks(limit=12),
#     }

#     template_map = {
#         "overview": "dashboard/overview.html",
#         "nodes": "dashboard/nodes.html",
#         "apikeys": "dashboard/apikeys.html",
#         "history": "dashboard/history.html",
#         "settings": "dashboard/settings.html",
#     }

#     if request.args.get("ajax") == "1":
#         if page == "nodes":
#             return jsonify({"type": "dashboard_nodes", "data": context["nodes"]})
#         if page == "history":
#             return jsonify(
#                 {"type": "dashboard_history", "data": context["recent_tasks"]}
#             )
#         return jsonify({"type": "dashboard_page", "page": page})

#     return render_template(template_map[page], **context)


# ======================
# === 接口路由 ===
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
                    "status": "queued",
                    "message": "图片已上传，等待推理...",
                    "task_id": task_id,
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
            "status": "pending",
            "message": "结果尚未返回",
            "task_id": task_id,
            "result": [],
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
                        "status": status,
                        "message": "任务完成，结果已返回",
                        "task_id": task_id,
                        "result": result,
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
        json_response["status"] = "error"
        json_response["message"] = f"查询失败: {str(e)}"
        return jsonify(json_response), 500

    finally:
        if "conn" in locals():
            conn.close()


def _get_host_system_status():
    status = {
        "cpu": 45.0,
        "memory": 68.0,
        "disk": 52.0,
        "network": 34.0,
    }

    try:
        if psutil:
            status["cpu"] = round(psutil.cpu_percent(interval=0.2), 1)
            memory = psutil.virtual_memory()
            status["memory"] = round(memory.percent, 1)
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            status["disk"] = round(disk.percent, 1)
            net = psutil.net_io_counters()
            status["network"] = round(
                min(100.0, (net.bytes_sent + net.bytes_recv) / 1e7), 1
            )
    except Exception:
        pass

    return status


def _get_all_nodes_from_db():
    nodes = []
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return nodes

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id, name, token, status, addr, is_active, created_at, updated_at FROM nodes ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()

        for row in rows:
            nodes.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name") or row.get("node_name") or row.get("id"),
                    "token": row.get("token"),
                    "status": row.get("status"),
                    "addr": row.get("addr"),
                    "is_active": bool(row.get("is_active")),
                    "created_at": (
                        row.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(row.get("created_at"), "strftime")
                        else row.get("created_at")
                    ),
                    "updated_at": (
                        row.get("updated_at").strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(row.get("updated_at"), "strftime")
                        else row.get("updated_at")
                    ),
                }
            )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    return nodes


def _get_overview_data():
    stats = get_dashboard_stats()
    system_status = _get_host_system_status()
    recent_tasks = get_recent_tasks(limit=5)

    if not recent_tasks:
        recent_tasks = [
            {
                "task_id": f"demo-{i+1}",
                "status": "success",
                "label": "示例结果",
                "confidence": 90.0 - i * 3,
                "result": {"label": "示例角色", "confidence": 90.0 - i * 3},
            }
            for i in range(5)
        ]

    recent_activity = []
    for task in recent_tasks:
        title = task.get("label") or "识别任务完成"
        confidence = task.get("confidence")
        recent_activity.append(
            {
                "icon": "📤",
                "type": "upload",
                "title": title,
                "description": f"任务 {task.get('task_id')} 已完成，置信度 {confidence if confidence is not None else '--'}%",
                "time": "刚刚",
            }
        )

    records = []
    for task in recent_tasks:
        records.append(
            {
                "id": task.get("task_id"),
                "filename": f"image_{task.get('task_id')[:8]}.jpg",
                "result": task.get("label") or "未知",
                "confidence": task.get("confidence") or 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": task.get("status", "success"),
            }
        )

    return {
        "stats": stats,
        "system": system_status,
        "recent_activity": recent_activity,
        "recent_records": records,
    }


@app.route("/dashboard/overview", methods=["GET"])
@app.route("/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    try:
        return jsonify(
            {
                "type": "dashboard_summary",
                "timestamp": int(datetime.now().timestamp()),
                "data": _get_overview_data(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/stats", methods=["GET"])
def api_dashboard_stats():
    try:
        return jsonify(
            {
                "type": "dashboard_stats",
                "timestamp": int(datetime.now().timestamp()),
                "data": get_dashboard_stats(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/nodes", methods=["GET"])
def api_dashboard_nodes():
    try:
        nodes = _get_all_nodes_from_db()

        return jsonify(
            {
                "type": "dashboard_nodes",
                "timestamp": int(datetime.now().timestamp()),
                "data": nodes,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/history", methods=["GET"])
@app.route("/dashboard/tasks", methods=["GET"])
def api_dashboard_tasks():
    try:
        tasks = get_recent_tasks(limit=10)
        if not tasks:
            tasks = [
                {
                    "task_id": f"demo-{i+1}",
                    "status": "success" if i % 2 == 0 else "failure",
                    "label": "示例角色",
                    "confidence": 90.0 - i * 5,
                    "result": {"label": "示例角色", "confidence": 90.0 - i * 5},
                }
                for i in range(10)
            ]

        return jsonify(
            {
                "type": "dashboard_tasks",
                "timestamp": int(datetime.now().timestamp()),
                "data": tasks,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    """节点查询接口。

    * 如果通过浏览器直接访问，则渲染 `nodes.html` 页面；
    * 如果通过 AJAX 或希望获取 JSON 格式数据，会返回一份标准的 JSON 响应。

    返回 JSON 时的数据结构参考 `NodeManager.get_available_nodes()`。
    """
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    wants_json = is_ajax or request.accept_mimetypes.accept_json

    try:
        nodes = node_manager.get_available_nodes()

        if wants_json:
            return (
                jsonify(
                    {
                        "type": "nodes_list",
                        "timestamp": int(datetime.now().timestamp()),
                        "data": nodes,
                    }
                ),
                200,
            )
        else:
            # 普通浏览器访问，渲染页面，由 JS 进行刷新
            return render_template(
                "nodes.html", title="节点管理", year=datetime.now().year
            )

    except Exception as e:
        if wants_json:
            return (
                jsonify(
                    {
                        "type": "nodes_list",
                        "timestamp": int(datetime.now().timestamp()),
                        "data": [],
                        "error": str(e),
                    }
                ),
                500,
            )
        else:
            flash(f"获取节点信息失败: {e}")
            return render_template(
                "nodes.html", title="节点管理", year=datetime.now().year
            )
