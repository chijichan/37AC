"""源数据集「不处理列表」：命中的源目录直接当数据集用（不做 YOLO 裁剪）。"""

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
    root = base / ("no-crop-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_image(path: Path, size=(320, 480), color=(120, 60, 30)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


# ---------------- 列表匹配规则 ----------------

def test_match_exact_and_child(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [cfg._normalize_dataset_path(r"W:\Img\蔚蓝档案\_amazing")])

    assert cfg.is_in_no_crop_list(r"W:\Img\蔚蓝档案\_amazing")
    assert cfg.is_in_no_crop_list(r"W:\Img\蔚蓝档案\_amazing\子目录")     # 位于条目之下
    assert cfg.is_in_no_crop_list(r"w:/img/蔚蓝档案/_amazing")            # 大小写 + 斜杠不敏感
    assert not cfg.is_in_no_crop_list(r"W:\Img\蔚蓝档案\_amazing2")       # 相似前缀不算
    assert not cfg.is_in_no_crop_list(r"W:\Img\蔚蓝档案\白子")


def test_match_relative_path_resolves_against_dataset_dir(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_DIR", Path(r"W:\Img"))
    normalized = cfg._normalize_dataset_path(r"蔚蓝档案\_amazing")
    assert normalized == cfg._normalize_dataset_path(r"W:\Img\蔚蓝档案\_amazing")


def test_parse_multiple_entries(monkeypatch):
    entries = [p for p in r"W:\Img\A\_x;W:\Img\B\_y".split(";")]
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [cfg._normalize_dataset_path(p) for p in entries])
    assert cfg.is_in_no_crop_list(r"W:\Img\A\_x")
    assert cfg.is_in_no_crop_list(r"W:\Img\B\_y")
    assert not cfg.is_in_no_crop_list(r"W:\Img\C\_z")


def test_empty_list_matches_nothing(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [])
    assert not cfg.is_in_no_crop_list(r"W:\Img\蔚蓝档案\_amazing")


# ---------------- crop_dataset 行为 ----------------

class FakeDetector:
    """新版接口：内存内返回压缩后的字节（crop_dataset 直接写目标文件）。"""

    def __init__(self):
        self.calls = []

    def detect_and_crop_bytes(self, src_img, target_classes=None, max_size=0, quality=90,
                              margin_ratio=0.0, detect_max_size=0):
        self.calls.append(src_img)
        import io

        buf = io.BytesIO()
        Image.new("RGB", (60, 80), (200, 100, 50)).save(buf, format="JPEG")
        return buf.getvalue(), {"ext": ".jpg", "bbox": (0, 0, 60, 80), "confidence": 0.9}


@pytest.fixture
def source_tree():
    root = _root()
    src = root / "src"
    _make_image(src / "蔚蓝档案" / "_amazing" / "a.png")
    _make_image(src / "蔚蓝档案" / "_amazing" / "b.png")
    _make_image(src / "蔚蓝档案" / "白子" / "c.png")
    out = root / "out"
    yield src, out
    shutil.rmtree(root, ignore_errors=True)


def test_crop_dataset_skips_crop_for_listed_dir(source_tree, monkeypatch):
    src, out = source_tree
    fake = FakeDetector()
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [cfg._normalize_dataset_path(src / "蔚蓝档案" / "_amazing")])
    monkeypatch.setattr(cfg, "MAX_IMAGES_PER_ROLE", 100)

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=100)

    # 不处理列表里的角色：原图直接入集，没有 _37ac 后缀文件
    listed = sorted(p.name for p in (out / "蔚蓝档案" / "_amazing").iterdir())
    assert listed == ["a.png", "b.png"]
    assert stats["no_crop"] == 2
    # 普通角色：走上 YOLO 裁剪（内存直出，统一 JPEG）
    normal = sorted(p.name for p in (out / "蔚蓝档案" / "白子").iterdir())
    assert normal == ["c_37ac.jpg"]
    assert len(fake.calls) == 1
    assert stats["processed"] == 3


def test_crop_dataset_without_list_crops_everything(source_tree, monkeypatch):
    src, out = source_tree
    fake = FakeDetector()
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_NO_CROP_DIRS", [])

    stats = YD.crop_dataset(str(src), str(out), max_images_per_role=100)

    assert stats["no_crop"] == 0
    assert sorted(p.name for p in (out / "蔚蓝档案" / "_amazing").iterdir()) == ["a_37ac.jpg", "b_37ac.jpg"]
    assert len(fake.calls) == 3
