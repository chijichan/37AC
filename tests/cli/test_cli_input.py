"""统一交互按键：ESC/Ctrl+Z 返回上级，Ctrl+C 结束程序。"""

import builtins

import pytest

from utils import cli_input as CI


def _feed(monkeypatch, *values):
    """依次返回给定的输入值；元素为异常类时抛出该异常。"""
    queue = list(values)

    def fake_input(prompt=""):
        item = queue.pop(0) if queue else ""
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item()
        return item

    monkeypatch.setattr(builtins, "input", fake_input)


def test_esc_means_back(monkeypatch):
    _feed(monkeypatch, "\x1b")
    with pytest.raises(CI.GoBack):
        CI.read_line("> ")


def test_ctrl_z_char_means_back(monkeypatch):
    _feed(monkeypatch, "\x1a")
    with pytest.raises(CI.GoBack):
        CI.read_line("> ")


def test_ctrl_z_eof_means_back(monkeypatch):
    _feed(monkeypatch, EOFError)
    with pytest.raises(CI.GoBack):
        CI.read_line("> ")


def test_empty_means_back(monkeypatch):
    _feed(monkeypatch, "   ")
    with pytest.raises(CI.GoBack):
        CI.read_line("> ")


def test_ctrl_c_means_exit(monkeypatch):
    _feed(monkeypatch, KeyboardInterrupt)
    with pytest.raises(CI.ExitProgram):
        CI.read_line("> ")


def test_normal_input_returned_and_controls_stripped(monkeypatch):
    _feed(monkeypatch, "  2  ")
    assert CI.read_line("> ") == "2"

    _feed(monkeypatch, "2\x1b")          # 值和 ESC 混在一起：仍取到有效值
    assert CI.read_line("> ") == "2"


def test_ask_retries_until_valid(monkeypatch, capsys):
    _feed(monkeypatch, "9", "x", "3")
    assert CI.ask("请选择: ", valid=("1", "2", "3")) == "3"
    printed = capsys.readouterr().out
    assert printed.count("无效选择") == 2
    assert "Ctrl+C" in printed            # 提示里带按键约定


def test_ask_accepts_any_non_empty_when_valid_none(monkeypatch):
    _feed(monkeypatch, "任意路径/图.png")
    assert CI.ask("路径: ") == "任意路径/图.png"


def test_ask_propagates_back_and_exit(monkeypatch):
    _feed(monkeypatch, "\x1b")
    with pytest.raises(CI.GoBack):
        CI.ask("请选择: ", valid=("1",))

    _feed(monkeypatch, KeyboardInterrupt)
    with pytest.raises(CI.ExitProgram):
        CI.ask("请选择: ", valid=("1",))


def test_wait_enter_swallows_back(monkeypatch):
    _feed(monkeypatch, "")
    CI.wait_enter()                       # 不抛异常

    _feed(monkeypatch, KeyboardInterrupt)
    with pytest.raises(CI.ExitProgram):   # Ctrl+C 仍然结束程序
        CI.wait_enter()
