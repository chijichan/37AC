"""背压（连接数 / 队列）与 CORS 默认收紧的回归防护。

注意：services 包会把 async_processor 的单例导出为同名属性，
因此这里必须用 importlib 拿**模块**，不能 from services import async_processor（那是实例）。
"""

import importlib
import inspect
from pathlib import Path

from services import listen_service as LS

AP = importlib.import_module("services.async_processor")
CLS = AP.AsyncTaskProcessor


def test_task_queue_has_bounded_size_and_rejects_when_full(monkeypatch):
    """队列有界：满时立即拒绝，而不是排队等待。"""
    monkeypatch.setattr(CLS, "start_background_processor", lambda self: None)
    proc = CLS(max_workers=1, max_queue=1)

    assert proc.task_queue.maxsize == 1
    assert proc.submit_task(lambda: None) is True
    assert proc.submit_task(lambda: None) is False          # 第二次被明确拒绝


def test_queue_size_comes_from_config(monkeypatch):
    import config.base as cfg

    monkeypatch.setattr(CLS, "start_background_processor", lambda self: None)
    monkeypatch.setattr(cfg, "MAX_TASK_QUEUE", 7)
    proc = CLS(max_workers=1)
    assert proc.task_queue.maxsize == 7


def test_connection_limit_exists_and_rejects():
    assert LS._CONN_STATE["limit"] >= 1
    src = inspect.getsource(LS)
    assert "MAX_NODE_CONNECTIONS" in src
    assert '"busy"' in src, "超过连接上限时应回 busy 再关闭"


def test_server_config_exposes_backpressure_keys():
    import config.base as cfg

    assert cfg.MAX_NODE_CONNECTIONS >= 1
    assert cfg.MAX_TASK_QUEUE >= 1
    assert cfg.CORS_ALLOW_ALL in (True, False)


def test_cors_is_deny_by_default():
    src = Path(AP.__file__).resolve().parents[1].joinpath("AC_web", "__init__.py").read_text(encoding="utf-8")
    assert "CORS_ALLOW_ALL" in src
    assert "CORS(app)  # 开发/默认环境回退" not in src, "不应再有无条件放行所有来源的兜底"
    assert "仅同源可用" in src
