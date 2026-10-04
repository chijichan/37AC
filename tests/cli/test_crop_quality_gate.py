"""裁剪质量门控：长宽比过滤。"""

import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from detection import cropper as C


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("gate-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _item(w, h, confidence=0.9):
    return {"bbox_norm": {"x": 0.1, "y": 0.1, "w": w, "h": h},
            "detector_confidence": confidence}


@pytest.fixture(autouse=True)
def defaults(monkeypatch):
    monkeypatch.setattr(C, "CROP_QUALITY_GATE", True)
    monkeypatch.setattr(C, "CROP_MIN_CONFIDENCE", 0.35)
    monkeypatch.setattr(C, "CROP_MIN_AREA_RATIO", 0.06)
    monkeypatch.setattr(C, "CROP_MAX_AREA_RATIO", 0.98)
    monkeypatch.setattr(C, "CROP_MIN_ASPECT_RATIO", 0.15)
    monkeypatch.setattr(C, "CROP_MAX_ASPECT_RATIO", 4.0)


def test_normal_boxes_pass():
    items = [_item(0.3, 0.6), _item(0.6, 0.4)]          # 0.5、1.5 → 放行
    assert C.gate_detections(items, (1000, 1000)) == items


def test_extreme_aspect_filtered():
    items = [_item(0.3, 0.6),                          # ok
             _item(0.8, 0.1),                          # 8.0 太扁
             _item(0.1, 0.8)]                          # 0.125 太细（面积 0.08 仍达标）
    passed = C.gate_detections(items, (1000, 1000))
    assert len(passed) == 1 and passed[0]["bbox_norm"]["w"] == 0.3


def test_aspect_filter_can_be_disabled(monkeypatch):
    monkeypatch.setattr(C, "CROP_MIN_ASPECT_RATIO", 0)
    monkeypatch.setattr(C, "CROP_MAX_ASPECT_RATIO", 0)
    # 注意面积要达标（0.08 > CROP_MIN_AREA_RATIO），否则是被面积条件过滤、而不是长宽比
    items = [_item(0.8, 0.1), _item(0.1, 0.8)]
    assert len(C.gate_detections(items, (1000, 1000))) == 2


def test_pixel_bbox_fallback():
    # 没有 bbox_norm 时用像素框算长宽比：1000x100 = 10 → 过滤
    item = {"bbox": (0, 0, 1000, 100), "detector_confidence": 0.9}
    assert C.gate_detections([item], (1000, 1000)) == []
    ok = {"bbox": (0, 0, 300, 600), "detector_confidence": 0.9}
    assert C.gate_detections([ok], (1000, 1000)) == [ok]


def test_crop_quality_ok_checks_aspect():
    root = _root()
    try:
        original = root / "original.png"
        Image.new("RGB", (1000, 1000), (0, 0, 0)).save(original)

        normal = root / "normal.png"
        Image.new("RGB", (200, 400), (1, 2, 3)).save(normal)     # 长宽比 0.5、面积占比 0.08
        assert C.crop_quality_ok(str(normal), str(original), confidence=0.9) is True

        wide = root / "wide.png"
        Image.new("RGB", (800, 100), (1, 2, 3)).save(wide)        # 长宽比 8.0、面积占比 0.08
        assert C.crop_quality_ok(str(wide), str(original), confidence=0.9) is False
    finally:
        shutil.rmtree(root, ignore_errors=True)

# ---------------- 数据集裁剪路径也走门控 ----------------

def test_check_max_area_can_be_skipped():
    """数据集场景：框几乎占满整图是正常的（源图本身就是紧裁剪立绘）。"""
    full_frame = _item(0.99, 1.0)                      # 面积 0.99 > CROP_MAX_AREA_RATIO
    assert C.gate_detections([full_frame], (1000, 1000)) == []
    assert C.gate_detections([full_frame], (1000, 1000), check_max_area=False) == [full_frame]


def _detector_with(box, confidence=0.9):
    from detection import yolo_detector as YD

    det = YD.YoloDetector()
    det._loaded = True
    det.detect = lambda image: [
        {"bbox": box, "confidence": confidence, "class_id": 0, "class_name": "person"}
    ]
    return det


def test_dataset_crop_applies_gate(monkeypatch):
    root = _root()
    try:
        from PIL import Image as _Image

        src = root / "src.png"
        _Image.new("RGB", (1000, 1000), (5, 5, 5)).save(src)

        # 极扁的误检框（1000x100 = 10.0）→ 门控拦下，当作"没检出人物"
        bad = _detector_with((0, 0, 1000, 100))          # 面积 0.1、长宽比 10
        data, _info = bad.detect_and_crop_bytes(str(src), max_size=0, detect_max_size=1000)
        assert data is None

        # 正常人物框 → 正常裁剪
        good = _detector_with((200, 100, 500, 900))      # 长宽比 0.375、面积 0.24
        data2, info2 = good.detect_and_crop_bytes(str(src), max_size=0, detect_max_size=1000)
        assert data2 and info2["bbox"] == (200, 100, 500, 900)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_dataset_crop_gate_can_be_disabled(monkeypatch):
    root = _root()
    try:
        from PIL import Image as _Image

        monkeypatch.setattr(C, "CROP_QUALITY_GATE", False)
        src = root / "src.png"
        _Image.new("RGB", (1000, 1000), (5, 5, 5)).save(src)

        bad = _detector_with((0, 0, 1000, 100))
        data, info = bad.detect_and_crop_bytes(str(src), max_size=0, detect_max_size=1000)
        assert data and info["bbox"] == (0, 0, 1000, 100)   # 关掉门控 → 不再拦截
    finally:
        shutil.rmtree(root, ignore_errors=True)
