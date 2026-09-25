"""图片补拉（需求3 后半）：services/image_refetch.py 回归测试（不需要数据库/真实节点）。"""

import base64

import pytest

from services import image_refetch

NODE_ID = 7
TASK_ID = "task-refetch-1"


@pytest.fixture
def wire(monkeypatch):
    """打桩 node_manager.nodes 与 json_protocol.send_json，返回可注入发送逻辑的容器。"""
    holder = {"send": None, "message": None}

    monkeypatch.setattr(image_refetch.node_manager, "nodes", {NODE_ID: {"socket": object()}})

    def fake_send(sock, message):
        holder["message"] = message
        if holder["send"]:
            return holder["send"](message)
        return True

    monkeypatch.setattr(image_refetch.json_protocol, "send_json", fake_send)
    monkeypatch.setattr(image_refetch, "IMAGE_NODE_REFETCH", True)
    return holder


def test_success_roundtrip_returns_bytes(wire):
    raw = b"\x89PNG\r\n\x1a\n" + b"payload"

    def send(message):
        request_id = message["data"]["request_id"]
        assert message["type"] == "image_request"
        assert message["data"]["task_id"] == TASK_ID
        image_refetch.resolve(request_id, {
            "image_data": base64.b64encode(raw).decode(),
            "image_size": len(raw),
            "image_filename": "probe.png",
        })
        return True

    wire["send"] = send
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)

    assert result["success"] is True
    assert result["data"]["bytes"] == raw
    assert result["data"]["filename"] == "probe.png"
    assert wire["message"]["data"]["request_id"]


def test_node_offline(monkeypatch, wire):
    monkeypatch.setattr(image_refetch.node_manager, "nodes", {})
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)

    assert result["success"] is False
    assert "不在线" in result["message"]


def test_without_node_id(wire):
    result = image_refetch.request_from_node(None, TASK_ID)

    assert result["success"] is False
    assert "不知道" in result["message"]


def test_timeout_when_node_silent(wire):
    result = image_refetch.request_from_node(NODE_ID, TASK_ID, timeout=0.1)

    assert result["success"] is False
    assert "超时" in result["message"]


def test_send_failure(wire):
    wire["send"] = lambda message: False
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)

    assert result["success"] is False
    assert "发送失败" in result["message"]


def test_node_reports_error(wire):
    def send(message):
        image_refetch.resolve(message["data"]["request_id"], {"error": "节点已清理该图片"})
        return True

    wire["send"] = send
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)

    assert result["success"] is False
    assert "已清理" in result["message"]


def test_bad_base64_payload(wire):
    def send(message):
        image_refetch.resolve(message["data"]["request_id"], {"image_data": "!!!not-base64!!!"})
        return True

    wire["send"] = send
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)

    assert result["success"] is False
    assert "解码失败" in result["message"]


def test_resolve_unknown_request_id():
    assert image_refetch.resolve("no-such-request", {}) is False


def test_disabled_switch(monkeypatch, wire):
    monkeypatch.setattr(image_refetch, "IMAGE_NODE_REFETCH", False)

    assert image_refetch.enabled() is False
    result = image_refetch.request_from_node(NODE_ID, TASK_ID)
    assert result["success"] is False
    assert "未启用" in result["message"]


def test_pending_cleared_after_request(wire):
    wire["send"] = lambda message: True
    image_refetch.request_from_node(NODE_ID, TASK_ID, timeout=0.1)

    assert image_refetch.pending_count() == 0
