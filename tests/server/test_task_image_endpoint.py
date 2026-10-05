"""GET /tasks/<task_id>/image 与任务图片留存的回归测试。

不依赖数据库：API Key 校验与 DB 连接都在 upload_routes 命名空间里被打桩。
"""

import io
import os
import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from config import base as cfg
from services import storage_service


def _solid_png(size=(1200, 800), color=(200, 30, 40)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _noise_png(size=(1200, 800)):
    buf = io.BytesIO()
    Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3)).save(buf, format="PNG")
    return buf.getvalue()


def _dimensions(data):
    with Image.open(io.BytesIO(data)) as img:
        return img.size


@pytest.fixture
def client(monkeypatch):
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("img-" + uuid.uuid4().hex[:8])
    tmp_dir, cache_dir = root / "tmp", root / "cache"
    monkeypatch.setattr(cfg, "IMAGE_TMP_PATH", tmp_dir)
    monkeypatch.setattr(cfg, "IMAGE_CACHE_PATH", cache_dir)
    storage_service.ensure_dirs()

    import routes.upload_routes as upload_routes
    from AC_web import app

    monkeypatch.setattr(
        upload_routes, "verify_api_key",
        lambda key: {"success": True, "data": {"key_id": 1, "user_id": 1}} if key == "good-key"
        else {"success": False, "message": "API密钥无效"},
    )
    # 单测不打数据库：默认关闭"向节点补拉"
    monkeypatch.setattr(upload_routes, "_try_refetch", lambda task_id: False)
    app.config.update(TESTING=False)
    yield SimpleNamespace(client=app.test_client(), dirs={"tmp": tmp_dir, "cache": cache_dir})
    shutil.rmtree(root, ignore_errors=True)


def _seed(task_id, data, ext=".png"):
    storage_service.save_temp(task_id, data, ext)
    storage_service.save_cache(task_id, data, ext)


# ---------------- 鉴权 ----------------

def test_image_requires_credential(client):
    response = client.client.get("/tasks/t-1/image")

    assert response.status_code == 401
    body = response.get_json()
    assert body["code"] == "API_KEY_MISSING"


def test_image_rejects_bad_api_key(client):
    response = client.client.get("/tasks/t-1/image", headers={"X-API-Key": "bad"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "API_KEY_INVALID"


# ---------------- 取图 ----------------

def test_image_returns_cached_copy_by_default(client):
    _seed("task-a", _noise_png((900, 700)))
    response = client.client.get("/tasks/task-a/image", headers={"X-API-Key": "good-key"})

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"              # cache 侧是压缩后的 JPEG
    assert response.headers["X-Image-Source"] == "cache"
    assert int(response.headers["Content-Length"]) == len(response.data)
    assert max(_dimensions(response.data)) <= 512
    assert "max-age" in response.headers.get("Cache-Control", "")


def test_image_original_prefers_tmp(client):
    raw = _noise_png((900, 700))
    _seed("task-b", raw)
    response = client.client.get("/tasks/task-b/image?original=1", headers={"X-API-Key": "good-key"})

    assert response.status_code == 200
    assert response.headers["X-Image-Source"] == "tmp"
    assert response.mimetype == "image/png"
    assert response.data == raw                              # 原图逐字节一致


def test_image_max_side_resizes_on_the_fly(client):
    _seed("task-c", _noise_png((1200, 800)))
    response = client.client.get("/tasks/task-c/image?max_side=64", headers={"X-API-Key": "good-key"})

    assert response.status_code == 200
    assert max(_dimensions(response.data)) <= 64


def test_missing_image_returns_410_with_metadata(client):
    response = client.client.get("/tasks/never-existed/image", headers={"X-API-Key": "good-key"})

    assert response.status_code == 410
    body = response.get_json()
    assert body["code"] == "IMAGE_EXPIRED"
    assert body["success"] is False
    assert body["image"]["available"] is False
    assert body["image"]["url"].endswith("/image")


def test_image_refetch_then_served_from_cache(client, monkeypatch):
    """本地已回收时向节点补拉：成功后写回 cache 并正常返回（需求3 后半）。"""
    import routes.upload_routes as upload_routes

    def fake_refetch(task_id):
        storage_service.save_cache(task_id, _solid_png((300, 200)), ".png")
        return True

    monkeypatch.setattr(upload_routes, "_try_refetch", fake_refetch)
    response = client.client.get("/tasks/refetched-1/image", headers={"X-API-Key": "good-key"})

    assert response.status_code == 200
    assert response.headers["X-Image-Source"] == "cache"
    assert max(_dimensions(response.data)) == 300


def test_image_refetch_failure_still_410(client, monkeypatch):
    import routes.upload_routes as upload_routes

    monkeypatch.setattr(upload_routes, "_try_refetch", lambda task_id: False)
    response = client.client.get("/tasks/gone-1/image", headers={"X-API-Key": "good-key"})

    assert response.status_code == 410
    assert response.get_json()["code"] == "IMAGE_EXPIRED"


def test_image_route_survives_path_traversal_attempt(client):
    # 路径穿越在路由层就被 Flask 规范化掉（404），根本到不了处理器
    response = client.client.get("/tasks/..%2F..%2Fetc/image", headers={"X-API-Key": "good-key"})
    assert response.status_code in (404, 410)


def test_image_route_rejects_illegal_task_id(client):
    # 带 ".." 的 task_id 会被 normalize_task_id 拒掉 -> 410，不会去碰文件系统
    response = client.client.get("/tasks/abc..def/image", headers={"X-API-Key": "good-key"})
    assert response.status_code == 410
    assert response.get_json()["code"] == "IMAGE_EXPIRED"


# ---------------- 任务查询里的 image 元数据 ----------------

def test_task_result_exposes_image_metadata(client, monkeypatch):
    import routes.upload_routes as upload_routes
    monkeypatch.setattr(upload_routes, "get_db_connection", lambda: None)   # 避开真实数据库

    _seed("task-d", _noise_png((800, 600)))
    response = client.client.get("/tasks/task-d", headers={"X-API-Key": "good-key"})

    assert response.status_code == 503
    body = response.get_json()
    assert body["code"] == "DB_UNAVAILABLE"
    assert body["image"]["available"] is True
    assert body["image"]["source"] == "cache"
    assert body["image"]["ext"] == ".jpg"


def test_task_result_image_metadata_when_expired(client, monkeypatch):
    import routes.upload_routes as upload_routes
    monkeypatch.setattr(upload_routes, "get_db_connection", lambda: None)

    response = client.client.get("/tasks/none-here", headers={"X-API-Key": "good-key"})
    body = response.get_json()

    assert body["image"]["available"] is False
    assert body["image"]["url"] == "/tasks/none-here/image"
