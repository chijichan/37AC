"""长任务期间的按键监听：ESC/Ctrl+Z → 停止返回上级；Ctrl+C → 结束程序。"""

import inspect
import sys
import time
import types

from utils import cli_input as CI
from training import trainer as T


def _watcher():
    w = CI.KeyWatcher(poll_interval=0.01)
    calls = {"back": 0, "exit": 0}
    w.on_back = lambda: calls.__setitem__("back", calls["back"] + 1)
    w.on_exit = lambda: calls.__setitem__("exit", calls["exit"] + 1)
    return w, calls


def test_esc_and_ctrl_z_request_back():
    for key in (CI.ESC, CI.CTRL_Z):
        watcher, calls = _watcher()
        assert watcher.handle_key(key) is True
        assert watcher.back_requested is True
        assert watcher.exit_requested is False
        assert calls["back"] == 1


def test_ctrl_c_requests_exit():
    watcher, calls = _watcher()
    assert watcher.handle_key(CI.CTRL_C) is True
    assert watcher.exit_requested is True
    assert watcher.back_requested is False
    assert calls["exit"] == 1


def test_normal_keys_ignored_and_back_only_once():
    watcher, calls = _watcher()
    assert watcher.handle_key("1") is False
    watcher.handle_key(CI.ESC)
    watcher.handle_key(CI.ESC)          # 连按不重复触发
    assert calls["back"] == 1
    assert watcher.back_requested and not watcher.exit_requested


def test_run_reads_keys_from_console(monkeypatch):
    """用假 msvcrt 喂按键：ESC 被识别为返回、Ctrl+C 被识别为退出。"""
    queue = ["a", CI.ESC, CI.CTRL_C]

    fake = types.SimpleNamespace(
        kbhit=lambda: bool(queue),
        getwch=lambda: queue.pop(0),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake)

    watcher, calls = _watcher()
    watcher.start()
    deadline = time.time() + 2.0
    while time.time() < deadline and not (watcher.back_requested and watcher.exit_requested):
        time.sleep(0.01)
    watcher.stop()

    assert watcher.back_requested and watcher.exit_requested
    assert calls["back"] == 1 and calls["exit"] == 1


def test_train_model_accepts_cancel_token():
    params = inspect.signature(T.train_model).parameters
    assert "cancel_token" in params
    assert issubclass(T.TrainingCancelled, Exception)
