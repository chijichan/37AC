# routes/model_routes.py
"""识别模型管理路由（泛化 models 管理）

- GET    /models              公开：拉取可选识别模型（激活模型 + llm + auto）
- GET    /models/admin        管理员：全部模型记录
- POST   /models              管理员：新增模型
- PUT    /models/<id>         管理员：编辑模型
- DELETE /models/<id>         管理员：删除模型
- POST   /models/<id>/activate 管理员：激活模型
"""

from flask import Blueprint, request, jsonify

from middleware.auth_middleware import admin_required
from services import model_manager
from services.node_manager import node_manager
from config.log_config import get_logger

model_bp = Blueprint("model", __name__)
logger = get_logger("model_routes")


@model_bp.route("/models", methods=["GET"])
def list_models():
    """拉取当前可用的识别模型列表（无需鉴权）。"""
    return jsonify({"success": True, "models": node_manager.get_model_list()}), 200


@model_bp.route("/models/admin", methods=["GET"])
@admin_required
def admin_list_models():
    """管理员：返回全部模型记录。"""
    return jsonify({"success": True, "models": model_manager.list_models()}), 200


@model_bp.route("/models", methods=["POST"])
@admin_required
def create_model():
    data = request.get_json(silent=True) or request.form
    model_id = (data.get("model_id") or "37ac").strip()
    version = (data.get("version") or "").strip()
    config_url = (data.get("config_url") or "").strip()
    if not model_id or not version or not config_url:
        return jsonify({"success": False, "message": "model_id / version / config_url 不能为空"}), 400

    result = model_manager.create_model(
        model_id=model_id,
        display_name=(data.get("display_name") or "").strip(),
        type=(data.get("type") or "local").strip(),
        version=version,
        config_url=config_url,
        config_hash=(data.get("config_hash") or "").strip() or None,
        notes=data.get("notes", ""),
        activate=bool(data.get("activate", False)),
    )
    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result), 201


@model_bp.route("/models/<int:model_id>", methods=["PUT"])
@admin_required
def update_model(model_id):
    data = request.get_json(silent=True) or request.form
    result = model_manager.update_model(
        model_id,
        model_id_new=(data.get("model_id") or None),
        display_name=(data.get("display_name") or None),
        type=(data.get("type") or None),
        version=(data.get("version") or None),
        config_url=(data.get("config_url") or None),
        config_hash=(data.get("config_hash") or None),
        notes=(data.get("notes") if data.get("notes") is not None else None),
    )
    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result), 200


@model_bp.route("/models/<int:model_id>", methods=["DELETE"])
@admin_required
def delete_model(model_id):
    result = model_manager.delete_model(model_id)
    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result), 200


@model_bp.route("/models/<int:model_id>/activate", methods=["POST"])
@admin_required
def activate_model(model_id):
    result = model_manager.set_active(model_id)
    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result), 200
