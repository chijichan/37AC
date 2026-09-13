"""连接池（utils/db_utils.py）行为测试

重点回归：池化连接必须使用 READ COMMITTED。
默认 REPEATABLE READ + 长期不提交的连接，会让第一个 SELECT 的快照一直沿用，
后台改了设置/数据后同一线程仍读到旧值（已在运行时实测复现）。
"""

import pytest

import utils.db_utils as db_utils


class _FakeConn:
    def __init__(self):
        self.pinged = 0
        self.closed = False

    def ping(self, reconnect=False):
        self.pinged += 1
        return True

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _reset_thread_local():
    """避免线程本地连接在用例之间串味。"""
    db_utils._tls.conn = None
    yield
    db_utils._tls.conn = None


def test_new_connection_uses_read_committed(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return _FakeConn()

    monkeypatch.setattr(db_utils.pymysql, "connect", fake_connect)
    conn = db_utils._new_connection()

    assert conn is not None
    assert "READ COMMITTED" in captured.get("init_command", "").upper()
    # 其余连接参数仍来自 DB_CONFIG
    assert captured.get("host") == db_utils.DB_CONFIG["host"]
    assert captured.get("database") == db_utils.DB_CONFIG["database"]


def test_get_connection_reuses_thread_local_connection(monkeypatch):
    calls = []

    def fake_connect(**kwargs):
        calls.append(kwargs)
        return _FakeConn()

    monkeypatch.setattr(db_utils.pymysql, "connect", fake_connect)

    first = db_utils.get_connection()
    second = db_utils.get_connection()

    assert first is second
    assert len(calls) == 1
    assert first.pinged >= 1


def test_get_connection_rebuilds_when_ping_fails(monkeypatch):
    calls = []

    def fake_connect(**kwargs):
        calls.append(kwargs)
        return _FakeConn()

    monkeypatch.setattr(db_utils.pymysql, "connect", fake_connect)

    def _boom(reconnect=False):
        raise RuntimeError("connection lost")

    first = db_utils.get_connection()
    first._conn.ping = _boom  # 模拟底层连接失效（PyMySQL ping 失败会抛异常）

    second = db_utils.get_connection()

    assert second is not first
    assert len(calls) == 2


def test_pooled_connection_close_only_returns_to_pool(monkeypatch):
    """close() 只归还连接，不真正断开（连接池语义）。"""
    raw = _FakeConn()
    conn = db_utils._PooledConnection(raw)

    conn.close()

    assert raw.closed is False
