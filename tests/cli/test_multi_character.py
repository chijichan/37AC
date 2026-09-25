"""多人物识别（需求1）：bbox 工具 / 多目标裁剪 / 坐标映射回归测试。

不依赖 ultralytics 权重：检测结果用假检测器注入（crop/detect 之外都是纯 PIL/算术）。
"""

import os
import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from detection import bbox as B
from detection.yolo_detector import YoloDetector, crop_characters


def _make_root() -> Path:
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("multi-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def root():
    path = _make_root()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def scene(root):
    """1000x800 的假“合影”。"""
    path = root / "scene.png"
    Image.new("RGB", (1000, 800), (12, 34, 56)).save(path)
    return path


class FakeDetector(YoloDetector):
    """把 detect() 打桩的检测器：返回预设的（传入图像坐标系的）框。"""

    def __init__(self, detections):
        super().__init__()
        self._fake = detections
        self._loaded = True

    def detect(self, image):
        return [dict(item) for item in self._fake]

    def _load_model(self):
        return True


# ---------------- bbox 工具 ----------------

def test_clamp_bbox_inside_and_minimum_size():
    assert B.clamp_bbox((-10, -10, 2000, 2000), (100, 50)) == (0, 0, 100, 50)
    assert B.clamp_bbox((30, 30, 31, 31), (100, 50)) == (30, 30, 31, 31)


def test_expand_bbox_by_ratio():
    assert B.expand_bbox((100, 100, 200, 200), (1000, 1000), 0.5) == (50, 50, 250, 250)
    assert B.expand_bbox((100, 100, 200, 200), (1000, 1000), 0.0) == (100, 100, 200, 200)


def test_scale_bbox_maps_between_coordinate_systems():
    # 1000x800 -> 500x400（缩放一半）
    assert B.scale_bbox((50, 25, 150, 125), (500, 400), (1000, 800)) == (100, 50, 300, 250)


def test_normalize_and_percent_bbox():
    norm = B.normalize_bbox((100, 80, 300, 480), (1000, 800))
    assert norm == {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.5}

    percent = B.percent_bbox((100, 80, 300, 480), (1000, 800))
    assert percent == {"x": 10.0, "y": 10.0, "w": 20.0, "h": 50.0}


def test_bbox_iou():
    assert B.bbox_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert B.bbox_iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


# ---------------- 多目标检测：坐标必须映射回原图 ----------------

def test_detect_all_maps_boxes_back_to_original_image(scene):
    # 传入的是「缩放后」坐标系的框（1000x800 -> 500x400）
    detector = FakeDetector([
        {"bbox": (100, 50, 200, 150), "confidence": 0.9, "class_id": 0, "class_name": "person"},
    ])

    found = detector.detect_all(str(scene), max_size=500, target_classes=["person"])

    assert found["image_size"] == (1000, 800)
    assert found["detected_size"] == (500, 400)
    assert found["detections"][0]["bbox"] == (200, 100, 400, 300)     # 已换算回原图
    assert found["detections"][0]["area"] == 200 * 200


def test_detect_all_sorts_by_area_and_filters_classes(scene):
    detector = FakeDetector([
        {"bbox": (10, 10, 60, 60), "confidence": 0.99, "class_id": 0, "class_name": "person"},
        {"bbox": (100, 100, 400, 400), "confidence": 0.60, "class_id": 0, "class_name": "person"},
        {"bbox": (0, 0, 30, 30), "confidence": 0.95, "class_id": 2, "class_name": "car"},
    ])

    found = detector.detect_all(str(scene), max_size=0, target_classes=["person"])
    boxes = [d["bbox"] for d in found["detections"]]

    assert boxes == [(100, 100, 400, 400), (10, 10, 60, 60)]   # 面积降序，car 被过滤


def test_detect_all_without_target_classes_keeps_everything(scene):
    detector = FakeDetector([
        {"bbox": (0, 0, 30, 30), "confidence": 0.95, "class_id": 2, "class_name": "car"},
    ])
    found = detector.detect_all(str(scene), max_size=0, target_classes=None)
    assert len(found["detections"]) == 1


# ---------------- 多目标裁剪 + 归一化坐标 ----------------

def test_crop_all_writes_one_file_per_detection(scene, root):
    detector = FakeDetector([])
    out_dir = root / "crops"
    detections = [
        {"bbox": (0, 0, 100, 200), "confidence": 0.8, "class_id": 0, "class_name": "person"},
        {"bbox": (500, 400, 700, 800), "confidence": 0.7, "class_id": 0, "class_name": "person"},
    ]

    crops = detector.crop_all(str(scene), detections, str(out_dir), margin_ratio=0.0)

    assert len(crops) == 2
    for item in crops:
        assert os.path.exists(item["crop_path"])
    with Image.open(crops[0]["crop_path"]) as img:
        assert img.size == (100, 200)
    with Image.open(crops[1]["crop_path"]) as img:
        assert img.size == (200, 400)


def test_crop_all_applies_margin(scene, root):
    detector = FakeDetector([])
    detections = [{"bbox": (100, 100, 200, 200), "confidence": 0.9, "class_id": 0, "class_name": "person"}]

    crops = detector.crop_all(str(scene), detections, str(root / "m"), margin_ratio=0.5)

    assert crops[0]["bbox"] == (50, 50, 250, 250)     # 各方向外扩 50%


def test_crop_characters_returns_percent_coordinates(scene, root, monkeypatch):
    fake = FakeDetector([
        {"bbox": (100, 80, 300, 480), "confidence": 0.91, "class_id": 0, "class_name": "person"},
    ])
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: fake)

    out = crop_characters(str(scene), max_size=0, margin_ratio=0.0, output_dir=str(root / "chars"))

    assert out["image_size"] == (1000, 800)
    characters = out["characters"]
    assert len(characters) == 1
    assert os.path.exists(characters[0]["crop_path"])
    assert characters[0]["bbox"] == (100, 80, 300, 480)
    assert characters[0]["bbox_norm"] == {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.5}
    assert characters[0]["bbox_percent"] == {"x": 10.0, "y": 10.0, "w": 20.0, "h": 50.0}
    assert characters[0]["detector_confidence"] == 0.91


def test_crop_characters_respects_max_characters(scene, root, monkeypatch):
    fake = FakeDetector([
        {"bbox": (0, 0, 300, 300), "confidence": 0.9, "class_id": 0, "class_name": "person"},
        {"bbox": (400, 0, 600, 300), "confidence": 0.8, "class_id": 0, "class_name": "person"},
        {"bbox": (700, 0, 900, 300), "confidence": 0.7, "class_id": 0, "class_name": "person"},
    ])
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: fake)

    out = crop_characters(str(scene), max_characters=2, max_size=0, margin_ratio=0.0,
                          output_dir=str(root / "limit"))

    assert len(out["characters"]) == 2


def test_crop_characters_returns_empty_when_nothing_detected(scene, root, monkeypatch):
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeDetector([]))

    out = crop_characters(str(scene), max_size=0, output_dir=str(root / "none"))

    assert out["characters"] == []
    assert out["image_size"] == (1000, 800)
