"""任务管理器 - 管理待处理任务的注册、监控、重试和完成"""

import time
import threading
from config.log_config import get_logger
from config.base import TASK_RETRY_INTERVAL_LOCAL, TASK_RETRY_INTERVAL_LLM, TASK_MAX_RETRIES

logger = get_logger("TaskManager")


def get_db_connection():
    """获取数据库连接（由外部配置）"""
    # 延迟导入避免循环依赖
    import pymysql
    from config.base import DB_CONFIG
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        return None


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
        """根据识别类型返回重试间隔（秒）"""
        return TASK_RETRY_INTERVAL_LLM if recognition_type == "llm" else TASK_RETRY_INTERVAL_LOCAL

    def register_task(self, task_id, image_path, max_retries=None, recognition_type="local"):
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
                    "attempts": 1,
                    "max_retries": max_retries,
                    "last_dispatch": now,
                    "next_retry": now + retry_interval,
                    "recognition_type": recognition_type,
                }
            else:
                entry["image_path"] = image_path
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
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
        except Exception as e:
            self._logger.error("读取重试图片失败: %s", e)
            self.mark_task_completed(task_id)
            return

        from services.node_manager import get_db_connection as _unused
        _unused  # 确保导入可用

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
