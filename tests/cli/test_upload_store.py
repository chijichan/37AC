"""uploads 治理：任务/通道命名 + 内容去重 + 启动清扫。"""
import os
import time
from pathlib import Path

import pytest

from services import node_service as NS


@pytest.fixture
def env(monkeypatch, tmp_path_factory):
    root = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests" / ("uploads-" + str(int(time.time() * 1000)))
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(NS, "IMAGE_PATH", str(root))
    yield root
    import shutil
    shutil.rmtree(root, ignore_errors=True)


def test_filename_carries_task_and_channel(env):
    data = b"IMAGE-BYTES"
    p1 = NS._store_task_image(data, "abc123:37ac", "37ac", ".jpg")
    assert os.path.basename(p1).startswith("abc123_37ac_")
    assert os.path.basename(p1).endswith(".jpg")


def test_same_content_stored_once(env):
    data = b"SAME-IMAGE"
    p1 = NS._store_task_image(data, "parent:37ac", "37ac", ".jpg")
    p2 = NS._store_task_image(data, "parent:llm", "llm", ".jpg")     # 多通道扇出
    assert p1 == p2, "同内容应复用同一个文件"
    assert len(list(env.glob("*.jpg"))) == 1, "磁盘上只应有一份"


def test_task_id_sanitized_against_traversal(env):
    p = NS._store_task_image(b"X", "../../evil/../id", None, ".jpg")
    name = os.path.basename(p)
    assert "/" not in name and "\\" not in name and ".." not in name
    assert Path(p).parent == env


def test_sweep_removes_old_keeps_new(env, monkeypatch):
    old = env / "old_0000000000.jpg"
    new = env / "new_1111111111.jpg"
    old.write_bytes(b"OLD")
    new.write_bytes(b"NEW")
    past = time.time() - 10 * 86400
    os.utime(old, (past, past))

    removed = NS._sweep_uploads(min_age_sec=86400)

    assert removed == 1
    assert not old.exists() and new.exists()


def test_duplicate_after_sweep_rewrites(env):
    data = b"REWRITE-ME"
    p1 = NS._store_task_image(data, "t1", None, ".jpg")
    os.remove(p1)                                    # 模拟被清扫掉
    p2 = NS._store_task_image(data, "t1", None, ".jpg")
    assert Path(p2).exists()
