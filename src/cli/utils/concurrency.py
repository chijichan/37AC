# -*- coding: utf-8 -*-
"""可中断的并发执行：Ctrl+C 后不再开始新任务，并尽快返回（不等所有任务跑完）。

背景：with ThreadPoolExecutor(...) 退出时会 shutdown(wait=True)，
Ctrl+C 只是打断主线程，之后仍要**等所有任务跑完**才返回——
几千张图的数据集裁剪因此"停不下来"，只能强杀进程。
这里改成：协作式取消标志 + shutdown(wait=False, cancel_futures=True)。
"""

import threading

from config.log_config import get_logger

logger = get_logger("concurrency")


class CancelToken:
    """协作式取消标志：worker 在处理每个单位（每张图/每个角色）前检查一次。"""

    def __init__(self, cancelled: bool = False):
        self._event = threading.Event()
        if cancelled:
            self._event.set()

    def cancel(self):
        self._event.set()

    def cancelled(self) -> bool:
        return self._event.is_set()


def interruptible_map(func, items, max_workers=1, cancel_token=None,
                      desc=None, unit="项", on_done=None):
    """并发执行 func(item, token)；Ctrl+C 时立刻停止（不再开始新任务）。

    Args:
        func: (item, token) -> result；**请在内部循环里检查 token.cancelled()**，
              这样在跑的线程也能在下一个检查点退出，而不是跑完整个角色/目录
        items: 待处理项
        max_workers: 并发线程数
        cancel_token: 外部取消标志（已置位则一项都不跑）
        desc / unit: tqdm 描述与单位
        on_done: 每个任务完成时在主线程回调 on_done(item, result)

    Returns:
        (interrupted, results)：interrupted=True 表示被 Ctrl+C 中断（results 为部分结果）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    token = cancel_token or CancelToken()
    items = list(items or [])
    results = []
    if not items or token.cancelled():
        return False, results

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    executor = ThreadPoolExecutor(max_workers=max(1, int(max_workers or 1)))
    futures = {}
    interrupted = False
    try:
        for item in items:
            if token.cancelled():
                break
            futures[executor.submit(func, item, token)] = item

        progress = as_completed(futures)
        if tqdm is not None and desc:
            progress = tqdm(progress, total=len(futures), desc=desc, unit=unit, ncols=100)

        for future in progress:
            item = futures[future]
            try:
                result = future.result()
            except Exception as e:              # 单个任务失败不影响其它任务
                logger.error("任务异常（%s）: %s", item, e)
                result = e
            results.append(result)
            if on_done is not None:
                try:
                    on_done(item, result)
                except Exception as e:
                    logger.debug("on_done 回调失败: %s", e)
    except KeyboardInterrupt:
        interrupted = True
        token.cancel()
        logger.warning(
            "收到 Ctrl+C：不再开始新任务，正在处理的那一张完成后即停止（已处理的图片会保留）"
        )
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        return interrupted, results
    finally:
        if not interrupted:
            executor.shutdown(wait=True)

    return interrupted, results
