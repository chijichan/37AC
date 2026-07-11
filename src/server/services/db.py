"""数据库连接工具模块 - 提供统一的数据库连接管理和查询辅助"""

from contextlib import contextmanager
from typing import Optional

import pymysql
from config.base import DB_CONFIG
from config.log_config import get_logger

logger = get_logger("db")


def get_connection():
    """获取数据库连接"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        return None


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
