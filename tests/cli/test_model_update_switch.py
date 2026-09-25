"""模型自动更新开关（AUTO_UPDATE_MODEL）回归测试。

不联网：requests.get 全部打桩；路径指向仓库内 .tmp-tests/。
"""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

import pytest

from services import node_service
from services.node_service import should_sync_model


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("model-switch-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def paths(monkeypatch):
    root = _root()
    monkeypatch.setattr(node_service, "MODEL_PATH", root / "37ac.pth")
    monkeypatch.setattr(node_service, "CLASSES_JSON_PATH", root / "classes.json")
    monkeypatch.setattr(node_service, "MODEL_INFO_PATH", root / "config.json")
    monkeypatch.setattr(node_service, "_update_disabled_logged", False)
    yield root
    shutil.rmtree(root, ignore_errors=True)


# ---------------- 纯函数 ----------------

def test_should_sync_model_matrix():
    assert should_sync_model(True, True) == (True, "auto")
    assert should_sync_model(False, True) == (False, "disabled")
    assert should_sync_model(True, False) == (True, "bootstrap")
    # 本地缺失时必须下载，开关关闭也不例外，否则节点无法推理
    assert should_sync_model(False, False) == (True, "bootstrap")


# ---------------- 关闭开关后不联网 ----------------

def test_disabled_with_local_model_makes_no_request(paths, monkeypatch):
    node_service.MODEL_PATH.write_bytes(b"local-weights")
    node_service.CLASSES_JSON_PATH.write_text("{}", encoding="utf-8")
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        raise AssertionError("关闭自动更新后不应发起任何网络请求")

    monkeypatch.setattr("requests.get", fake_get)
    node_service._sync_local_model(
        [{"id": "37ac", "config_url": "http://host/config.json"}], auto_update=False
    )

    assert calls == []


def test_disabled_without_classes_bootstraps(paths, monkeypatch):
    """权重在但类别缺失：仍应下载一次，避免节点起不来。"""
    node_service.MODEL_PATH.write_bytes(b"local-weights")
    weights = b"W" * 64
    classes = b'{"a": 1}'
    cfg = {
        "version": "1.0.0",
        "model": {"file": "m.pth", "sha256": hashlib.sha256(weights).hexdigest()},
        "classes": {"file": "classes.json", "sha256": hashlib.sha256(classes).hexdigest()},
    }
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("config.json"):
            return FakeResponse(json.dumps(cfg).encode())
        if url.endswith("m.pth"):
            return FakeResponse(weights)
        if url.endswith("classes.json"):
            return FakeResponse(classes)
        raise AssertionError(url)

    monkeypatch.setattr("requests.get", fake_get)
    node_service._sync_local_model(
        [{"id": "37ac", "config_url": "http://host/config.json"}], auto_update=False
    )

    assert node_service.MODEL_PATH.read_bytes() == weights
    assert node_service.CLASSES_JSON_PATH.read_bytes() == classes
    assert any(url.endswith("config.json") for url in calls)


# ---------------- 开启开关后的正常路径 ----------------

def test_bootstrap_downloads_full_model(paths, monkeypatch):
    weights = b"W" * 128
    classes = b'{"a": 2}'
    cfg = {
        "version": "9.9.9",
        "model": {"file": "m.pth", "sha256": hashlib.sha256(weights).hexdigest()},
        "classes": {"file": "classes.json", "sha256": hashlib.sha256(classes).hexdigest()},
    }

    def fake_get(url, **kwargs):
        if url.endswith("config.json"):
            return FakeResponse(json.dumps(cfg).encode())
        if url.endswith("m.pth"):
            return FakeResponse(weights)
        if url.endswith("classes.json"):
            return FakeResponse(classes)
        raise AssertionError(url)

    monkeypatch.setattr("requests.get", fake_get)
    node_service._sync_local_model(
        [{"id": "37ac", "config_url": "http://host/config.json"}], auto_update=False
    )

    assert node_service.MODEL_PATH.read_bytes() == weights
    local_cfg = json.loads(node_service.MODEL_INFO_PATH.read_text(encoding="utf-8"))
    assert local_cfg["version"] == "9.9.9"
    assert local_cfg["model_id"] == node_service.MODEL_ID


def test_enabled_and_up_to_date_skips_weight_download(paths, monkeypatch):
    weights = b"W" * 32
    node_service.MODEL_PATH.write_bytes(weights)
    node_service.CLASSES_JSON_PATH.write_text("{}", encoding="utf-8")
    node_service.MODEL_INFO_PATH.write_text(
        json.dumps({"version": "2.0.0"}), encoding="utf-8"
    )
    cfg = {
        "version": "2.0.0",
        "model": {"file": "m.pth", "sha256": hashlib.sha256(weights).hexdigest()},
        "classes": {"file": "classes.json", "sha256": ""},
    }
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("config.json"):
            return FakeResponse(json.dumps(cfg).encode())
        raise AssertionError("版本一致时不应下载权重: " + url)

    monkeypatch.setattr("requests.get", fake_get)
    node_service._sync_local_model(
        [{"id": "37ac", "config_url": "http://host/config.json"}], auto_update=True
    )

    assert calls == ["http://host/config.json"]


def test_enabled_updates_when_version_changes(paths, monkeypatch):
    weights = b"NEW" * 40
    classes = b'{"a": 3}'
    node_service.MODEL_PATH.write_bytes(b"OLD")
    node_service.CLASSES_JSON_PATH.write_text("{}", encoding="utf-8")
    node_service.MODEL_INFO_PATH.write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
    cfg = {
        "version": "3.0.0",
        "model": {"file": "m.pth", "sha256": hashlib.sha256(weights).hexdigest()},
        "classes": {"file": "classes.json", "sha256": hashlib.sha256(classes).hexdigest()},
    }

    def fake_get(url, **kwargs):
        if url.endswith("config.json"):
            return FakeResponse(json.dumps(cfg).encode())
        if url.endswith("m.pth"):
            return FakeResponse(weights)
        if url.endswith("classes.json"):
            return FakeResponse(classes)
        raise AssertionError(url)

    monkeypatch.setattr("requests.get", fake_get)
    node_service._sync_local_model(
        [{"id": "37ac", "config_url": "http://host/config.json"}], auto_update=True
    )

    assert node_service.MODEL_PATH.read_bytes() == weights
    assert json.loads(node_service.MODEL_INFO_PATH.read_text(encoding="utf-8"))["version"] == "3.0.0"
