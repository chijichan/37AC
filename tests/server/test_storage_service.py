"""图片缓存/临时文件系统（services/storage_service.py）回归测试。"""

import io
import os
import shutil
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from config import base as cfg
from services import storage_service


def _png(size=(64, 48), color=(255, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _noise_png(size=(800, 600)):
    """噪声图：PNG 体积大且几乎不可无损压缩，便于测容量回收。"""
    raw = os.urandom(size[0] * size[1] * 3)
    buf = io.BytesIO()
    Image.frombytes("RGB", size, raw).save(buf, format="PNG")
    return buf.getvalue()


def _size_of(data):
    with Image.open(io.BytesIO(data)) as img:
        return img.size


def _make_root() -> Path:
    """测试根目录（src/cli/saves/tmp/.tmp-tests/，已 gitignore）。

    不用 pytest 的 tmp_path：受限文件沙箱下系统 TEMP 只能创建顶层目录、
    再往里建子目录会 PermissionError（实测），而仓库内路径可正常读写。
    """
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    # 注意：不要用 tempfile.mkdtemp —— 本环境（受限文件沙箱）里 mkdtemp 出来的目录
    # 之后无法再建子目录/写入（WinError 5），普通 mkdir 则正常。
    root = base / ("store-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def store(monkeypatch):
    root = _make_root()
    dirs = {"tmp": root / "tmp", "cache": root / "cache"}
    monkeypatch.setattr(cfg, "IMAGE_TMP_PATH", dirs["tmp"])
    monkeypatch.setattr(cfg, "IMAGE_CACHE_PATH", dirs["cache"])

    over = {"max_bytes": {}, "ttl": {}, "protect": {}, "compress_max_side": 512, "quality": 85}
    real_limits = storage_service._limits

    def fake_limits(label):
        limits = real_limits(label)
        limits["max_bytes"] = over["max_bytes"].get(label, limits["max_bytes"])
        limits["ttl"] = over["ttl"].get(label, limits["ttl"])
        limits["protect"] = over["protect"].get(label, limits["protect"])
        limits["compress_max_side"] = over["compress_max_side"]
        return limits

    monkeypatch.setattr(storage_service, "_limits", fake_limits)
    # 测试里不需要写入触发的异步回收，保持确定性
    monkeypatch.setattr(storage_service, "_trigger_cleanup_if_needed", lambda label: None)

    storage_service.ensure_dirs()
    yield SimpleNamespace(dirs=dirs, over=over, root=root)
    shutil.rmtree(root, ignore_errors=True)


# ---------------- 基础读写 ----------------

def test_save_temp_and_find(store):
    data = _png()
    path = storage_service.save_temp("t-1", data, ".png")

    assert path is not None and path.exists()
    assert path.parent == store.dirs["tmp"]
    assert path.read_bytes() == data

    found, source = storage_service.find_image("t-1")
    assert source == "tmp"
    assert found == path


def test_prefer_cache_order(store):
    storage_service.save_temp("t-2", _png(), ".png")
    storage_service.save_cache("t-2", _png(), ".png")

    path, source = storage_service.find_image("t-2", prefer="cache")
    assert source == "cache"
    path, source = storage_service.find_image("t-2", prefer="tmp")
    assert source == "tmp"


def test_invalid_task_id_rejected(store):
    assert storage_service.save_temp("../evil", _png(), ".png") is None
    assert storage_service.save_temp("a/b", _png(), ".png") is None
    assert storage_service.save_temp("", _png(), ".png") is None
    assert storage_service.normalize_task_id("..%2f") == ""
    assert storage_service.normalize_task_id("normal-uuid-123") == "normal-uuid-123"


@pytest.mark.parametrize("label,setting", [
    ("tmp", "IMAGE_TMP_PATH"),
    ("cache", "IMAGE_CACHE_PATH"),
])
def test_storage_directory_cannot_be_project_root(label, setting, monkeypatch):
    project_root = Path(storage_service.__file__).resolve().parents[3]
    monkeypatch.setattr(cfg, setting, project_root)

    with pytest.raises(ValueError, match="项目根目录"):
        storage_service._dir(label)


def test_unknown_extension_falls_back_to_jpg(store):
    path = storage_service.save_temp("t-3", _png(), ".exe")
    assert path.suffix == ".jpg"


# ---------------- cache 压缩策略 ----------------

def test_cache_keeps_small_image_as_is(store):
    data = _png(size=(120, 90))
    path = storage_service.save_cache("t-4", data, ".png")

    assert path.name == "t-4.png"
    assert path.read_bytes() == data        # 不需要压缩就不做二次有损编码


def test_cache_compresses_large_image(store):
    data = _png(size=(1200, 800))
    path = storage_service.save_cache("t-5", data, ".png")

    assert path.name == "t-5.jpg"
    payload = path.read_bytes()
    assert max(_size_of(payload)) <= 512
    assert len(payload) < len(data)


def test_cache_replaces_previous_extension(store):
    storage_service.save_cache("t-6", _png(size=(120, 90)), ".png")
    storage_service.save_cache("t-6", _png(size=(1200, 800)), ".png")

    files = [p.name for p in store.dirs["cache"].iterdir()]
    assert files == ["t-6.jpg"]


def test_read_bytes_resizes_on_demand(store):
    storage_service.save_cache("t-7", _png(size=(1200, 800)), ".png")

    data, source, mimetype = storage_service.read_bytes("t-7", max_side=200)
    assert source == "cache" and mimetype == "image/jpeg"
    assert max(_size_of(data)) <= 200

    data2, _source, mimetype2 = storage_service.read_bytes("t-7")
    assert mimetype2 == "image/jpeg"
    assert max(_size_of(data2)) <= 512


def test_read_missing_returns_empty(store):
    assert storage_service.read_bytes("nope") == (None, "", "")


# ---------------- 回收 ----------------

def test_cleanup_removes_expired(store):
    path = storage_service.save_temp("old-1", _png(), ".png")
    old = time.time() - 7200
    os.utime(path, (old, old))
    store.over["ttl"]["tmp"] = 60
    store.over["protect"]["tmp"] = 0

    result = storage_service.cleanup()
    assert result["tmp"]["expired"] == 1
    assert not path.exists()


def test_cleanup_keeps_files_inside_protect_window(store):
    path = storage_service.save_temp("fresh-1", _png(), ".png")
    store.over["ttl"]["tmp"] = 1          # 立刻过期
    store.over["protect"]["tmp"] = 3600   # 但保护窗口更长

    storage_service.cleanup()
    assert path.exists()


def test_cleanup_compresses_before_evicting(store):
    # 直接落盘一张超限大图（绕过 save_cache 的写入期压缩），让 cleanup 去压缩它
    path = store.dirs["cache"] / "big-1.png"
    path.write_bytes(_noise_png(size=(1600, 1200)))
    assert path.stat().st_size > 1024 * 1024
    store.over["max_bytes"]["cache"] = 1024 * 1024     # 上限 1MB

    result = storage_service.cleanup()
    assert result["cache"]["compressed"] >= 1
    assert result["cache"]["evicted"] == 0
    assert result["cache"]["bytes"] <= 1024 * 1024
    assert not path.exists()                           # 压缩后换成了 .jpg


def test_cleanup_evicts_oldest_first_when_still_over(store):
    # 非法图片内容 -> 无法压缩，逼出「按权重淘汰」这条路径
    first = store.dirs["tmp"] / "old-a.png"
    second = store.dirs["tmp"] / "new-b.png"
    first.write_bytes(os.urandom(300 * 1024))
    second.write_bytes(os.urandom(300 * 1024))
    old = time.time() - 3600
    os.utime(first, (old, old))

    store.over["max_bytes"]["tmp"] = 400 * 1024
    store.over["ttl"]["tmp"] = 0            # 关掉 TTL，只测容量淘汰
    store.over["protect"]["tmp"] = 0

    result = storage_service.cleanup()
    assert result["tmp"]["evicted"] >= 1
    assert not first.exists()               # 更老的先被淘汰
    assert second.exists()
    assert result["tmp"]["bytes"] <= 400 * 1024


def test_stats_reports_both_dirs(store):
    storage_service.save_temp("s-1", _png(), ".png")
    storage_service.save_cache("s-2", _png(), ".png")

    info = storage_service.stats()
    assert set(info) == {"tmp", "cache"}
    assert info["tmp"]["files"] == 1 and info["tmp"]["bytes"] > 0
    assert info["cache"]["files"] == 1
    assert info["cache"]["compress_max_side"] == 512


def test_weight_prefers_recent_and_large():
    ttl = 3600
    assert storage_service._weight(1000, 0, ttl) > storage_service._weight(1000, ttl, ttl)
    assert storage_service._weight(2000, 100, ttl) > storage_service._weight(1000, 100, ttl)
