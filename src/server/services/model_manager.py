# services/model_manager.py
"""识别模型管理器 - 泛化的模型管理（models 表）

每个模型一条记录（同一种模型可有多个版本，以 model_id+version 唯一）：
  - model_id      模型标识，如 37ac / deepseek-v4.1
  - display_name  展示名称
  - type          local / llm
  - version       版本号
  - config_url    配置文件(config.json)下载地址（内含权重/类别 URL）
  - config_hash   配置文件 SHA-256（可选）
  - notes         说明
  - status        active / inactive（同一 model_id 下最多一个 active）
"""

from datetime import datetime

from utils.db_utils import get_connection
from config.log_config import get_logger

logger = get_logger("model_manager")

# 与 SELECT 语句的列顺序保持一致（游标未使用 DictCursor 时按此 zip 成字典）
_MODEL_COLUMNS = (
    "id", "model_id", "display_name", "type", "version",
    "config_url", "config_hash",
    "notes", "status", "created_at", "updated_at",
)


def _normalize(row):
    """把数据库行转成可 JSON 序列化的 dict。

    兼容 DictCursor（dict）和普通游标（tuple/list）。
    """
    if row is None:
        return None
    if isinstance(row, dict):
        item = dict(row)
    else:
        item = dict(zip(_MODEL_COLUMNS, row))
    for field in ("created_at", "updated_at"):
        value = item.get(field)
        if isinstance(value, datetime):
            item[field] = value.strftime("%Y-%m-%d %H:%M:%S")
    return item


def list_models(model_id=None):
    """返回模型列表；model_id 为空时返回全部，否则只返回该模型的所有版本。"""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            if model_id:
                cursor.execute(
                    "SELECT id, model_id, display_name, type, version, config_url, config_hash, "
                    "notes, status, created_at, updated_at "
                    "FROM models WHERE model_id = %s ORDER BY updated_at DESC, id DESC",
                    (model_id,),
                )
            else:
                cursor.execute(
                    "SELECT id, model_id, display_name, type, version, config_url, config_hash, "
                    "notes, status, created_at, updated_at "
                    "FROM models ORDER BY model_id, updated_at DESC, id DESC",
                )
            rows = cursor.fetchall()
        return [_normalize(r) for r in rows]
    except Exception as e:
        logger.error("查询模型列表失败: %s", e)
        return []
    finally:
        conn.close()


def get_active_models():
    """返回所有已激活的模型记录。"""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, model_id, display_name, type, version, config_url, config_hash, "
                "notes, status, created_at, updated_at "
                "FROM models WHERE status = 'active' ORDER BY id DESC",
            )
            rows = cursor.fetchall()
        return [_normalize(r) for r in rows]
    except Exception as e:
        logger.error("查询激活模型失败: %s", e)
        return []
    finally:
        conn.close()


def get_active_model(model_id):
    """返回指定模型标识的当前激活版本；没有则返回 None。"""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, model_id, display_name, type, version, config_url, config_hash, "
                "notes, status, created_at, updated_at "
                "FROM models WHERE model_id = %s AND status = 'active' ORDER BY id DESC LIMIT 1",
                (model_id,),
            )
            row = cursor.fetchone()
        return _normalize(row)
    except Exception as e:
        logger.error("查询激活模型失败: %s", e)
        return None
    finally:
        conn.close()


def create_model(model_id, version, config_url, display_name="", type="local",
                 config_hash=None, notes="", activate=False):
    """新增一个模型记录。activate=True 时立即激活（停用同名旧版本）。"""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO models (model_id, display_name, type, version, config_url, config_hash, "
                "notes, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (model_id, display_name or model_id, type or "local", version, config_url,
                 config_hash or None, notes or "", "active" if activate else "inactive"),
            )
            new_id = cursor.lastrowid
            if activate:
                _deactivate_same_model_id(cursor, model_id, new_id)
        conn.commit()
        logger.info("新增模型: model_id=%s version=%s activate=%s", model_id, version, activate)
        return {"success": True, "id": new_id}
    except Exception as e:
        conn.rollback()
        logger.error("新增模型失败: %s", e)
        return {"success": False, "message": f"新增失败: {e}"}
    finally:
        conn.close()


def update_model(model_id, model_id_new=None, display_name=None, type=None, version=None,
                 config_url=None, config_hash=None, notes=None):
    """更新模型记录（不包含激活/停用）。"""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    sets = []
    params = []
    if model_id_new is not None:
        sets.append("model_id = %s")
        params.append(model_id_new)
    if display_name is not None:
        sets.append("display_name = %s")
        params.append(display_name)
    if type is not None:
        sets.append("type = %s")
        params.append(type)
    if version is not None:
        sets.append("version = %s")
        params.append(version)
    if config_url is not None:
        sets.append("config_url = %s")
        params.append(config_url)
    if config_hash is not None:
        sets.append("config_hash = %s")
        params.append(config_hash)
    if notes is not None:
        sets.append("notes = %s")
        params.append(notes)
    if not sets:
        return {"success": False, "message": "没有要更新的字段"}
    params.append(model_id)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE models SET {', '.join(sets)} WHERE id = %s",
                tuple(params),
            )
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        logger.error("更新模型失败: %s", e)
        return {"success": False, "message": f"更新失败: {e}"}
    finally:
        conn.close()


def set_active(model_id):
    """激活指定模型记录，并停用同名模型的其他记录。"""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT model_id FROM models WHERE id = %s",
                (model_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "模型记录不存在"}
            same = row[0]
            _deactivate_same_model_id(cursor, same, model_id)
            cursor.execute(
                "UPDATE models SET status = 'active' WHERE id = %s",
                (model_id,),
            )
        conn.commit()
        logger.info("激活模型: id=%s model_id=%s", model_id, same)
        return {"success": True}
    except Exception as e:
        conn.rollback()
        logger.error("激活模型失败: %s", e)
        return {"success": False, "message": f"激活失败: {e}"}
    finally:
        conn.close()


def delete_model(model_id):
    """删除指定模型记录。"""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM models WHERE id = %s", (model_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        logger.error("删除模型失败: %s", e)
        return {"success": False, "message": f"删除失败: {e}"}
    finally:
        conn.close()


def _deactivate_same_model_id(cursor, model_id, keep_id):
    """停用同一 model_id 下除 keep_id 外的所有记录。"""
    cursor.execute(
        "UPDATE models SET status = 'inactive' WHERE model_id = %s AND id <> %s",
        (model_id, keep_id),
    )
