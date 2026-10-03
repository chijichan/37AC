"""指定角色裁剪：only_roles 过滤 + reset_roles 清空旧产物。"""

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
    root = base / ("only-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class BytesDetector:
    def __init__(self):
        self.calls = []

    def detect_and_crop_bytes(self, src_img, target_classes=None, max_size=0, quality=90,
                              margin_ratio=0.0, detect_max_size=0):
        import io

        self.calls.append(str(src_img))
        buf = io.BytesIO()
        Image.new("RGB", (40, 60), (10, 20, 30)).save(buf, format="JPEG")
        return buf.getvalue(), {"ext": ".jpg", "bbox": (0, 0, 40, 60), "confidence": 0.9}


# ---------------- 匹配规则 ----------------

def test_role_matches_variants():
    assert YD._role_matches("蔚蓝档案/白子", ["蔚蓝档案/白子"])          # 完整
    assert YD._role_matches("蔚蓝档案/白子", ["白子"])                  # 只写角色名
    assert YD._role_matches("蔚蓝档案/白子", ["档案/白"])               # 子串
    assert YD._role_matches("蔚蓝档案/白子", ["蔚蓝档案/*"])            # 通配符
    assert YD._role_matches("蔚蓝档案/白子", ["*白子*"])                # 两端通配
    assert YD._role_matches("Piapro_Characters/初音未来", ["piapro_characters/初音未来"])  # 大小写
    assert not YD._role_matches("蔚蓝档案/白子", ["原神/荧"])
    assert not YD._role_matches("蔚蓝档案/白子", ["   "])               # 空模式忽略


# ---------------- 只裁指定角色 ----------------

@pytest.fixture
def tree():
    root = _root()
    dataset = root / "src"
    for ip, role in (("蔚蓝档案", "白子"), ("蔚蓝档案", "星野"), ("原神", "荧")):
        d = dataset / ip / role
        d.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 300), (5, 5, 5)).save(d / "a.png")
    yield dataset, root / "out"
    shutil.rmtree(root, ignore_errors=True)


def _patch(monkeypatch, fake):
    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_get_thread_detector", lambda: fake)
    monkeypatch.setattr(YD, "_new_detector", lambda: fake)
    fake._load_model = lambda: True
    fake.load_error = ""
    monkeypatch.setattr(cfg, "YOLO_CROP_WORKERS", 1)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_SIZE", 0)
    monkeypatch.setattr(cfg, "DATASET_COMPRESS_QUALITY", 90)
    monkeypatch.setattr(cfg, "DATASET_FILL_UNCROPPED", True)
    monkeypatch.setattr(cfg, "DATASET_IGNORE_DIRS", [])


def test_only_roles_crops_selected_and_skips_others(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10,
                            only_roles=["蔚蓝档案/白子"])

    assert stats["matched_roles"] == 1
    assert (out / "蔚蓝档案" / "白子").exists()
    assert not (out / "蔚蓝档案" / "星野").exists()      # 未选中的角色完全不碰
    assert not (out / "原神" / "荧").exists()
    assert len(fake.calls) == 1                          # 只为选中的角色跑了检测


def test_only_roles_supports_role_name_and_wildcard(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10,
                            only_roles=["星野", "原神/*"])

    assert stats["matched_roles"] == 2
    assert (out / "蔚蓝档案" / "星野").exists()
    assert (out / "原神" / "荧").exists()
    assert not (out / "蔚蓝档案" / "白子").exists()


def test_no_match_writes_nothing(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)

    stats = YD.crop_dataset(str(dataset), str(out), max_images_per_role=10,
                            only_roles=["不存在的角色"])

    assert stats["matched_roles"] == 0 and stats["processed"] == 0
    assert fake.calls == []
    assert not out.exists()


def test_reset_roles_clears_only_selected_output(tree, monkeypatch):
    dataset, out = tree
    fake = BytesDetector()
    _patch(monkeypatch, fake)
    # 预置旧产物：选中的角色有脏数据，未选中的也要保留
    (out / "蔚蓝档案" / "白子").mkdir(parents=True)
    (out / "蔚蓝档案" / "白子" / "old_37ac.jpg").write_bytes(b"OLD")
    (out / "原神" / "荧").mkdir(parents=True)
    (out / "原神" / "荧" / "keep_37ac.jpg").write_bytes(b"KEEP")

    YD.crop_dataset(str(dataset), str(out), max_images_per_role=10,
                    only_roles=["白子"], reset_roles=True)

    names = sorted(p.name for p in (out / "蔚蓝档案" / "白子").iterdir())
    assert names == ["a_37ac.jpg"]                       # 旧产物被清掉、重新裁
    assert (out / "原神" / "荧" / "keep_37ac.jpg").exists()   # 其它角色原样保留
