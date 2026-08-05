"""数据库连接工具模块 - 提供统一的数据库连接管理和查询辅助"""

import threading
from contextlib import contextmanager
from typing import Optional

import pymysql
from config.base import DB_CONFIG
from config.log_config import get_logger

logger = get_logger("db")


class _PooledConnection:
    """连接池包装：拦截 close()，将连接归还到线程本地复用。

    数据库在远程服务器（实测单次握手约 1s），反复新建连接是识别链路的主要瓶颈。
    通过 线程本地 + ping 健康检查 复用连接，将每次 DB 访问降到 RTT 量级（约 0.15s）。
    """

    __slots__ = ("_conn", "_closed")

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_closed", False)

    def close(self):
        """归还连接到线程本地池（不真正断开 TCP，供复用）。"""
        object.__setattr__(self, "_closed", True)

    def _discard(self):
        """销毁底层连接（连接已失效时由连接池调用）。"""
        try:
            self._conn.close()
        except Exception:
            pass
        object.__setattr__(self, "_conn", None)

    def ping(self) -> bool:
        """轻量健康检查；失败返回 False，由连接池决定是否重建。"""
        try:
            self._conn.ping(reconnect=False)
            return True
        except Exception:
            return False

    def __getattr__(self, name):
        # 转发所有其他属性/方法到真实连接（cursor / commit / rollback / open 等）
        return getattr(self._conn, name)


# 线程本地连接存储：每个线程持有一个复用的池化连接
_tls = threading.local()


def _new_connection():
    """新建一个底层 PyMySQL 连接。"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        return None


def get_connection():
    """获取数据库连接（线程本地连接池，复用连接避免对远程 MySQL 反复握手）。

    返回的 _PooledConnection 包装对象：close() 仅归还（不断开），
    池会在下次获取时用 ping 校验连接健康度，失效则自动重建。
    """
    conn = getattr(_tls, "conn", None)
    if conn is not None:
        if conn.ping():
            return conn
        # 连接已失效：销毁后重建
        logger.debug("数据库连接已失效，重建中")
        conn._discard()

    raw = _new_connection()
    if raw is None:
        _tls.conn = None
        return None
    conn = _PooledConnection(raw)
    _tls.conn = conn
    return conn


@contextmanager
def db_cursor(cursor_class=None):
    """数据库游标上下文管理器

    用法:
        with db_cursor() as cursor:
            cursor.execute("SELECT ...")
            # 自动 commit
    """
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            yield None, None
            return
        with conn.cursor(cursor_class) as cursor:
            yield cursor, conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


@contextmanager
def db_connection():
    """数据库连接上下文管理器

    用法:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ...")
            conn.commit()
    """
    conn = None
    try:
        conn = get_connection()
        if conn is None:
            yield None
            return
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def format_datetime_fields(obj: dict, fields: list) -> dict:
    """将字典中的 datetime 字段格式化为字符串"""
    for field in fields:
        value = obj.get(field)
        if value and hasattr(value, "strftime"):
            obj[field] = value.strftime("%Y-%m-%d %H:%M:%S")
    return obj


def safe_execute(sql: str, params: tuple = None, fetchone: bool = False, fetchall: bool = False):
    """安全执行 SQL 并返回结果（简单场景使用）"""
    with db_cursor(pymysql.cursors.DictCursor if fetchone or fetchall else None) as (cursor, conn):
        if cursor is None:
            return None
        cursor.execute(sql, params or ())
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return cursor.lastrowid
