"""检查点服务：快照 / 列表 / 回滚 / 删除 / 清理。"""

import json
import shutil
import uuid
from pathlib import Path

import pytest

from services import checkpoint_service as CS


def _make_model_dir(root: Path, version="0.0.12", weights=b"WEIGHTS-V1", classes=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "37ac-v0.0.1.pth").write_bytes(weights)
    (root / "classes.json").write_text(
        json.dumps(classes or {"原神/荧": {"id": 1}}, ensure_ascii=False), encoding="utf-8")
    (root / "config.json").write_text(json.dumps(
        {"version": version, "model": {"file": "37ac-v0.0.1.pth", "sha256": "ABC"}}, ensure_ascii=False),
        encoding="utf-8")
    return root


@pytest.fixture
def env(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    root.mkdir(parents=True, exist_ok=True)
    work = root / ("ckpt-" + uuid.uuid4().hex[:8])
    model_dir = _make_model_dir(work / "models")
    monkeypatch.setattr(CS, "MODEL_DIR", model_dir)
    monkeypatch.setattr(CS, "MODEL_FILENAME", "37ac-v0.0.1.pth")
    monkeypatch.setattr(CS, "CLASSES_JSON_PATH", model_dir / "classes.json")
    monkeypatch.setattr(CS, "MODEL_INFO_PATH", model_dir / "config.json")
    yield {"dir": model_dir, "work": work}
    shutil.rmtree(work, ignore_errors=True)


def test_create_snapshots_all_three_files(env):
    meta = CS.create_checkpoint(kind="best", version="0.0.12", accuracy=91.5)

    assert meta["kind"] == "best" and meta["accuracy"] == 91.5
    snap = CS.checkpoint_dir() / meta["name"]
    for name in ("37ac-v0.0.1.pth", "classes.json", "config.json", "meta.json"):
        assert (snap / name).exists(), name

    items = CS.list_checkpoints()
    assert [it["name"] for it in items] == [meta["name"]]
    assert items[0]["exists"] is True


def test_version_taken_from_config_when_not_given(env):
    meta = CS.create_checkpoint(kind="final")
    assert meta["version"] == "0.0.12"
    assert meta["name"].startswith("0.0.12-")


def test_restore_reverts_all_and_keeps_pre_restore(env):
    first = CS.create_checkpoint(kind="best", version="0.0.12", accuracy=90)

    # 制造"新状态"：权重与类别都换了
    (env["dir"] / "37ac-v0.0.1.pth").write_bytes(b"WEIGHTS-V2")
    (env["dir"] / "classes.json").write_text('{"原神/荧": {"id": 1}, "原神/胡桃": {"id": 2}}', encoding="utf-8")

    result = CS.restore_checkpoint(first["name"])

    assert (env["dir"] / "37ac-v0.0.1.pth").read_bytes() == b"WEIGHTS-V1"
    assert "原神/胡桃" not in (env["dir"] / "classes.json").read_text(encoding="utf-8")
    assert result["backup"], "回滚前应自动建 pre-restore 检查点"
    kinds = {it["kind"] for it in CS.list_checkpoints()}
    assert "pre-restore" in kinds


def test_protected_checkpoints_survive_prune(env):
    CS.create_checkpoint(kind="baseline", version="0.0.11")
    names = []
    for i in range(4):
        m = CS.create_checkpoint(kind="final", version="0.0.1%d" % i)
        names.append(m["name"])

    result = CS.prune(keep=1, max_total_mb=1e9)

    left = {it["name"] for it in CS.list_checkpoints()}
    assert any(it["kind"] == "baseline" for it in CS.list_checkpoints())
    assert len(left) == 2                       # baseline + 最近 1 个
    assert result["removed"], "应删掉多余检查点"


def test_delete_protected_requires_force(env):
    meta = CS.create_checkpoint(kind="baseline")
    assert CS.delete_checkpoint(meta["name"]) is False
    assert CS.delete_checkpoint(meta["name"], force=True) is True
    assert CS.list_checkpoints() == []


def test_current_info(env):
    # 造一个够大的权重（几字节的文件四舍五入后是 0.0 MB）
    (env["dir"] / "37ac-v0.0.1.pth").write_bytes(b"W" * (200 * 1024))
    info = CS.current_info()
    assert info["version"] == "0.0.12"
    assert info["class_count"] == 1
    assert info["model_exists"] is True and info["model_size_mb"] > 0
    # 基模取自 config.json 的 training.base；老模型没有该字段时给出明确提示
    assert info["base"] == "未知（旧模型无记录）"


def test_create_skips_when_no_weights(env):
    (env["dir"] / "37ac-v0.0.1.pth").unlink()
    assert CS.create_checkpoint(kind="best") is None
    assert CS.list_checkpoints() == []
