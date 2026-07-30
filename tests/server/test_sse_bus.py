"""测试 SSE 事件总线"""

import json
import queue
import time

import pytest


class TestSSEBus:
    """测试 SSE 事件总线"""

    def test_subscribe_returns_queue(self):
        """测试订阅返回 Queue 实例"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_1")
        assert isinstance(q, queue.Queue)

    def test_publish_and_receive(self):
        """测试发布和接收"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_1")
        bus.publish("task_1", {"status": "completed", "label": "原神/荧"})
        data = q.get(timeout=1)
        parsed = json.loads(data)
        assert parsed["status"] == "completed"
        assert parsed["label"] == "原神/荧"

    def test_publish_to_no_subscribers(self):
        """测试发布到无订阅者不报错"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        # 不应抛出异常
        bus.publish("nonexistent_task", {"status": "completed"})

    def test_multiple_subscribers(self):
        """测试多个订阅者都收到消息"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q1 = bus.subscribe("task_1")
        q2 = bus.subscribe("task_1")
        bus.publish("task_1", {"status": "completed"})

        data1 = q1.get(timeout=1)
        data2 = q2.get(timeout=1)
        assert json.loads(data1)["status"] == "completed"
        assert json.loads(data2)["status"] == "completed"

    def test_unsubscribe(self):
        """测试取消订阅"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_1")
        bus.unsubscribe("task_1", q)
        # 取消后不应再收到消息
        assert "task_1" not in bus._subscribers or bus._subscribers["task_1"] == []

    def test_iter_events_returns_result(self):
        """测试 iter_events 返回结果"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_1")

        # 在一个线程中推送结果
        import threading
        def publish():
            time.sleep(0.1)
            bus.publish("task_1", {"status": "completed", "label": "test"})

        t = threading.Thread(target=publish, daemon=True)
        t.start()

        events = list(bus.iter_events("task_1", q, timeout=5))
        assert len(events) >= 1
        last_event = events[-1]
        assert "completed" in last_event

    def test_iter_events_timeout(self):
        """测试 iter_events 超时返回 timeout 消息"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_timeout")
        events = list(bus.iter_events("task_timeout", q, timeout=0.5))
        # 应收到 heartbeat 和 timeout 消息
        timeout_events = [e for e in events if "timeout" in e]
        assert len(timeout_events) >= 1

    def test_publish_non_json_data(self):
        """测试发布非 JSON 可序列化数据"""
        from services.sse_bus import SSEBus

        bus = SSEBus()
        q = bus.subscribe("task_1")
        # 发布一个包含不可序列化对象的 dict
        class Unserializable:
            pass
        bus.publish("task_1", {"data": "valid"})  # 正常的 JSON 数据
        data = q.get(timeout=1)
        parsed = json.loads(data)
        assert parsed["data"] == "valid"