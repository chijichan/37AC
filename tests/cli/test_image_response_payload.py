"""节点侧补拉响应组装（需求3 后半）：services/node_service.py 回归测试。"""

import base64
import shutil
import uuid
from pathlib import Path

import pytest

from services.node_service import build_image_response_payload


def _make_root() -> Path:
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("node-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sample_file():
    root = _make_root()
    path = root / "img.png"
    raw = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    path.write_bytes(raw)
    yield path, raw
    shutil.rmtree(root, ignore_errors=True)


def test_payload_contains_base64_image(sample_file):
    path, raw = sample_file
    payload = build_image_response_payload(11, "req-1", "task-1", str(path))

    assert payload["node_id"] == 11
    assert payload["request_id"] == "req-1"
    assert payload["task_id"] == "task-1"
    assert payload["image_size"] == len(raw)
    assert payload["image_filename"] == "img.png"
    assert base64.b64decode(payload["image_data"]) == raw
    assert "error" not in payload


def test_payload_reports_cleaned_when_missing(sample_file):
    path, _raw = sample_file
    path.unlink()

    payload = build_image_response_payload(11, "req-2", "task-1", str(path))

    assert payload["error"] == "节点已清理该图片"
    assert "image_data" not in payload


def test_payload_reports_cleaned_when_path_missing():
    assert build_image_response_payload(11, "req-3", "task-1", None)["error"] == "节点已清理该图片"
    assert build_image_response_payload(11, "req-3", "task-1", "")["error"] == "节点已清理该图片"


def test_payload_reports_read_failure(sample_file):
    path, _raw = sample_file
    # 传一个目录，读取必然失败
    payload = build_image_response_payload(11, "req-4", "task-1", str(path.parent))

    assert "读取图片失败" in payload["error"]
