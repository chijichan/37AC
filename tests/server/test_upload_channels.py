"""POST /upload 多通道 与 POST /upload/human 的路由级测试（假 DB，不联网）。"""

import io
import json
import shutil
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from config import base as cfg
from services import channel_service, settings_service, storage_service


def _png(size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split())
        self.db.executed.append((normalized, params))
        upper = normalized.upper()
        if upper.startswith("SELECT RESULT"):
            row = self.db.rows.get(params[0])
            self._row = (row,) if row is not None else None
        elif upper.startswith("INSERT INTO TASK_RESULTS"):
            # 两种写法：初始化 (task_id, user_id, api_key_id, 'pending', result)
            #           更新   (task_id, result, status)
            if "USER_ID" in upper:
                task_id, payload, status = params[0], params[3], "pending"
            else:
                task_id, payload, status = params[0], params[1], params[2]
            self.db.rows[task_id] = payload
            self.db.status[task_id] = status
            self._row = None

    def fetchone(self):
        return self._row


class FakeDB:
    def __init__(self):
        self.rows = {}
        self.status = {}
        self.executed = []

    def cursor(self, *args, **kwargs):
        return FakeCursor(self)

    def commit(self):
        return None

    def close(self):
        return None


def _wait_for(predicate, timeout=4.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def env(monkeypatch):
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("channels-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cfg, "IMAGE_TMP_PATH", root / "tmp")
    monkeypatch.setattr(cfg, "IMAGE_CACHE_PATH", root / "cache")
    monkeypatch.setattr(storage_service, "_trigger_cleanup_if_needed", lambda label: None)
    storage_service.ensure_dirs()

    # 维护模式闸门走 settings_service -> 这里直接返回"非维护"，避免单测打数据库
    monkeypatch.setattr(
        settings_service, "get_setting",
        lambda key, default=None: "0" if key == "maintenance_mode" else default,
    )

    import routes.upload_routes as upload_routes
    from AC_web import app

    db = FakeDB()
    calls = []
    monkeypatch.setattr(upload_routes, "get_db_connection", lambda: db)
    monkeypatch.setattr(
        upload_routes, "dispatch_task",
        lambda *args, **kwargs: (calls.append((args, kwargs)) or
                                 {"status": "dispatched", "message": "ok"}),
    )
    monkeypatch.setattr(
        upload_routes, "verify_api_key",
        lambda key: {"success": True, "data": {"key_id": 1, "user_id": 1, "permission": "write"}},
    )
    monkeypatch.setattr(upload_routes, "node_manager", SimpleNamespace(
        has_llm_enabled_nodes=lambda: False,
        resolve_model_to_recognition_type=lambda model: "local",
    ))
    channel_service._vote_windows.clear()

    client = app.test_client()
    yield SimpleNamespace(client=client, db=db, calls=calls, root=root, upload=upload_routes)
    shutil.rmtree(root, ignore_errors=True)


def _upload(client, data_extra=None, files=True):
    data = dict(data_extra or {})
    if files:
        data["file"] = (io.BytesIO(_png()), "probe.png")
    return client.post(
        "/upload", data=data, content_type="multipart/form-data",
        headers={"X-API-Key": "good-key"},
    )


# ---------------- 多通道上传 ----------------

def test_upload_multi_channel_fans_out(env):
    response = _upload(env.client, {"channels": "37ac,llm"})
    body = response.get_json()

    assert response.status_code == 200
    assert body["channels"] == ["37ac", "llm"]
    assert body["channel_status"] == {"37ac": "queued", "llm": "queued"}
    task_id = body["task_id"]

    assert _wait_for(lambda: len(env.calls) == 2)
    sub_ids = sorted(call[0][2] for call in env.calls)
    assert sub_ids == [f"{task_id}:37ac", f"{task_id}:llm"]
    recognitions = sorted(call[1]["recognition_type"] for call in env.calls)
    assert recognitions == ["llm", "local"]

    assert _wait_for(lambda: task_id in env.db.rows)
    stored = json.loads(env.db.rows[task_id])
    assert stored["requested_channels"] == ["37ac", "llm"]
    assert stored["37ac"]["status"] == "queued"


def test_upload_single_channel_keeps_parent_task_id(env):
    response = _upload(env.client, {"channels": "37ac"})
    task_id = response.get_json()["task_id"]

    assert _wait_for(lambda: len(env.calls) == 1)
    assert env.calls[0][0][2] == task_id          # 单通道不加后缀（向后兼容）
    assert env.calls[0][1]["recognition_type"] == "local"


def test_upload_human_inline_answer(env):
    response = _upload(env.client, {
        "channels": "37ac,human",
        "human_name": "原神/荧",
        "human_character_index": "0",
        "human_note": "很明显",
    })
    body = response.get_json()

    assert body["channels"] == ["37ac", "human"]
    assert body["channel_status"]["human"] == "completed"
    task_id = body["task_id"]

    assert _wait_for(lambda: task_id in env.db.rows)
    stored = json.loads(env.db.rows[task_id])
    vote = stored["human"]["votes"][0]
    assert vote["name"] == "原神/荧"
    assert vote["character_index"] == 0
    assert vote["note"] == "很明显"
    assert vote["source"] == "upload"
    assert vote["voter"] == "api:1"          # 上传者标识（与匿名 ip:.. 对称）


def test_upload_legacy_model_param_still_works(env):
    response = _upload(env.client, {"model": "llm"})
    body = response.get_json()

    assert body["channels"] == ["llm"]
    assert _wait_for(lambda: len(env.calls) == 1)
    assert env.calls[0][1]["recognition_type"] == "llm"


# ---------------- 匿名人工投票端点 ----------------

def _seed_task(env, channels=("37ac", "llm")):
    task_id = str(uuid.uuid4())
    env.db.rows[task_id] = json.dumps(channel_service.initial_result(task_id, list(channels)),
                                      ensure_ascii=False)
    env.db.status[task_id] = "pending"
    return task_id


def test_human_endpoint_records_vote(env):
    task_id = _seed_task(env)

    response = env.client.post("/upload/human", json={
        "task_id": task_id, "name": "蔚蓝档案/白子", "character_index": 1,
    })
    body = response.get_json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["human"]["votes"][0]["name"] == "蔚蓝档案/白子"
    assert "human" in (json.loads(env.db.rows[task_id])["requested_channels"])


def test_human_endpoint_same_ip_overwrites(env):
    task_id = _seed_task(env)
    env.client.post("/upload/human", json={"task_id": task_id, "name": "A"})
    env.client.post("/upload/human", json={"task_id": task_id, "name": "B"})

    votes = json.loads(env.db.rows[task_id])["human"]["votes"]
    assert len(votes) == 1
    assert votes[0]["name"] == "B"


def test_human_endpoint_validates_input(env):
    response = env.client.post("/upload/human", json={"task_id": "x"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_PARAMS"

    response = env.client.post("/upload/human", json={"name": "x"})
    assert response.status_code == 400


def test_human_endpoint_unknown_task(env):
    response = env.client.post("/upload/human", json={"task_id": "nope", "name": "A"})
    assert response.status_code == 404
    assert response.get_json()["code"] == "NOT_FOUND"


def test_human_endpoint_rate_limited(env, monkeypatch):
    monkeypatch.setattr(env.upload, "HUMAN_VOTE_LIMIT_PER_HOUR", 1)
    channel_service._vote_windows.clear()
    task_id = _seed_task(env)

    first = env.client.post("/upload/human", json={"task_id": task_id, "name": "A"})
    second = env.client.post("/upload/human", json={"task_id": task_id, "name": "B"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.get_json()["code"] == "RATE_LIMITED"
