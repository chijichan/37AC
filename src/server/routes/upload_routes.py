# routes/upload_routes.py
"""上传和任务查询路由"""

import base64
import random
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
from services import settings_service
from services import storage_service
from services import channel_service
from config.base import HUMAN_VOTE_LIMIT_PER_HOUR
from middleware.rate_limiter import rate_limit
from middleware.auth_middleware import _extract_token, _verify_access_token
from utils.api_response import (
    CODE_API_KEY_INVALID,
    CODE_API_KEY_MISSING,
    CODE_DB_UNAVAILABLE,
    CODE_IMAGE_EXPIRED,
    CODE_INVALID_PARAMS,
    CODE_NOT_FOUND,
    CODE_RATE_LIMITED,
)
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


def _decode_base64_image(b64):
    """从 base64 字符串解码图片二进制，返回 (bytes, ext)。

    兼容带 data URL 前缀的写法，如：
      data:image/png;base64,xxxx
      image_base64=xxxx
    """
    if not b64:
        return None, ""
    b64 = str(b64).strip()
    ext = ""
    payload = b64
    if "," in b64 and b64.split(",", 1)[0].startswith("data:"):
        prefix, payload = b64.split(",", 1)
        mime = prefix.split(";")[0].split(":", 1)[-1]
        if "png" in mime:
            ext = ".png"
        elif "jpeg" in mime or "jpg" in mime:
            ext = ".jpg"
        elif "webp" in mime:
            ext = ".webp"
    try:
        data = base64.b64decode(payload, validate=False)
    except Exception:
        return None, ""
    if not data:
        return None, ""
    return data, ext


def _require_api_key():
    """验证 API Key 中间件"""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return (
            None,
            jsonify(
                {
                    "success": False,
                    "code": CODE_API_KEY_MISSING,
                    "message": "缺少 API Key，请在请求头中提供 X-API-Key",
                }
            ),
            401,
        )

    result = verify_api_key(api_key)
    if not result["success"]:
        result.setdefault("code", CODE_API_KEY_INVALID)
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

        # 识别通道（2026-09-25）：channels=37ac,llm,human；未给则按旧 model 参数推导
        model = (request.form.get("model") or "").strip().lower()
        channels_raw = (request.form.get("channels") or "").strip()
        body_json = request.get_json(silent=True) or {} if request.is_json else {}
        model = (body_json.get("model") or model or "").strip().lower()
        channels_raw = str(body_json.get("channels") or channels_raw or "").strip()
        if model not in ("37ac", "llm", "auto"):
            model = "37ac"

        channels = channel_service.parse_channels(channels_raw, model)

        # 人工通道：上传时内联提交（human_name），或稍后由 POST /upload/human 匿名补投
        human_name = str(
            request.form.get("human_name") or body_json.get("human_name") or body_json.get("human") or ""
        ).strip()
        human_index = request.form.get("human_character_index", body_json.get("human_character_index"))
        human_note = request.form.get("human_note") or body_json.get("human_note")
        if human_name and "human" not in channels:
            channels.append("human")

        node_channels = channel_service.node_channels(channels)

        # auto：按系统设置 auto_split_ratio 分流（默认 55% 37ac / 45% llm）
        # 无启用 LLM 的在线节点时全走 37ac
        if "auto" in channels:
            try:
                split_ratio = int(settings_service.get_settings().get("auto_split_ratio", "55"))
            except Exception:
                split_ratio = 55
            split_ratio = max(0, min(100, split_ratio))
            if node_manager.has_llm_enabled_nodes() and random.random() * 100 >= split_ratio:
                recognition_type = "llm"
            else:
                recognition_type = "local"
        elif node_channels:
            # 多通道时以第一个节点通道为准（每个通道会各自 dispatch 一次）
            recognition_type = channel_service.CHANNEL_TO_RECOGNITION.get(node_channels[0], "local")
        else:
            recognition_type = "local"

        # 图片来源：优先 multipart 文件（file / image），其次 image_base64
        image_data = None
        image_filename = None
        detected_ext = ""
        uploaded_file = request.files.get("file") or request.files.get("image")

        if uploaded_file is not None:
            file = uploaded_file
            if file.filename == "":
                return jsonify({"success": False, "message": "没有选择文件"}), 400

            # 校验文件名与扩展名白名单
            safe_name = _safe_image_filename(file.filename)
            if not safe_name:
                return jsonify({"success": False, "message": "请上传 png/jpg/jpeg/webp 格式的图片"}), 400

            image_data = file.read()
            detected_ext = _detect_image_format(image_data)
            if detected_ext not in (".png", ".jpg", ".jpeg", ".webp"):
                return jsonify({"success": False, "message": "文件内容不是有效的图片格式"}), 400
            image_filename = safe_name
        else:
            # base64：兼容 JSON 体或表单字段 image_base64
            if request.is_json:
                body = request.get_json(silent=True) or {}
            else:
                body = {}
            b64 = request.form.get("image_base64") or body.get("image_base64") or ""
            image_data, detected_ext = _decode_base64_image(b64)
            if not image_data or detected_ext not in (".png", ".jpg", ".jpeg", ".webp"):
                return jsonify({
                    "success": False,
                    "message": "缺少图片：请上传文件（file/image）或提供 image_base64",
                }), 400
            image_filename = f"base64_upload_{uuid.uuid4().hex[:8]}{detected_ext}"

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 服务端留存（需求3）：tmp 存原图、cache 存压缩副本；
        # 节点那一份由 dispatch_task 里的 base64 下发（同一份数据，两处落地）
        try:
            storage_service.save_temp(task_id, image_data, detected_ext)
            storage_service.save_cache(task_id, image_data, detected_ext)
        except Exception as e:
            logger.warning("保存上传图片失败 task_id=%s: %s", task_id, e)

        # 结果骨架：result 里按通道分段（37ac / llm / human）
        initial_payload = channel_service.initial_result(task_id, channels)
        if human_name:
            channel_service.add_human_vote(
                initial_payload,
                channel_service.human_entry(
                    human_name, character_index=human_index, note=human_note, source="upload",
                    voter=f"api:{api_key_data['key_id']}",
                ),
                voter_key=f"api:{api_key_data['key_id']}",
            )

        # 判断客户端是否期望流式响应
        wants_stream = (
            request.accept_mimetypes.best == "text/event-stream"
            or request.headers.get("X-Stream-Response", "").lower() == "true"
        )

        # 定义分发函数（两种模式共用）
        def dispatch():
            # 先写入任务归属，确保 waiting/failed 也记录到对应用户/API Key
            conn = None
            try:
                conn = get_db_connection()
                if conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO task_results (task_id, user_id, api_key_id, status, result) "
                            "VALUES (%s, %s, %s, 'pending', %s) "
                            "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), api_key_id=VALUES(api_key_id), status='pending'",
                            (task_id, api_key_data["user_id"], api_key_data["key_id"],
                             json.dumps(initial_payload, ensure_ascii=False)),
                        )
                        conn.commit()
            except Exception as e:
                logger.error("初始化任务归属失败: %s", e)
            finally:
                if conn:
                    conn.close()

            # 多通道扇出：每个需要节点推理的通道各发一次（多通道时用 "<父id>:<通道>" 作子任务 id）
            dispatched = []
            for channel in node_channels:
                sub_id = channel_service.sub_task_id(task_id, channel, len(node_channels))
                channel_recognition = channel_service.CHANNEL_TO_RECOGNITION.get(channel, recognition_type)
                res = dispatch_task(
                    None,
                    image_data,
                    sub_id,
                    image_filename=image_filename,
                    recognition_type=channel_recognition,
                )
                dispatched.append((channel, res))
                logger.info("任务 %s 通道 %s 调度结果: %s", task_id, channel, res)

            if not dispatched:
                # 只请求了人工通道：等标注即可，任务行已就绪
                logger.info("任务 %s 仅请求人工通道，等待标注", task_id)
                return

            failed = [(ch, res) for ch, res in dispatched if res.get("status") in ("failed", "error")]
            waiting = [ch for ch, res in dispatched if res.get("status") == "waiting"]
            for channel, res in failed:
                section = initial_payload.setdefault(channel, {})
                section["status"] = "failed"
                section["error"] = res.get("message") or "分发失败"
            if failed or waiting:
                _patch_result_row(task_id, initial_payload,
                                  channel_service.overall_status(initial_payload))

            result = dispatched[0][1]
            status = "failed" if len(failed) == len(dispatched) else (
                "waiting" if len(waiting) == len(dispatched) else "dispatched"
            )

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
            is_llm_path = recognition_type == "llm"
            inference_buffer = 180 if is_llm_path else 60
            sse_timeout = retry_interval * 3 + inference_buffer

            def generate():
                # 先发一个 queued 事件
                yield f"data: {json.dumps({'status': 'queued', 'message': '任务已提交，等待推理...', 'task_id': task_id, 'model': model, 'timeout': sse_timeout}, ensure_ascii=False)}\n\n"

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
        response_payload = {
            "type": "dispatch_task",
            "timestamp": int(datetime.now().timestamp()),
            "status": "queued",
            "message": "图片已上传，等待推理...",
            "task_id": task_id,
            "model": model,
            # 新增：本次请求的通道与各通道初始状态（前端按通道分区展示）
            "channels": channels,
            "channel_status": {
                channel: (initial_payload.get(channel) or {}).get("status", "queued")
                for channel in channels
            },
        }
        return jsonify(response_payload)

    # GET 请求：返回 API 说明
    return jsonify({
        "type": "info",
        "message": "37AC 上传 API",
        "usage": {
            "method": "POST",
            "url": "/upload",
            "headers": {"X-API-Key": "your_api_key", "Accept": "text/event-stream"},
            "body": {
                "file": "image_file (multipart)",
                "image_base64": "可选，JSON/表单里的 base64 图片（multipart 优先）",
                "model": "37ac | llm | auto（旧参数，等价单通道）",
                "channels": "可选，多通道逗号分隔：37ac,llm,human（不给则按 model 推导）",
                "human_name": "可选，上传时内联提交人工答案（会自动加入 human 通道）",
                "human_character_index": "可选，人工答案对应的人物序号（对应 37ac 结果的 characters[i]）",
                "human_note": "可选备注",
            },
            "channels": "结果按通道分段存放在 result 里：result['37ac'] / result['llm'] / result['human']；顶层仍保留旧字段（37ac 优先，其次 llm）",
            "human_endpoint": "POST /upload/human —— 匿名提交/修改人工标注（{task_id, name, character_index?}，按 IP 限流，同 IP 同任务重复提交=改票）",
            "result_endpoint": "GET /tasks/<task_id>（含 channel_status 与各通道结果）",
            "models_endpoint": "GET /models（无鉴权，拉取可选识别模型）",
            "streaming": "设置 Accept: text/event-stream 或 X-Stream-Response: true 获取流式响应",
        },
    }), 200


@upload_bp.route("/upload/human", methods=["POST"])
def submit_human_label():
    """人工识别通道：提交/修改某张图的人工标注（匿名可用，按 IP 限流）。

    请求体（JSON 或表单）：{task_id, name, character_index?, note?}
    规则：同一 IP 对同一 task 重复提交视为**改票**；每 IP 每小时上限见 HUMAN_VOTE_LIMIT_PER_HOUR。
    结果写入 result["human"]，前端与 37ac / llm 分区展示。
    """
    data = request.get_json(silent=True) or request.form or {}
    task_id = str(data.get("task_id") or "").strip()
    name = str(data.get("name") or data.get("human_name") or "").strip()
    if not task_id or not name:
        return jsonify({
            "success": False,
            "code": CODE_INVALID_PARAMS,
            "message": "缺少 task_id 或 name",
        }), 400

    ip = _client_ip()
    if not channel_service.vote_allowed(ip, HUMAN_VOTE_LIMIT_PER_HOUR):
        return jsonify({
            "success": False,
            "code": CODE_RATE_LIMITED,
            "message": f"提交过于频繁（每 IP 每小时 {HUMAN_VOTE_LIMIT_PER_HOUR} 次）",
        }), 429

    payload = _load_result_payload(task_id)
    if payload is None:
        return jsonify({
            "success": False,
            "code": CODE_NOT_FOUND,
            "message": "任务不存在或已被清理",
        }), 404

    channel_service.add_human_vote(
        payload,
        channel_service.human_entry(
            name,
            character_index=data.get("character_index"),
            note=data.get("note"),
            source="human",
            voter=f"ip:{ip}",
        ),
        voter_key=f"ip:{ip}",
    )
    channels = list(dict.fromkeys((payload.get("requested_channels") or []) + [channel_service.CHANNEL_HUMAN]))
    payload["requested_channels"] = channels
    channel_service.resolve_human_bbox(payload)

    status = channel_service.overall_status(payload)
    _patch_result_row(task_id, payload, status)
    channel_status = {c: channel_service.channel_status(payload, c) for c in channels}
    sse_bus.publish(task_id, {
        "status": "human_submitted",
        "message": "收到人工标注",
        "task_id": task_id,
        "human": payload.get(channel_service.CHANNEL_HUMAN),
        "channel_status": channel_status,
        "result": payload.get("characters") or [],
    })

    return jsonify({
        "success": True,
        "message": "标注已记录",
        "data": {
            "task_id": task_id,
            "status": status,
            "human": payload.get(channel_service.CHANNEL_HUMAN),
            "channel_status": channel_status,
        },
    }), 200


def _patch_result_row(task_id, payload, status):
    """把 result JSON 与状态写回任务行（多通道合并、人工投票都用它）。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO task_results (task_id, result, status) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE result=VALUES(result), status=VALUES(status)",
                (task_id, json.dumps(payload or {}, ensure_ascii=False), status or "pending"),
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error("更新任务结果失败 task_id=%s: %s", task_id, e)
        return False
    finally:
        if conn:
            conn.close()


def _load_result_payload(task_id):
    """读取任务的 result JSON（不存在返回 None，解析失败返回 {}）。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        with conn.cursor() as cursor:
            cursor.execute("SELECT result FROM task_results WHERE task_id = %s", (task_id,))
            row = cursor.fetchone()
        if not row:
            return None
        raw = row[0]
        if not raw:
            return {}
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}
    except Exception as e:
        logger.error("读取任务结果失败 task_id=%s: %s", task_id, e)
        return None
    finally:
        if conn:
            conn.close()


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _image_info(task_id):
    """任务图片的可取性信息（只加字段，旧客户端无感）。"""
    url = f"/tasks/{task_id}/image"
    try:
        path, source = storage_service.find_image(task_id)
    except Exception as e:
        logger.debug("查询任务图片失败 %s: %s", task_id, e)
        return {"available": False, "url": url}
    if not path:
        return {"available": False, "url": url}
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    return {
        "available": True,
        "url": url,
        "source": source,
        "ext": path.suffix,
        "bytes": size,
    }


def _task_node_id(task_id):
    """查询该任务是由哪个节点完成的（补拉用）。列不存在/查库失败都返回 None。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        with conn.cursor() as cursor:
            cursor.execute("SELECT node_id FROM task_results WHERE task_id = %s", (task_id,))
            row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.debug("查询任务节点失败 task_id=%s: %s", task_id, e)
        return None
    finally:
        if conn:
            conn.close()


def _try_refetch(task_id) -> bool:
    """本地图片已被回收时，向处理该任务的节点补拉一份（需求3 后半）。

    补拉成功后写回 tmp/cache，后续请求直接命中本地。
    """
    from services import image_refetch

    if not image_refetch.enabled():
        return False

    node_id = _task_node_id(task_id)
    result = image_refetch.request_from_node(node_id, task_id)
    if not result.get("success"):
        logger.info("补拉图片失败 task_id=%s: %s", task_id, result.get("message"))
        return False

    data = result["data"]["bytes"]
    ext = storage_service.safe_ext(result["data"].get("filename"))
    storage_service.save_cache(task_id, data, ext)
    storage_service.save_temp(task_id, data, ext)
    return True


def _image_expired_response(task_id):
    """图片已被回收（或从未落盘）：410 + 元数据，前端可显示占位。"""
    return jsonify({
        "success": False,
        "code": CODE_IMAGE_EXPIRED,
        "message": "图片已过期或不存在（服务端已回收临时文件）",
        "task_id": task_id,
        "image": {"available": False, "url": f"/tasks/{task_id}/image"},
    }), 410


def _require_image_auth():
    """取图鉴权：X-API-Key（与 /tasks 一致）或 Bearer JWT（前端用）。返回 (error_response, status)。"""
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        result = verify_api_key(api_key)
        if result.get("success"):
            return None, None
        result.setdefault("code", CODE_API_KEY_INVALID)
        return jsonify(result), 401

    token = _extract_token()
    if token:
        payload, error, status = _verify_access_token(token)
        if payload:
            return None, None
        return jsonify(error or {"success": False, "message": "令牌无效"}), status or 401

    return jsonify({
        "success": False,
        "code": CODE_API_KEY_MISSING,
        "message": "缺少凭证：请提供 X-API-Key 请求头或 Bearer 令牌",
    }), 401


@upload_bp.route("/tasks/<task_id>/image", methods=["GET"])
def get_task_image(task_id):
    """获取任务图片（需求4）。

    - 默认返回 cache 里的留存副本；?original=1 优先返回 tmp 里的原图
    - ?max_side=N 服务端即时缩放（不落盘）
    - 图片已被回收 -> 410 + IMAGE_EXPIRED（前端据此显示占位）
    """
    error_response, status_code = _require_image_auth()
    if error_response:
        return error_response, status_code

    prefer = "tmp" if str(request.args.get("original", "")).lower() in ("1", "true", "yes") else "cache"
    max_side = request.args.get("max_side", type=int)
    if max_side is not None:
        max_side = max(16, min(4096, max_side))

    data, source, mimetype = storage_service.read_bytes(task_id, prefer=prefer, max_side=max_side)
    if not data and _try_refetch(task_id):
        # 补拉成功：已写回本地，重新按原参数读取（含 max_side 缩放）
        data, source, mimetype = storage_service.read_bytes(task_id, prefer=prefer, max_side=max_side)
    if not data:
        return _image_expired_response(task_id)

    response = Response(data, mimetype=mimetype)
    response.headers["X-Image-Source"] = source
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["Content-Length"] = str(len(data))
    return response


@upload_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task_result(task_id):
    _api_key_data, error_response, status_code = _require_api_key()
    if error_response:
        return error_response, status_code

    json_response = {
        "type": "task_result",
        "timestamp": int(datetime.now().timestamp()),
        "status": "pending",
        "message": "结果尚未返回",
        "task_id": task_id,
        "result": [],
        "image": _image_info(task_id),
    }

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            json_response["status"] = "error"
            json_response["code"] = CODE_DB_UNAVAILABLE
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

            # 多通道：补全人工标注的框（只给了 character_index 时从模型通道取），并给出各通道状态
            requested = []
            channel_status = {}
            if isinstance(result, dict):
                requested = result.get("requested_channels") or []
                if requested:
                    channel_service.resolve_human_bbox(result)
                    channel_status = {
                        channel: channel_service.channel_status(result, channel)
                        for channel in requested
                    }

            return (
                jsonify(
                    {
                        "type": "task_result",
                        "timestamp": int(datetime.now().timestamp()),
                        "status": status,
                        "message": "任务完成，结果已返回",
                        "task_id": task_id,
                        "result": result,
                        "channels_requested": requested,
                        "channel_status": channel_status,
                        "image": _image_info(task_id),
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
    _api_key_data, error_response, status_code = _require_api_key()
    if error_response:
        return error_response, status_code

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
