"""共享数据库工具 - 通用 SQL 构建，避免各服务重复拼接 UPDATE 语句"""

from typing import Any


def build_update_sql(
    table: str,
    updates: dict[str, Any],
    where_clause: str,
    where_params: tuple | list = (),
    raw_assignments: list[str] | None = None,
) -> tuple[str, tuple] | tuple[None, None]:
    """构建 UPDATE 语句，仅包含值为非 None 的字段。

    Args:
        table: 表名
        updates: {列名: 值}，值为 None 的列会被跳过
        where_clause: WHERE 子句（不含 WHERE 关键字，如 "id = %s"）
        where_params: WHERE 子句参数（追加在 SET 参数之后）
        raw_assignments: 额外追加的 SET 子句（非参数化，如 ["updated_at = NOW()"]）

    Returns:
        (sql, params) 或 (None, None)（无字段可更新时）

    Example:
        sql, params = build_update_sql(
            "users", {"email": "a@b.com", "avatar": None},
            "id = %s", (1,),
        )
        # sql: "UPDATE users SET email = %s WHERE id = %s"
        # params: ("a@b.com", 1)
    """
    assignments = []
    params: list[Any] = []

    if not where_clause:
        raise ValueError("build_update_sql: where_clause 不能为空（禁止全表更新）")

    for column, value in updates.items():
        if value is not None:
            assignments.append(f"{column} = %s")
            params.append(value)

    if raw_assignments:
        assignments.extend(raw_assignments)

    if not assignments:
        return None, None

    sql = f"UPDATE {table} SET {', '.join(assignments)} WHERE {where_clause}"
    params.extend(where_params)
    return sql, tuple(params)
