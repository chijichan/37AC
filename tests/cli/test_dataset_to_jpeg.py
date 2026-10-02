"""数据集转 JPEG：命名/跳过/删除原文件的规则。"""

import shutil
import uuid
from pathlib import Path

from PIL import Image

from utils.image_utils import convert_dataset_to_jpeg


def _root():
    base = Path(__file__).resolve().parents[2] / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("tojpeg-" + uuid.uuid4().hex[:8])
    (root / "原神" / "荧").mkdir(parents=True, exist_ok=True)
    return root


def test_converts_png_and_removes_original():
    root = _root()
    try:
        role = root / "原神" / "荧"
        Image.new("RGB", (300, 400), (10, 20, 30)).save(role / "a.png")
        Image.new("RGB", (300, 400), (10, 20, 30)).save(role / "b.webp")
        Image.new("RGB", (300, 400), (10, 20, 30)).save(role / "already.jpg")

        stats = convert_dataset_to_jpeg(str(root), quality=85, workers=1)

        names = sorted(p.name for p in role.iterdir())
        assert names == ["a.jpg", "already.jpg", "b.jpg"]
        assert stats["converted"] == 2
        assert stats["total"] == 2                     # jpg 不在待转列表里
        with Image.open(role / "a.jpg") as img:
            assert img.format == "JPEG"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_skips_when_target_exists():
    root = _root()
    try:
        role = root / "原神" / "荧"
        Image.new("RGB", (100, 100), (1, 2, 3)).save(role / "c.png")
        Image.new("RGB", (100, 100), (9, 9, 9)).save(role / "c.jpg")

        stats = convert_dataset_to_jpeg(str(root), quality=90, workers=1)

        assert stats["skipped"] == 1 and stats["converted"] == 0
        assert (role / "c.png").exists()               # 原文件不动，避免丢数据
    finally:
        shutil.rmtree(root, ignore_errors=True)
