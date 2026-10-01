"""数据集裁剪走"内存直出"：不落临时文件、从原图裁剪、压缩后直写数据集目录。"""

import io
import shutil
import uuid
from pathlib import Path

import pytest
from PIL import Image

from config import base as cfg
from detection import yolo_detector as YD


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("memcrop-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------- 检测器：从原图裁剪 + 坐标映射 ----------------

def test_detect_and_crop_bytes_maps_bbox_and_crops_from_original(monkeypatch):
    root = _root()
    try:
        src = root / "big.png"
        Image.new("RGB", (1000, 500), (10, 20, 30)).save(src)

        det = YD.YoloDetector()
        det._loaded = True          # 跳过模型加载
        # 检测发生在缩略图上（500x250），框用缩略图坐标
        monkeypatch.setattr(det, "detect", lambda image: [
            {"bbox": (100, 50, 300, 250), "confidence": 0.9, "class_id": 0, "class_name": "person"}
        ])

        data, info = det.detect_and_crop_bytes(
            str(src), target_classes=["person"], max_size=0, detect_max_size=500
        )

        assert info["image_size"] == (1000, 500)        # 原图尺寸
        assert info["detected_size"] == (500, 250)      # 检测用缩略图
        assert info["bbox"] == (200, 100, 600, 500)     # 框已按比例映射回原图
        assert info["ext"] == ".jpg" and data
        # 关键：从**原图**裁 400x400（若从缩略图裁只有 200x200）
        with Image.open(io.BytesIO(data)) as out:
            assert out.size == (400, 400)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_detect_and_crop_bytes_compresses_to_max_size(monkeypatch):
    root = _root()
    try:
        src = root / "big.png"
        Image.new("RGB", (1000, 500), (10, 20, 30)).save(src)
        det = YD.YoloDetector()
        det._loaded = True
        monkeypatch.setattr(det, "detect", lambda image: [
            {"bbox": (0, 0, 500, 250), "confidence": 0.8, "class_id": 0, "class_name": "person"}
        ])

        data, info = det.detect_and_crop_bytes(str(src), max_size=200, quality=80, detect_max_size=500)

        with Image.open(io.BytesIO(data)) as out:
            assert out.size == (200, 100)               # 最长边压到 200
            assert out.format == "JPEG"
        assert info["bytes"] == len(data)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_detect_and_crop_bytes_returns_none_without_detection(monkeypatch):
    root = _root()
    try:
        src = root / "none.png"
        Image.new("RGB", (300, 300), (1, 2, 3)).save(src)
        det = YD.YoloDetector()
        det._loaded = True
        monkeypatch.setattr(det, "detect", lambda image: [])

        assert det.detect_and_crop_bytes(str(src)) == (None, None)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------- crop_dataset：直写数据集目录 ----------------

class BytesDetector:
    def __init__(self, payload=b"FAKE-JPEG-BYTES", fail=()):
        self.payload = payload
        self.fail = set(fail)
        self.calls = []

    def detect_and_crop_bytes(self, src_img, target_classes=None, max_size=0, quality=90,
                              margin_ratio=0.0, detect_max_size=0):
        self.calls.append({"src": Path(src_img).name, "max_size": max_size, "quality": quality})
        if Path(src_img).name in self.fail:
            return None, None
        return self.payload, {"ext": ".jpg", "bbox": (0, 0, 10, 10), "confidence": 0.9}


@pytest.fixture
def tree():
    root = _root()
    dataset = root / "src"
    role = dataset / "原神" / "荧"
    role.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (200, 300), (5, 5, 5)).save(role / "a.png")
    yield dataset, root / "out"
    shutil.rmtree(root, ignore_errors=True)


def test_crop_dataset_writes_bytes_directly(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector(payload=b"DIRECT-JPEG")
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 512)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_QUALITY", 88)
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [])
    monkeypatch.setattr(cfg, "DATASET_FILL_UNCROPPED", True)

    # 任何临时目录创建都视为回归（新流程不该再落临时文件）
    def _no_temp(*args, **kwargs):
        raise AssertionError("不应再创建临时目录")

    monkeypatch.setattr("tempfile.mkdtemp", _no_temp)

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10)

    written = out / "原神" / "荧" / "a_37ac.jpg"
    assert written.exists()
    assert written.read_bytes() == b"DIRECT-JPEG"        # 字节直写，没被改写
    assert stats["processed"] == 1
    # 压缩参数透传给检测器
    assert fake.calls == [{"src": "a.png", "max_size": 512, "quality": 88}]


def test_crop_dataset_skips_when_output_exists(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [])
    # 已经裁过（jpng 命名也要能识别，兼容旧产物）
    (out / "原神" / "荧").mkdir(parents=True, exist_ok=True)
    (out / "原神" / "荧" / "a_37ac.jpg").write_bytes(b"OLD")

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10)

    assert fake.calls == []                              # 不重复处理
    assert (out / "原神" / "荧" / "a_37ac.jpg").read_bytes() == b"OLD"
    assert stats["skipped"] >= 1
