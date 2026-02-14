# views.py
import os
import uuid
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from AC_web import app
import threading

from tcp_server import get_db_connection

# ======================
# === 配置项 ===
# ======================
UPLOAD_FOLDER = 'uploads'  # 用户上传的图片存放位置
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ======================
# === 工具函数：保存上传的图片 ===
# ======================
def save_uploaded_file(file):
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return filepath
    return None

# ======================
# === 原有路由 ===
# ======================
# 即将弃用
@app.route('/')
@app.route('/home')
def home():
    return render_template('index.html', title='首页', year=datetime.now().year)

@app.route('/contact')
def contact():
    return render_template('contact.html', title='联系我们', year=datetime.now().year, message='')

@app.route('/about')
def about():
    return render_template('about.html', title='关于我们', year=datetime.now().year, message='')

# ======================
# === 上传与调度路由 ===
# ======================
@app.route('/upload', methods=['GET', 'POST'])
def upload_and_predict():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)

        image_data = file.read()
        file.seek(0)  # 如果后续还需要保存一份到磁盘，可以重置指针

        filepath = save_uploaded_file(file)
        if not filepath:
            flash('请上传 png/jpg/jpeg 格式的图片')
            return redirect(request.url)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 启动一个线程去分发任务（非阻塞）
        def dispatch():
            from tcp_server import dispatch_task
            result = dispatch_task(filepath, image_data, task_id)
            print(f"[调度结果] 任务 {task_id}: {result}")
            return jsonify({'status': 'waiting', 'task_id': task_id, 'error': '没有空闲节点'})

        threading.Thread(target=dispatch, daemon=True).start()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'queued', 'task_id': task_id, 'message': '图片已上传，等待推理...'})
        else:
            return render_template('upload.html', title='上传结果', year=datetime.now().year, task_id=task_id, status='queued')

    return render_template('upload.html', title='上传图片', year=datetime.now().year)

@app.route('/task-result/<task_id>', methods=['GET'])
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
                result = json.loads(result_json_str)  # 转为字典，如 {'label': '猫', 'confidence': 95.0}
            except json.JSONDecodeError:
                result = {'raw_result': result_json_str}  # 如果不是合法 JSON，原样返回字符串

            return jsonify({
                'status': 'success',
                'task_id': task_id,
                'result': result,          # 可能是字典或原始字符串
                'status': status            # 如 'completed'
            })

        else:
            return jsonify({
                'status': 'pending',
                'task_id': task_id,
                'message': '结果尚未返回'
            }), 202

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'查询失败: {e}'
        }), 500

    finally:
        if 'conn' in locals():
            conn.close()