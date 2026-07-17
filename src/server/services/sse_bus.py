"""SSE 事件总线 - 支持任务结果的实时推送（Server-Sent Events）

用法：
    from services.sse_bus import sse_bus

    # 订阅某个 task_id 的事件流
    queue = sse_bus.subscribe(task_id)

    # 生产者（如 message_handlers）推送结果
    sse_bus.publish(task_id, {"status": "completed", "result": [...]})

    # 消费者端拿到 queue 后在 Flask 中生成 SSE 流：
    for event in sse_bus.iter_events(task_id, queue, timeout=60):
        yield event
"""

import queue
import threading
import time
import json
import logging

logger = logging.getLogger("SSEBus")


class SSEBus:
    """基于 queue.Queue 的轻量级 SSE 事件总线。
    每个 task_id 可对应多个订阅者，通过广播实现一对多推送。
    """

    def __init__(self):
        # task_id → list of queue.Queue
        self._subscribers: dict[str, list[queue.Queue]] = {}
        self._lock = threading.Lock()

    def subscribe(self, task_id: str) -> queue.Queue:
        """订阅某个 task 的事件，返回一个 Queue 实例供消费者迭代。"""
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.setdefault(task_id, []).append(q)
        logger.debug("[SSE] 订阅: task_id=%s, 当前订阅数=%d", task_id,
                     len(self._subscribers.get(task_id, [])))
        return q

    def unsubscribe(self, task_id: str, q: queue.Queue):
        """取消订阅（消费者断开时调用）。"""
        with self._lock:
            subs = self._subscribers.get(task_id)
            if subs and q in subs:
                subs.remove(q)
                logger.debug("[SSE] 取消订阅: task_id=%s", task_id)
            if subs is not None and len(subs) == 0:
                del self._subscribers[task_id]

    def publish(self, task_id: str, data: dict):
        """向所有订阅了 task_id 的消费者推送 JSON 数据。"""
        payload = json.dumps(data, ensure_ascii=False)
        with self._lock:
            subs = list(self._subscribers.get(task_id, []))
        for q in subs:
            try:
                q.put_nowait(payload)
            except queue.Full:
                logger.warning("[SSE] 队列已满，丢弃事件: task_id=%s", task_id)
            except Exception:
                logger.warning("[SSE] 推送异常: task_id=%s", task_id, exc_info=True)
        logger.info("[SSE] 推送: task_id=%s, 订阅数=%d", task_id, len(subs))

    def iter_events(self, task_id: str, q: queue.Queue, timeout: float = 60.0):
        """生成器：阻塞等待事件，超时则发送 heartbeat 并继续。

        用于 Flask SSE 路由中的 Response 生成器。
        对 waiting 状态不结束流，继续等待最终结果。
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data = q.get(timeout=5.0)  # 每 5 秒检查一次超时
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("[SSE] 收到非 JSON 数据: task_id=%s", task_id)
                    continue
                # waiting 状态不结束流，继续等待最终结果
                if parsed.get("status") == "waiting":
                    yield f"data: {data}\n\n"
                    continue
                yield f"data: {data}\n\n"
                return  # 拿到最终结果后结束流
            except queue.Empty:
                # 发送 SSE heartbeat 注释，保持连接活跃
                yield ": heartbeat\n\n"
        # 超时：自动取消订阅防止死订阅泄漏
        self.unsubscribe(task_id, q)
        yield f"data: {json.dumps({'status': 'timeout', 'message': '等待超时', 'task_id': task_id}, ensure_ascii=False)}\n\n"


# 全局单例
sse_bus = SSEBus()
