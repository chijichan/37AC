"""LLM 限流/服务端错误：退避重试 + 部分失败语义（不联网）。"""

import json
import shutil
import uuid
from pathlib import Path

import pytest
import requests
from PIL import Image

from prediction import predictor as P


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("llm-retry-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeResp:
    def __init__(self, status_code, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text or json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        return self._payload


def _ok(label="原神/荧"):
    content = json.dumps({"label": label, "confidence": 90}, ensure_ascii=False)
    return FakeResp(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture
def env(monkeypatch):
    """准备：单张图、可选切图、可记录的 sleep 与 post。"""
    root = _root()
    image = root / "scene.png"
    Image.new("RGB", (300, 400), (30, 60, 90)).save(image)
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(P, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", False)      # 默认走整图路径
    monkeypatch.setattr(P, "LLM_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(P, "LLM_RETRY_BASE_SEC", 2.0)
    monkeypatch.setattr(P, "LLM_RETRY_MAX_SEC", 30.0)
    monkeypatch.setattr(P, "LLM_MAX_TOTAL_SEC", 0.0)           # 测试里默认不限总预算
    yield {"image": image, "root": root, "sleeps": sleeps, "monkeypatch": monkeypatch}
    shutil.rmtree(root, ignore_errors=True)


def _post_sequence(env, responses, calls=None):
    queue = list(responses)

    def fake_post(url, headers=None, json=None, timeout=None):
        if calls is not None:
            calls.append(json)
        item = queue.pop(0) if queue else FakeResp(500, text="no more")
        if isinstance(item, Exception):
            raise item
        return item

    env["monkeypatch"].setattr("requests.post", fake_post)


# ---------------- 纯函数：退避计算 ----------------

def test_retry_delay_prefers_retry_after():
    resp = FakeResp(429, headers={"Retry-After": "2"})
    delay = P._retry_delay(resp, attempt=1, base=1, cap=30)
    assert 2.0 <= delay <= 2.5          # 2s + 最多 25% 抖动


def test_retry_delay_respects_cap():
    resp = FakeResp(429, headers={"Retry-After": "600"})
    assert P._retry_delay(resp, attempt=1, base=1, cap=5) <= 6.25


def test_retry_delay_exponential_without_header():
    resp = FakeResp(503)
    first = P._retry_delay(resp, attempt=1, base=1, cap=30)
    third = P._retry_delay(resp, attempt=3, base=1, cap=30)
    assert 1.0 <= first <= 1.25
    assert 4.0 <= third <= 5.0


def test_parse_retry_after_http_date():
    import email.utils
    from datetime import datetime, timedelta, timezone

    when = datetime.now(timezone.utc) + timedelta(seconds=7)
    resp = FakeResp(429, headers={"Retry-After": email.utils.format_datetime(when)})
    seconds = P._parse_retry_after(resp)
    assert seconds is not None and 5 <= seconds <= 8


# ---------------- 重试行为 ----------------

def test_429_then_success(env):
    calls = []
    _post_sequence(env, [FakeResp(429, text="限流"), _ok()], calls)

    result = P.predict_image_llm(str(env["image"]))

    assert result["success"] is True
    assert len(calls) == 2                     # 一次重试
    assert len(env["sleeps"]) == 1
    assert result["class_probs"][0]["name"] == "原神/荧"


def test_retry_after_header_used_for_wait(env):
    _post_sequence(env, [FakeResp(429, headers={"Retry-After": "3"}), _ok()])

    P.predict_image_llm(str(env["image"]))

    assert 3.0 <= env["sleeps"][0] <= 3.75


def test_persistent_429_returns_error_on_whole_image(env):
    env["monkeypatch"].setattr(P, "LLM_MAX_ATTEMPTS", 3)
    calls = []
    _post_sequence(env, [FakeResp(429, text="限流")] * 5, calls)

    result = P.predict_image_llm(str(env["image"]))

    assert result["success"] is False
    assert len(calls) == 3                     # 尝试 3 次后放弃
    assert "http_429" in (result["error"] or "")
    assert len(env["sleeps"]) == 2             # 只等待两次（最后一次不再等）


def test_timeout_is_retried(env):
    calls = []
    _post_sequence(env, [requests.Timeout(), requests.Timeout(), _ok()], calls)

    result = P.predict_image_llm(str(env["image"]))

    assert result["success"] is True
    assert len(calls) == 3
    assert len(env["sleeps"]) == 2


def test_non_retryable_401_fails_fast(env):
    calls = []
    _post_sequence(env, [FakeResp(401, text="invalid api key")], calls)

    result = P.predict_image_llm(str(env["image"]))

    assert result["success"] is False
    assert len(calls) == 1                     # 不重试
    assert env["sleeps"] == []
    assert "401" in (result["error"] or "")


def test_total_budget_stops_retries(env):
    env["monkeypatch"].setattr(P, "LLM_MAX_TOTAL_SEC", 0.001)
    calls = []
    _post_sequence(env, [FakeResp(429, text="限流")] * 5, calls)

    P.predict_image_llm(str(env["image"]))

    assert len(calls) == 1                     # 预算用尽，不再重试
    assert env["sleeps"] == []


# ---------------- 一图多角：限流只影响那一个人物 ----------------

def _fake_crops(root, count=2):
    crops = []
    for index in range(count):
        crop_file = root / ("crop_%d.jpg" % index)
        Image.new("RGB", (100, 200), (200, 100, 50)).save(crop_file)
        crops.append({
            "index": index,
            "crop_path": str(crop_file),
            "bbox_norm": {"x": 0.1 * index, "y": 0.1, "w": 0.3, "h": 0.7},
            "bbox_percent": {"x": 10.0 * index, "y": 10.0, "w": 30.0, "h": 70.0},
            "detector_confidence": 0.9,
        })
    return crops


def test_rate_limited_character_is_marked_not_failed(env):
    monkeypatch = env["monkeypatch"]
    root = env["root"]
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", True)
    monkeypatch.setattr(P, "crop_for_llm", lambda path, method=None: (_fake_crops(root), str(root), "yolo"))

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        # 第一个人物：一直限流；第二个人物：正常
        if len(calls) <= 3:
            return FakeResp(429, text="该模型当前访问量过大")
        return _ok("蔚蓝档案/白子")

    monkeypatch.setattr("requests.post", fake_post)

    result = P.predict_image_llm(str(env["image"]))

    assert result["success"] is True           # 还有人识别出来了 → 整图不算失败
    assert result["error"] is None
    assert result["character_count"] == 1
    assert result["characters"][0]["label"] == "蔚蓝档案/白子"
    # 限流的那个记为"未识别"，带上框与原因
    assert result["character_failed_count"] == 1
    failed = result["failed_characters"][0]
    assert failed["index"] == 0
    assert failed["reason"] == "http_429"
    assert failed["bbox_percent"] == {"x": 0.0, "y": 10.0, "w": 30.0, "h": 70.0}
    assert result["warnings"]
    assert not root.exists()                   # 临时子图目录照样清理
