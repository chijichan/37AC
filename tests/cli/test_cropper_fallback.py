"""裁剪方式选择与回退链（需求2）：detection/cropper.py 回归测试。"""

import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from detection import cropper, mediapipe_detector
from detection.yolo_detector import YoloDetector


def _make_root() -> Path:
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("crop-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def scene():
    root = _make_root()
    path = root / "scene.png"
    Image.new("RGB", (800, 600), (30, 40, 50)).save(path)
    yield path, root
    shutil.rmtree(root, ignore_errors=True)


class FakeYolo(YoloDetector):
    def __init__(self, detections):
        super().__init__()
        self._fake = detections
        self._loaded = True

    def detect(self, image):
        return [dict(item) for item in self._fake]

    def _load_model(self):
        return True


def _person_box():
    return {"bbox": (100, 100, 300, 500), "confidence": 0.9, "class_id": 0, "class_name": "person"}


# ---------------- mediapipe 不可用时的能力上报 ----------------

def test_available_methods_without_mediapipe(monkeypatch):
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: False)
    assert cropper.available_methods() == ["yolo"]


def test_available_methods_with_mediapipe(monkeypatch):
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: True)
    assert cropper.available_methods() == ["yolo", "mediapipe"]


# ---------------- 脸框 -> 角色区域 的几何 ----------------

def test_face_box_to_character_expands_around_face():
    # 脸 (100,100)-(200,200)：宽 100、高 100
    box = mediapipe_detector.face_box_to_character((100, 100, 200, 200), (1000, 1000),
                                                   expand_w=2.0, expand_h=3.0, up_shift=0.5)
    # 宽 200、高 300，中心 x=150；脸底 200 往上留一半 -> top=50
    assert box == (50, 50, 250, 350)


def test_face_box_to_character_clamps_to_image():
    box = mediapipe_detector.face_box_to_character((10, 10, 60, 60), (200, 200),
                                                   expand_w=4.0, expand_h=4.0, up_shift=0.5)
    assert box[0] >= 0 and box[1] >= 0 and box[2] <= 200 and box[3] <= 200


def test_landmarks_to_bbox_skips_invisible_points():
    class P:
        def __init__(self, x, y, v):
            self.x, self.y, self.visibility = x, y, v

    landmarks = [P(0.1, 0.1, 0.9), P(0.5, 0.5, 0.9), P(0.9, 0.9, 0.1)]   # 第三个不可见
    box = mediapipe_detector.landmarks_to_bbox(landmarks, (100, 100))
    assert box == (10, 10, 50, 50)


def test_landmarks_to_bbox_all_invisible_returns_none():
    class P:
        def __init__(self):
            self.x, self.y, self.visibility = 0.5, 0.5, 0.0

    assert mediapipe_detector.landmarks_to_bbox([P()], (100, 100)) is None


# ---------------- auto 回退链 ----------------

def test_auto_uses_yolo_when_person_found(scene, monkeypatch):
    path, root = scene
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeYolo([_person_box()]))
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: False)

    out = cropper.crop_characters_by_method(str(path), method="auto", margin_ratio=0.0,
                                            output_dir=str(root / "y"))

    assert out["crop_method"] == "yolo"
    assert len(out["characters"]) == 1
    assert out["characters"][0]["bbox"] == (100, 100, 300, 500)
    assert out["characters"][0]["bbox_norm"] == {"x": 0.125, "y": 0.1667, "w": 0.25, "h": 0.6667}


def test_auto_uses_default_temp_root_when_output_dir_omitted(scene, monkeypatch):
    path, root = scene
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeYolo([_person_box()]))
    monkeypatch.setattr("detection.yolo_detector._tmp_root", lambda: root)
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: False)

    out = cropper.crop_characters_by_method(str(path), method="auto", margin_ratio=0.0)

    assert out["crop_method"] == "yolo"
    assert len(out["characters"]) == 1
    assert Path(out["tmp_dir"]).parent == root


def test_auto_falls_back_to_mediapipe(scene, monkeypatch):
    path, root = scene
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeYolo([]))
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: True)
    monkeypatch.setattr(mediapipe_detector, "detect_persons", lambda *a, **k: {
        "image_size": (800, 600), "detected_size": (800, 600),
        "detections": [{"bbox": (80, 60, 320, 560), "area": 120000, "confidence": 0.8,
                        "class_id": -1, "class_name": "mediapipe_face"}],
    })

    out = cropper.crop_characters_by_method(str(path), method="auto", margin_ratio=0.0,
                                            output_dir=str(root / "m"))

    assert out["crop_method"] == "mediapipe"
    assert len(out["characters"]) == 1
    assert out["characters"][0]["class_name"] == "mediapipe_face"
    assert out["characters"][0]["bbox"] == (80, 60, 320, 560)


def test_auto_falls_back_to_full_image(scene, monkeypatch):
    path, root = scene
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeYolo([]))
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: True)
    monkeypatch.setattr(mediapipe_detector, "detect_persons", lambda *a, **k: {
        "image_size": (800, 600), "detected_size": None, "detections": [],
    })

    out = cropper.crop_characters_by_method(str(path), method="auto", output_dir=str(root / "f"))

    assert out["crop_method"] == "full"
    assert out["characters"] == []
    assert out["image_size"] == (800, 600)


def test_mediapipe_only_skips_yolo(scene, monkeypatch):
    path, root = scene
    called = {"yolo": False}

    def _yolo(*args, **kwargs):
        called["yolo"] = True
        return {"image_size": (800, 600), "detected_size": None, "characters": []}

    monkeypatch.setattr("detection.yolo_detector.crop_characters", _yolo)
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: True)
    monkeypatch.setattr(mediapipe_detector, "detect_persons", lambda *a, **k: {
        "image_size": (800, 600), "detected_size": (800, 600),
        # 框要够大：裁剪门控默认要求面积占比 >= 6%（过小视为误检碎片被丢弃）
        "detections": [{"bbox": (10, 10, 400, 560), "area": 214500, "confidence": 0.5,
                        "class_id": -1, "class_name": "mediapipe_face"}],
    })

    out = cropper.crop_characters_by_method(str(path), method="mediapipe", margin_ratio=0.0,
                                            output_dir=str(root / "mp"))

    assert called["yolo"] is False
    assert out["crop_method"] == "mediapipe"


def test_mediapipe_unavailable_does_not_crash(scene, monkeypatch):
    path, root = scene
    monkeypatch.setattr("detection.yolo_detector.get_detector", lambda: FakeYolo([]))
    monkeypatch.setattr(mediapipe_detector, "is_available", lambda: False)
    monkeypatch.setattr(mediapipe_detector, "detect_persons", lambda *a, **k: {
        "image_size": (800, 600), "detected_size": None, "detections": [],
    })

    out = cropper.crop_characters_by_method(str(path), method="auto", output_dir=str(root / "x"))

    assert out["crop_method"] == "full"
    assert out["characters"] == []
