"""异步处理器 - 提供通用异步任务处理和按消息类型分类的异步处理器"""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading
from config.log_config import get_logger

logger = get_logger("async_processor")


class AsyncTaskProcessor:
    """通用异步任务处理器"""

    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.start_background_processor()

    def start_background_processor(self):
        """启动后台任务处理器"""
        def process_tasks():
            while True:
                try:
                    task_func, args, kwargs = self.task_queue.get(timeout=1)
                    future = self.executor.submit(task_func, *args, **kwargs)
                    self.result_queue.put(future)
                except Exception:
                    continue

        processor_thread = threading.Thread(target=process_tasks, daemon=True)
        processor_thread.start()

    def submit_task(self, func, *args, **kwargs):
        """提交任务到异步处理器"""
        self.task_queue.put((func, args, kwargs))
        return True


class MessageTypeProcessor:
    """按消息类型分类的异步处理器"""

    def __init__(self):
        self.processors = {
            "register": ThreadPoolExecutor(max_workers=3),
            "heartbeat": ThreadPoolExecutor(max_workers=15),
            "task_result": ThreadPoolExecutor(max_workers=5),
            "default": ThreadPoolExecutor(max_workers=3),
        }

        self.message_queues = {
            "register": Queue(),
            "heartbeat": Queue(),
            "task_result": Queue(),
            "default": Queue(),
        }

        self._start_message_processors()

    def _start_message_processors(self):
        """启动各消息类型的后台处理循环"""
        for msg_type in self.message_queues.keys():
            self._start_single_message_processor(msg_type)

    def _start_single_message_processor(self, msg_type):
        """启动单个消息类型的处理循环"""
        def message_processor():
            queue = self.message_queues[msg_type]
            processor = self.processors[msg_type]

            while True:
                try:
                    task_func, args, kwargs = queue.get(timeout=1)
                    processor.submit(task_func, *args, **kwargs)
                except Exception:
                    continue

        thread = threading.Thread(target=message_processor, daemon=True)
        thread.start()

    def submit_message_task(self, msg_type, func, *args, **kwargs):
        """提交消息处理任务"""
        if msg_type in self.message_queues:
            self.message_queues[msg_type].put((func, args, kwargs))
        else:
            self.message_queues["default"].put((func, args, kwargs))


# 模块级全局实例
async_processor = AsyncTaskProcessor(max_workers=10)
message_type_processor = MessageTypeProcessor()
