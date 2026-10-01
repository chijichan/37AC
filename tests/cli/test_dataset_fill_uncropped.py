"""数据集裁剪不足时用整图压缩补足（DATASET_FILL_UNCROPPED）。"""

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
    root = base / ("fill-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeDetector:
    """failing 里的文件名返回"没检出人物"（None, None）。"""

    def __init__(self, failing=()):
        self.failing = set(failing)
        self.calls = []

    def detect_and_crop(self, src_img, target_classes=None, suffix="_37ac", max_size=None):
        self.calls.append(Path(src_img).name)
        if Path(src_img).name in self.failing:
            return None, None
        out = Path(src_img).with_name(Path(src_img).stem + suffix + Path(src_img).suffix)
        shutil.copy2(src_img, out)
        return str(out), {"bbox": [0, 0, 10, 10]}


@pytest.fixture
def tree():
    """crop_dataset 接收的是数据集根目录（内部按 IP/角色 两层遍历）。"""
    root = _root()
    dataset_root = root / "src"
    role = dataset_root / "原神" / "荧"
    role.mkdir(parents=True, exist_ok=True)
    # 每张尺寸不同，确保"按文件大小降序"处理时顺序可控
    for i in range(6):
        Image.new("RGB", (200 + i * 20, 300), (10 * i, 60, 90)).save(role / ("img%d.png" % i))
    yield dataset_root, root / "out"
    shutil.rmtree(root, ignore_errors=True)


def _patch(monkeypatch, fake, cap, fill=True):
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [])
    monkeypatch.setattr(cfg, "DATASET_FILL_UNCROPPED", fill)
    return cap


def _counts(out_dir: Path):
    files = sorted(p.name for p in out_dir.iterdir())
    return [f for f in files if "_37ac" in f], [f for f in files if "_37ac" not in f]


def test_all_crops_fail_fills_with_whole_images(tree, monkeypatch):
    src, out = tree
    fake = FakeDetector(failing={"img%d.png" % i for i in range(6)})
    _patch(monkeypatch, fake, 10)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=10)

    cropped, whole = _counts(out / "原神" / "荧")
    assert cropped == []                      # 一张都没裁出来
    assert len(whole) == 6                    # 全部用整图补足
    assert stats["whole"] == 6
    assert stats["processed"] == 6


def test_fill_respects_cap(tree, monkeypatch):
    src, out = tree
    fake = FakeDetector(failing={"img%d.png" % i for i in range(6)})
    _patch(monkeypatch, fake, 4)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=4)

    cropped, whole = _counts(out / "原神" / "荧")
    assert len(whole) == 4                    # 上限 4，不会多存
    assert stats["whole"] == 4


def test_crops_take_priority_over_whole(tree, monkeypatch):
    src, out = tree
    # 4 张能裁、2 张失败，上限 4 → 应当全是裁剪图，不掺整图
    fake = FakeDetector(failing={"img0.png", "img1.png"})
    _patch(monkeypatch, fake, 4)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=4)

    cropped, whole = _counts(out / "原神" / "荧")
    assert len(cropped) == 4
    assert whole == []
    assert stats["whole"] == 0


def test_partial_fill(tree, monkeypatch):
    src, out = tree
    # 3 张能裁、3 张失败，上限 10 → 3 张裁剪 + 3 张整图
    fake = FakeDetector(failing={"img0.png", "img1.png", "img2.png"})
    _patch(monkeypatch, fake, 10)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=10)

    cropped, whole = _counts(out / "原神" / "荧")
    assert len(cropped) == 3 and len(whole) == 3
    assert stats["whole"] == 3
    assert stats["processed"] == 6


def test_fill_disabled_keeps_old_behaviour(tree, monkeypatch):
    src, out = tree
    fake = FakeDetector(failing={"img0.png", "img1.png", "img2.png"})
    _patch(monkeypatch, fake, 10, fill=False)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=10)

    cropped, whole = _counts(out / "原神" / "荧")
    assert len(cropped) == 3 and whole == []
    assert stats["whole"] == 0
    assert stats["skipped"] >= 3              # 未使用的失败样本按旧口径记 skipped
