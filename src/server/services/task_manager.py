"""任务管理器 - 管理待处理任务的注册、监控、重试和完成"""

import time
import threading
from config.log_config import get_logger
from config.base import TASK_RETRY_INTERVAL_LOCAL, TASK_RETRY_INTERVAL_LLM, TASK_MAX_RETRIES
from services.node_manager import get_db_connection, node_manager

logger = get_logger("TaskManager")


class TaskManager:
    """任务管理器，负责注册、监控和重试待处理任务"""

    def __init__(self):
        self.pending_tasks = {}
        self.lock = threading.Lock()
        self.check_interval = 2
        self.max_retries = TASK_MAX_RETRIES
        self._logger = get_logger("TaskManager")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _get_retry_interval(self, recognition_type):
        """根据识别类型返回重试间隔（秒）。

        - "local" → 本地推理较快，使用短间隔
        - "llm" / "auto" → 节点可能走大模型推理（思考+生成耗时数秒~数十秒），
          重试间隔必须 >= 节点上报的 LLM_TIMEOUT_SEC + 缓冲，
          否则会在节点推理完成前重复分发同一任务。
        """
        if recognition_type in ("llm", "auto"):
            node_timeout = node_manager.get_llm_timeout_sec()
            if node_timeout > 0:
                return max(TASK_RETRY_INTERVAL_LLM, node_timeout + 15)
            return TASK_RETRY_INTERVAL_LLM
        return TASK_RETRY_INTERVAL_LOCAL

    def register_task(self, task_id, image_path=None, image_data=None, max_retries=None, recognition_type="local"):
        """注册一个待处理任务"""
        if max_retries is None:
            max_retries = self.max_retries

        retry_interval = self._get_retry_interval(recognition_type)
        now = time.time()
        with self.lock:
            entry = self.pending_tasks.get(task_id)
            if entry is None:
                self.pending_tasks[task_id] = {
                    "image_path": image_path,
                    "image_data": image_data,
                    "attempts": 1,
                    "max_retries": max_retries,
                    "last_dispatch": now,
                    "next_retry": now + retry_interval,
                    "recognition_type": recognition_type,
                }
            else:
                entry["image_path"] = image_path
                entry["image_data"] = image_data
                entry["attempts"] = 1
                entry["max_retries"] = max_retries
                entry["last_dispatch"] = now
                entry["next_retry"] = now + retry_interval
                entry["recognition_type"] = recognition_type

    def mark_task_completed(self, task_id):
        """标记任务为已完成"""
        with self.lock:
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]

    def _monitor_loop(self):
        """后台监控循环，检查待处理任务状态并重试"""
        while True:
            time.sleep(self.check_interval)
            now = time.time()
            to_retry = []

            with self.lock:
                for task_id, entry in list(self.pending_tasks.items()):
                    if now >= entry["next_retry"]:
                        to_retry.append((task_id, entry.copy()))

            for task_id, entry in to_retry:
                if self._is_task_completed(task_id):
                    self.mark_task_completed(task_id)
                    continue

                if entry["attempts"] >= entry["max_retries"]:
                    self._logger.warning(
                        "任务 %s 达到最大重试次数 (%s)，停止重试",
                        task_id, entry["max_retries"]
                    )
                    self.mark_task_completed(task_id)
                    continue

                self._retry_task(task_id, entry)

    def _is_task_completed(self, task_id):
        """检查任务是否已完成"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM task_results WHERE task_id = %s",
                    (task_id,),
                )
                row = cursor.fetchone()
            if row and row[0] and row[0] != "pending":
                return True
        except Exception:
            pass
        finally:
            if "conn" in locals() and conn:
                conn.close()
        return False

    def _retry_task(self, task_id, entry):
        """重试一个任务"""
        # 延迟导入避免循环依赖
        from services.task_dispatcher import dispatch_task

        image_path = entry["image_path"]
        image_data = entry.get("image_data")
        if image_data is None and image_path:
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
            except Exception as e:
                self._logger.error("读取重试图片失败: %s", e)
                self.mark_task_completed(task_id)
                return

        if image_data is None:
            self._logger.error("无法重试任务 %s：缺少图片数据", task_id)
            self.mark_task_completed(task_id)
            return

        response = dispatch_task(
            image_path,
            image_data,
            task_id,
            register_pending=False,
            recognition_type=entry.get("recognition_type", "local"),
        )

        now = time.time()
        with self.lock:
            current = self.pending_tasks.get(task_id)
            if not current:
                return
            current["attempts"] = current.get("attempts", 0) + 1
            current["last_dispatch"] = now
            retry_interval = self._get_retry_interval(entry.get("recognition_type", "local"))
            current["next_retry"] = now + retry_interval

        self._logger.info(
            "任务 %s 第 %s 次重试，结果: %s",
            task_id, entry["attempts"] + 1, response.get("status")
        )


# 模块级全局实例
task_manager = TaskManager()
