"""源数据集「不处理列表」：命中的目录完全忽略（不进数据集）。"""

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
    root = base / ("ignore-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class BytesDetector:
    def __init__(self, fail=()):
        self.fail = set(fail)
        self.calls = []

    def detect_and_crop_bytes(self, src_img, target_classes=None, max_size=0, quality=90,
                              margin_ratio=0.0, detect_max_size=0):
        import io

        self.calls.append(Path(src_img).name)
        if Path(src_img).name in self.fail:
            return None, None
        buf = io.BytesIO()
        Image.new("RGB", (60, 80), (200, 100, 50)).save(buf, format="JPEG")
        return buf.getvalue(), {"ext": ".jpg", "bbox": (0, 0, 60, 80), "confidence": 0.9}


# ---------------- 列表匹配 ----------------

def test_match_exact_and_child(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS",
                        [cfg._normalize_dataset_path(r"W:\Img\蔚蓝档案\_amazing")])

    assert cfg.is_in_ignore_list(r"W:\Img\蔚蓝档案\_amazing")
    assert cfg.is_in_ignore_list(r"W:\Img\蔚蓝档案\_amazing\子目录")     # 位于条目之下
    assert cfg.is_in_ignore_list(r"w:/img/蔚蓝档案/_amazing")           # 大小写 + 斜杠不敏感
    assert not cfg.is_in_ignore_list(r"W:\Img\蔚蓝档案\_amazing2")      # 相似前缀不算
    assert not cfg.is_in_ignore_list(r"W:\Img\蔚蓝档案\白子")


def test_relative_path_resolves_against_dataset_dir(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_DIR", Path(r"W:\Img"))
    assert cfg._normalize_dataset_path(r"蔚蓝档案\_amazing") == cfg._normalize_dataset_path(
        r"W:\Img\蔚蓝档案\_amazing")


def test_empty_list_matches_nothing(monkeypatch):
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS", [])
    assert not cfg.is_in_ignore_list(r"W:\Img\蔚蓝档案\_amazing")


# ---------------- crop_dataset：命中即完全不管 ----------------

@pytest.fixture
def tree():
    root = _root()
    dataset = root / "src"
    for role in ("_amazing", "白子"):
        d = dataset / "蔚蓝档案" / role
        d.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 300), (5, 5, 5)).save(d / "a.png")
    yield dataset, root / "out"
    shutil.rmtree(root, ignore_errors=True)


def _patch(monkeypatch, fake, clean=True):
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_QUALITY", 90)
    monkeypatch.setattr(cfg, "DATASET_FILL_UNCROPPED", True)
    monkeypatch.setattr(cfg, "DATASET_IGNORE_CLEAN", clean)
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS",
                        [cfg._normalize_dataset_path(r"W:\Img\蔚蓝档案\_amazing")])


def test_ignored_dir_is_skipped_entirely(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)
    # 让忽略判断对得上临时目录
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS",
                        [cfg._normalize_dataset_path(dataset / "蔚蓝档案" / "_amazing")])

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10)

    # 完全不管：输出目录里没有 _amazing，也没有整图补齐
    assert not (out / "蔚蓝档案" / "_amazing").exists()
    # 检测器只为另一个角色调用过
    assert fake.calls == ["a.png"] or fake.calls == []
    assert stats["ignored"] == 1
    assert stats["processed"] >= 1


def test_ignored_dir_cleans_stale_output(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS",
                        [cfg._normalize_dataset_path(dataset / "蔚蓝档案" / "_amazing")])
    stale = out / "蔚蓝档案" / "_amazing"
    stale.mkdir(parents=True, exist_ok=True)
    (stale / "old_37ac.jpg").write_bytes(b"OLD")

    YD.crop_dataset(str(dataset), str(out), max_images_per_role=10)

    assert not stale.exists()          # 旧产物被清理


def test_ignored_dir_keeps_stale_output_when_clean_disabled(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake, clean=False)
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS",
                        [cfg._normalize_dataset_path(dataset / "蔚蓝档案" / "_amazing")])
    stale = out / "蔚蓝档案" / "_amazing"
    stale.mkdir(parents=True, exist_ok=True)
    (stale / "old_37ac.jpg").write_bytes(b"OLD")

    YD.crop_dataset(str(dataset), str(out), max_images_per_role=10)

    assert (stale / "old_37ac.jpg").read_bytes() == b"OLD"     # 只跳过、不删
