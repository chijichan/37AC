"""训练报告：progress.json 契约 + HTML 渲染 + run 列表。"""

import json
import shutil
import uuid
from pathlib import Path

import pytest

from services import report_service as RS


@pytest.fixture
def env(monkeypatch):
    root = Path(__file__).resolve().parents[2] / ".tmp-tests"
    root.mkdir(parents=True, exist_ok=True)
    work = root / ("report-" + uuid.uuid4().hex[:8])
    monkeypatch.setattr(RS, "REPORT_DIR", work)
    monkeypatch.setattr(RS, "REPORT_ENABLED", True)
    monkeypatch.setattr(RS, "REPORT_REFRESH_SEC", 5)
    RS._STATE["run_dir"] = None
    RS._STATE["data"] = None
    yield work
    RS._STATE["run_dir"] = None
    RS._STATE["data"] = None
    shutil.rmtree(work, ignore_errors=True)


def _load(folder):
    return json.loads((folder / "progress.json").read_text(encoding="utf-8"))


def test_start_run_writes_progress_and_html(env):
    folder = RS.start_run({"version": "0.0.17", "base": "dbv4-resnet18", "classes": 181,
                           "train": 15061, "val": 1673, "batch": 32, "image_size": 224,
                           "device": "privateuseone:0"}, version="0.0.17")

    assert folder.is_dir() and folder.parent == env
    data = _load(folder)
    assert data["status"] == "running" and data["run_id"] == folder.name
    assert data["meta"]["base"] == "dbv4-resnet18"
    html = (folder / "index.html").read_text(encoding="utf-8")
    assert '<meta http-equiv="refresh" content="5">' in html
    assert "每 5 秒自动刷新" in html
    assert "file:// 硬刷新 / http:// 软刷新" not in html
    assert "jsstat" not in html
    assert "图表交互已启用" not in html
    assert "JS v12 已运行" not in html
    assert "dbv4-resnet18" in html and "181" in html


def test_epochs_and_charts(env):
    folder = RS.start_run({"version": "0.0.17"}, version="0.0.17")
    for i in range(1, 6):
        RS.record_epoch(i, "P1", 5.0 - i * 0.2, 2.0 + i, 5.0 + i * 3, 1e-3, secs=210)

    data = _load(folder)
    assert len(data["epochs"]) == 5
    html = (folder / "index.html").read_text(encoding="utf-8")
    # 准确率图 = train + val 两条折线；损失图 = 1 条 → 共 3 条
    assert html.count("<polyline") == 3
    assert '准确率（每轮 %）' in html and ">train<" in html and ">val<" in html
    assert "17.00%" in html or "17.0" in html               # 第 5 轮 val
    assert "5.00%" in html or "5.0" in html


def test_checkpoints_events_status(env, monkeypatch):
    folder = RS.start_run({"version": "0.0.17"}, version="0.0.17")
    RS.add_checkpoint("0.0.17-x-best", "best", accuracy=42.31, size_mb=43.2)
    RS.add_event("早停触发")
    RS.set_status("finished", "训练完成")

    data = _load(folder)
    assert data["status"] == "finished"
    assert data["checkpoints"][0]["kind"] == "best" and data["checkpoints"][0]["accuracy"] == 42.31
    assert any("早停" in e["text"] for e in data["events"])
    html = (folder / "index.html").read_text(encoding="utf-8")
    assert "42.31%" in html and "已完成" in html and "早停触发" in html


def test_atomic_write_leaves_no_tmp(env):
    folder = RS.start_run({"version": "0.0.17"})
    RS.record_epoch(1, "P1", 4.0, 3.0, 6.0, 1e-3, secs=100)
    assert not list(folder.glob("*.tmp")), "原子写不应残留 .tmp"


def test_list_and_latest_run(env):
    first = RS.start_run({"version": "0.0.1"}, version="0.0.1")
    RS._STATE["run_dir"] = None
    RS._STATE["data"] = None
    second = RS.start_run({"version": "0.0.2"}, version="0.0.2")

    runs = RS.list_runs()
    assert {r["run_id"] for r in runs} == {first.name, second.name}
    assert RS.latest_run()["report"].endswith("index.html")


def test_disabled_writes_nothing(env, monkeypatch):
    monkeypatch.setattr(RS, "REPORT_ENABLED", False)
    assert RS.start_run({"version": "0.0.1"}) is None
    assert not env.exists() or list(env.iterdir()) == []   # 关闭时连目录都不建
