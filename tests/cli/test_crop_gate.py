"""裁剪质量门控（实测驱动：误检框会拉低准确率）回归测试。"""

import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from detection import cropper


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("gate-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def root():
    path = _root()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setattr(cropper, "CROP_QUALITY_GATE", True)
    monkeypatch.setattr(cropper, "CROP_MIN_CONFIDENCE", 0.35)
    monkeypatch.setattr(cropper, "CROP_MIN_AREA_RATIO", 0.06)
    monkeypatch.setattr(cropper, "CROP_MAX_AREA_RATIO", 0.98)


# ---------------- 候选框门控 ----------------

def test_gate_filters_low_confidence(gate_on):
    items = [
        {"bbox_norm": {"w": 0.4, "h": 0.6}, "detector_confidence": 0.9},
        {"bbox_norm": {"w": 0.4, "h": 0.6}, "detector_confidence": 0.2},
    ]
    assert len(cropper.gate_detections(items, (1000, 1000))) == 1


def test_gate_filters_small_and_huge_boxes(gate_on):
    items = [
        {"bbox_norm": {"w": 0.2, "h": 0.2}, "detector_confidence": 0.9},   # 面积 4% -> 丢弃
        {"bbox_norm": {"w": 0.9, "h": 0.99}, "detector_confidence": 0.9},  # 面积 89% -> 保留
        {"bbox_norm": {"w": 0.995, "h": 0.995}, "detector_confidence": 0.9},  # 99% -> 太大，丢弃
    ]
    assert len(cropper.gate_detections(items, (1000, 1000))) == 1


def test_gate_keeps_pose_boxes_without_confidence(gate_on):
    items = [{"bbox_norm": {"w": 0.3, "h": 0.8}, "detector_confidence": None,
              "class_name": "mediapipe_pose"}]
    assert len(cropper.gate_detections(items, (1000, 1000))) == 1


def test_gate_computes_area_from_raw_bbox(gate_on):
    # 没有 bbox_norm 时用像素框 / 原图面积算占比（5% -> 丢弃；25% -> 保留）
    items = [
        {"bbox": (0, 0, 100, 500), "detector_confidence": 0.9},
        {"bbox": (0, 0, 500, 500), "detector_confidence": 0.9},
    ]
    assert len(cropper.gate_detections(items, (1000, 1000))) == 1


def test_gate_disabled_passes_everything(monkeypatch):
    monkeypatch.setattr(cropper, "CROP_QUALITY_GATE", False)
    items = [{"bbox_norm": {"w": 0.01, "h": 0.01}, "detector_confidence": 0.01}]
    assert len(cropper.gate_detections(items, (1000, 1000))) == 1


def test_gate_handles_empty_and_none():
    assert cropper.gate_detections([], (10, 10)) == []
    assert cropper.gate_detections(None, (10, 10)) == []


# ---------------- 单框路径门控 ----------------

def test_crop_quality_ok_by_area(root, gate_on):
    original = root / "orig.png"
    Image.new("RGB", (1000, 1000), (0, 0, 0)).save(original)

    tiny = root / "tiny.png"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(tiny)          # 1% -> 不合格
    ok = root / "ok.png"
    Image.new("RGB", (500, 500), (0, 0, 0)).save(ok)            # 25% -> 合格
    huge = root / "huge.png"
    Image.new("RGB", (999, 999), (0, 0, 0)).save(huge)          # 99.8% -> 太大，不合格

    assert cropper.crop_quality_ok(str(tiny), str(original), 0.9) is False
    assert cropper.crop_quality_ok(str(ok), str(original), 0.9) is True
    assert cropper.crop_quality_ok(str(huge), str(original), 0.9) is False


def test_crop_quality_ok_by_confidence(root, gate_on):
    original = root / "orig.png"
    Image.new("RGB", (500, 500), (0, 0, 0)).save(original)
    crop = root / "crop.png"
    Image.new("RGB", (250, 250), (0, 0, 0)).save(crop)

    assert cropper.crop_quality_ok(str(crop), str(original), 0.1) is False
    assert cropper.crop_quality_ok(str(crop), str(original), 0.9) is True
    assert cropper.crop_quality_ok(str(crop), str(original), None) is True   # 没置信度不拦


def test_crop_quality_ok_missing_files_passes(root, gate_on):
    assert cropper.crop_quality_ok(str(root / "nope.png"), str(root / "nope2.png"), 0.9) is True


def test_crop_quality_ok_disabled(monkeypatch, root):
    monkeypatch.setattr(cropper, "CROP_QUALITY_GATE", False)
    assert cropper.crop_quality_ok(str(root / "nope.png"), str(root / "nope2.png"), 0.01) is True


# ---------------- 与统一入口联动 ----------------

def test_crop_characters_by_method_applies_gate(root, gate_on, monkeypatch):
    image_path = root / "scene.png"
    Image.new("RGB", (1000, 1000), (10, 10, 10)).save(image_path)
    for index in range(3):
        Image.new("RGB", (200, 200), (index * 50, 0, 0)).save(root / f"c{index}.jpg")

    characters = [
        {"index": 0, "crop_path": str(root / "c0.jpg"), "bbox_norm": {"w": 0.5, "h": 0.5},
         "bbox_percent": {"w": 50.0, "h": 50.0}, "detector_confidence": 0.9},   # 保留
        {"index": 1, "crop_path": str(root / "c1.jpg"), "bbox_norm": {"w": 0.5, "h": 0.5},
         "bbox_percent": {"w": 50.0, "h": 50.0}, "detector_confidence": 0.1},   # 置信度低
        {"index": 2, "crop_path": str(root / "c2.jpg"), "bbox_norm": {"w": 0.05, "h": 0.05},
         "bbox_percent": {"w": 5.0, "h": 5.0}, "detector_confidence": 0.9},     # 面积太小
    ]
    monkeypatch.setattr("detection.cropper.crop_characters_by_method", cropper.crop_characters_by_method, raising=False)
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: type("D", (), {
        "detect_all": lambda self, *a, **k: {
            "image_size": (1000, 1000), "detected_size": (1000, 1000), "detections": [],
        },
    })())
    monkeypatch.setattr(cropper, "_mediapipe_characters", lambda *a, **k: {
        "image_size": (1000, 1000), "detected_size": (1000, 1000), "characters": characters,
    })

    found = cropper.crop_characters_by_method(str(image_path), method="mediapipe",
                                              output_dir=str(root))

    assert found["crop_method"] == "mediapipe"
    assert len(found["characters"]) == 1
    assert found["characters"][0]["index"] == 0
