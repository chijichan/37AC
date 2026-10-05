"""LLM 一图多角（裁剪方案）：切图 + 逐张识别（不联网）。"""

import json
import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from prediction import predictor as P


def _make_root() -> Path:
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("llm-crop-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


def _llm_reply(label: str, confidence: int = 90, tags=None) -> dict:
    content = json.dumps(
        {"label": label, "confidence": confidence, "features_used": ["白发"], "tags": tags or ["女性角色"]},
        ensure_ascii=False,
    )
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def root():
    path = _make_root()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def image_path(root):
    path = root / "scene.png"
    Image.new("RGB", (400, 300), (20, 40, 60)).save(path)
    return path


def _fake_crops(root, count=2):
    """造 count 张"子图"，并返回检测器风格的 characters 列表。"""
    crops = []
    for index in range(count):
        crop_file = root / f"crop_{index}.jpg"
        Image.new("RGB", (120, 200), (200, 100, 50)).save(crop_file)
        crops.append({
            "index": index,
            "crop_path": str(crop_file),
            "bbox": (index * 100, 20, index * 100 + 100, 220),
            "bbox_norm": {"x": 0.1 * index, "y": 0.1, "w": 0.25, "h": 0.7},
            "bbox_percent": {"x": 10.0 * index, "y": 10.0, "w": 25.0, "h": 70.0},
            "detector_confidence": 0.9 - index * 0.1,
            "class_name": "person",
        })
    return crops


# ---------------- 切图方式选择 ----------------

def test_resolve_crop_method_auto_prefers_yolo(monkeypatch):
    monkeypatch.setattr(P, "LLM_CROP_METHOD", "auto")
    monkeypatch.setattr(P, "LOCAL_RECOGNITION_ENABLED", True)
    assert P.resolve_llm_crop_method() == "yolo"

    # 只做 LLM 的节点没有 torch，不能用 YOLO -> 用 mediapipe（轻量）
    monkeypatch.setattr(P, "LOCAL_RECOGNITION_ENABLED", False)
    assert P.resolve_llm_crop_method() == "mediapipe"


def test_resolve_crop_method_explicit(monkeypatch):
    for method in ("yolo", "mediapipe", "none"):
        monkeypatch.setattr(P, "LLM_CROP_METHOD", method)
        assert P.resolve_llm_crop_method() == method


def test_crop_for_llm_none_skips_detector(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("method=none 时不应调用检测器")

    monkeypatch.setattr("detection.cropper.crop_characters_by_method", _boom)
    assert P.crop_for_llm("whatever.jpg", method="none") == ([], None, "none")


def test_crop_for_llm_uses_detector(root, monkeypatch):
    crops = _fake_crops(root)
    monkeypatch.setattr("detection.cropper.crop_characters_by_method", lambda *a, **k: {
        "image_size": (400, 300), "detected_size": (400, 300),
        "characters": crops, "crop_method": "yolo", "tmp_dir": str(root),
    })

    found, tmp_dir, method = P.crop_for_llm("scene.png", method="yolo")

    assert len(found) == 2 and method == "yolo" and tmp_dir == str(root)


# ---------------- 逐张识别 ----------------

def test_predict_llm_identifies_each_crop(image_path, root, monkeypatch):
    crops = _fake_crops(root)
    monkeypatch.setattr(P, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", True)
    monkeypatch.setattr(P, "crop_for_llm", lambda path, method=None: (crops, str(root), "yolo"))

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        index = len(calls) - 1
        return FakeResponse(_llm_reply(["原神/雷电将军", "蔚蓝档案/白子"][index], 95 - index * 5))

    monkeypatch.setattr("requests.post", fake_post)

    result = P.predict_image_llm(str(image_path))

    assert result["success"] is True
    assert len(calls) == 2                       # 每个人物一次调用
    assert result["character_count"] == 2
    assert result["crop_method"] == "llm_yolo"
    # 框来自检测器（不是 LLM 猜的）
    assert result["characters"][0]["bbox"] == crops[0]["bbox_norm"]
    assert result["characters"][1]["bbox_percent"] == crops[1]["bbox_percent"]
    assert result["characters"][1]["detector_confidence"] == crops[1]["detector_confidence"]
    assert result["characters"][0]["source"] == "llm"
    # 顶层兼容字段 = 置信度最高的人物
    assert result["class_probs"][0]["name"] == "原神/雷电将军"
    # 子图临时目录用完即清
    assert not root.exists()


def test_predict_llm_falls_back_to_whole_image(image_path, monkeypatch):
    monkeypatch.setattr(P, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", True)
    monkeypatch.setattr(P, "crop_for_llm", lambda path, method=None: ([], None, "none"))

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return FakeResponse(_llm_reply("原神/荧", 88))

    monkeypatch.setattr("requests.post", fake_post)

    result = P.predict_image_llm(str(image_path))

    assert len(calls) == 1                       # 没切出人物 -> 整图一次
    assert result["crop_method"] == "llm"
    assert result["character_count"] == 1
    assert result["characters"][0]["bbox"] is None
    assert result["class_probs"][0]["name"] == "原神/荧"


def test_predict_llm_skips_crop_when_disabled(image_path, monkeypatch):
    monkeypatch.setattr(P, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", False)

    def _boom(*args, **kwargs):
        raise AssertionError("关闭多角时不应切图")

    monkeypatch.setattr(P, "crop_for_llm", _boom)
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(_llm_reply("原神/荧")))

    result = P.predict_image_llm(str(image_path))

    assert result["success"] is True
    assert result["crop_method"] == "llm"


def test_predict_llm_partial_failure_keeps_others(image_path, root, monkeypatch):
    """某个人物识别失败（模型返回空）时，其它人物结果照常返回。"""
    crops = _fake_crops(root, count=2)
    monkeypatch.setattr(P, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(P, "LLM_MULTI_CHARACTER", True)
    monkeypatch.setattr(P, "crop_for_llm", lambda path, method=None: (crops, str(root), "yolo"))

    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        if len(calls) == 1:
            return FakeResponse({"choices": [{"message": {"content": "{}"}}]})   # 第一个失败
        return FakeResponse(_llm_reply("蔚蓝档案/白子"))

    monkeypatch.setattr("requests.post", fake_post)

    result = P.predict_image_llm(str(image_path))

    assert result["success"] is True
    assert result["character_count"] == 1
    assert result["characters"][0]["label"] == "蔚蓝档案/白子"


# ---------------- 解析器仍兼容"整图多角"自定义提示词 ----------------

def test_parse_llm_response_accepts_characters_array():
    resp = {"choices": [{"message": {"content": json.dumps({
        "characters": [{"label": "崩坏：星穹铁道/银狼", "confidence": 77}],
    }, ensure_ascii=False)}}]}

    label, confidence, _f, _t, probs = P._parse_llm_response(resp)

    assert label == "崩坏：星穹铁道/银狼"
    assert confidence == 77
    assert probs == []


def test_parse_llm_response_empty_content():
    assert P._parse_llm_response({"choices": [{"message": {"content": ""}}]}) == ("", 0.0, [], [], [])
