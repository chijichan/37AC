"""通道级失败标记（services/task_manager.py::_mark_task_failed）回归测试。

背景：多通道时重试用的 task_id 是 "<父id>:<通道>"。失败时必须写进父任务那一行对应的
通道 section，而不是新建一行；否则父任务永远 pending，还多出一条幽灵记录。
"""

import importlib
import json
import sys

import pytest

# services/__init__.py 把 task_manager 这个属性重绑成了实例，这里要的是模块本身
tm_mod = sys.modules.get("services.task_manager") or importlib.import_module("services.task_manager")
from services import channel_service as cs


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split())
        self.db.executed.append((normalized, params))
        upper = normalized.upper()
        if upper.startswith("SELECT RESULT"):
            row = self.db.rows.get(params[0])
            self._row = (row,) if row is not None else None
        elif upper.startswith("INSERT INTO TASK_RESULTS"):
            # 多通道： (task_id, result, status)；单通道：(task_id, result) + status 字面量
            if len(params) == 2:
                task_id, payload, status = params[0], params[1], "failed"
            else:
                task_id, payload, status = params[0], params[1], params[2]
            self.db.rows[task_id] = payload
            self.db.status[task_id] = status
            self._row = None

    def fetchone(self):
        return self._row


class FakeDB:
    def __init__(self, rows=None):
        self.rows = dict(rows or {})
        self.status = {}
        self.executed = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        return None

    def close(self):
        return None


@pytest.fixture
def sse_events(monkeypatch):
    events = []

    class FakeBus:
        @staticmethod
        def publish(task_id, payload):
            events.append((task_id, payload))

    monkeypatch.setattr(tm_mod, "sse_bus", FakeBus)
    return events


def _manager_with_db(monkeypatch, db):
    monkeypatch.setattr(tm_mod, "get_db_connection", lambda: db)
    manager = tm_mod.TaskManager.__new__(tm_mod.TaskManager)   # 不启动监控线程
    manager._logger = tm_mod.logger
    return manager


def test_subtask_failure_marks_parent_channel(monkeypatch, sse_events):
    payload = cs.initial_result("p1", ["37ac", "llm"])
    cs.merge_channel_result(payload, "37ac", {"recognition_type": "local", "class_probs": [], "characters": []})
    db = FakeDB({"p1": json.dumps(payload)})

    manager = _manager_with_db(monkeypatch, db)
    manager._mark_task_failed("p1:llm", "没有支持 llm 的节点")

    # 没有新建 "<父id>:<通道>" 的幽灵行
    assert "p1:llm" not in db.rows
    merged = json.loads(db.rows["p1"])
    assert merged["llm"]["status"] == "failed"
    assert merged["llm"]["success"] is False
    assert "没有支持 llm 的节点" in merged["llm"]["error"]
    # 37ac 的结果必须原样保留，整体状态是"部分完成"
    assert merged["37ac"]["status"] == "completed"
    assert db.status["p1"] == "partial"
    # SSE 用父任务 id 推，前端才收得到
    assert sse_events and sse_events[-1][0] == "p1"


def test_subtask_failure_does_not_overwrite_completed_channel(monkeypatch, sse_events):
    payload = cs.initial_result("p2", ["37ac", "llm"])
    cs.merge_channel_result(payload, "llm", {"recognition_type": "llm", "class_probs": [{"name": "A", "prob": 1}], "characters": []})
    db = FakeDB({"p2": json.dumps(payload)})

    manager = _manager_with_db(monkeypatch, db)
    manager._mark_task_failed("p2:llm", "重试次数用尽")

    merged = json.loads(db.rows["p2"])
    assert merged["llm"]["status"] == "completed"            # 已有结果不被失败覆盖
    assert "重试次数用尽" not in json.dumps(merged, ensure_ascii=False)
    assert sse_events == []                                  # 也不推假失败


def test_plain_task_failure_keeps_single_row_behaviour(monkeypatch, sse_events):
    db = FakeDB()
    manager = _manager_with_db(monkeypatch, db)
    manager._mark_task_failed("t-single", "分发失败")

    assert json.loads(db.rows["t-single"]) == {"error": "分发失败"}
    assert db.status["t-single"] == "failed"
    assert sse_events[-1][0] == "t-single"
