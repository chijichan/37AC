#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
37AC 数据库安装脚本（交互式管理员配置）
========================================

功能：
  1. 从 src/server/.env 读取数据库连接信息；
  2. 执行 scripts/install.sql 完成「建库 + 建表 + 索引」（跳过其中默认 admin 的 INSERT）；
  3. 交互式输入管理员用户名 / 密码 / 邮箱，生成 bcrypt 哈希写入 users 表。

用法：
  python scripts/install_db.py

说明：
  - 校验规则与系统注册接口保持一致（用户名 3-50 位、密码 6-128 位、邮箱标准格式）。
  - 密码以 getpass 输入（不回显），并以 bcrypt 哈希入库，绝不保存明文。
"""

import getpass
import os
import re
import sys
from pathlib import Path

import bcrypt
import pymysql
from dotenv import load_dotenv

# ---- 路径定位 ----
ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / "src" / "server" / ".env"
INSTALL_SQL = Path(__file__).resolve().parent / "install.sql"

# ---- 加载 .env ----
load_dotenv(ENV_PATH)

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "37ac")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

# ---- 校验规则（与 services/auth/validators.py 保持一致）----
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$")


def validate_username(name: str):
    if len(name) < 3 or len(name) > 50:
        return False, "用户名长度必须在 3-50 个字符之间"
    if not USERNAME_RE.match(name):
        return False, "用户名只能包含字母、数字、下划线和中文"
    return True, ""


def validate_password(pwd: str):
    if len(pwd) < 6 or len(pwd) > 128:
        return False, "密码长度必须在 6-128 个字符之间"
    return True, ""


def validate_email(email: str):
    return bool(EMAIL_RE.match(email)), "邮箱格式不正确"


def split_statements(sql_text: str):
    """将 SQL 文本按语句拆分（处理 -- 行注释与 /* */ 块注释），返回语句列表。"""
    statements = []
    buf = []
    in_block = False
    for raw in sql_text.splitlines():
        line = raw
        stripped = line.strip()
        if in_block:
            if "*/" in line:
                in_block = False
                line = line.split("*/", 1)[1]
            else:
                continue
        if stripped.startswith("--"):
            continue
        if "/*" in line and "*/" not in line:
            in_block = True
            line = line.split("/*", 1)[0]
        if not line.strip():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            statements.append("\n".join(buf).strip())
            buf = []
    if buf:
        statements.append("\n".join(buf).strip())
    return [s for s in statements if s]


def main():
    print("=" * 60)
    print("  37AC 数据库安装")
    print("=" * 60)
    print(f"  MySQL 主机 : {DB_HOST}")
    print(f"  数据库名   : {DB_NAME}")
    print(f"  安装脚本   : {INSTALL_SQL.name}")
    print("=" * 60)

    for k, v in (("DB_HOST", DB_HOST), ("DB_USER", DB_USER), ("DB_NAME", DB_NAME)):
        if not v:
            print(f"[错误] .env 缺少 {k}，请检查 src/server/.env", file=sys.stderr)
            sys.exit(1)

    # ---- 1) 连接 MySQL（不指定库，先建库）----
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            charset=DB_CHARSET,
            autocommit=True,
        )
    except Exception as e:
        print(f"[错误] 无法连接数据库: {e}", file=sys.stderr)
        sys.exit(1)

    # ---- 2) 执行 install.sql 建库建表（跳过默认 admin 的 INSERT）----
    sql_text = INSTALL_SQL.read_text(encoding="utf-8")
    statements = split_statements(sql_text)
    ddl_statements = [s for s in statements if not s.upper().startswith("INSERT")]

    try:
        with conn.cursor() as cur:
            for stmt in ddl_statements:
                cur.execute(stmt)
        print(f"[OK] 已建库 {DB_NAME} 并创建全部表结构（执行 {len(ddl_statements)} 条语句）")
    except Exception as e:
        print(f"[错误] 建库建表失败: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # ---- 3) 交互式输入管理员配置 ----
    print("\n---- 配置初始管理员 ----")

    while True:
        username = input("管理员用户名 [默认 admin]: ").strip() or "admin"
        ok, msg = validate_username(username)
        if ok:
            break
        print(f"  [提示] {msg}")

    while True:
        password = getpass.getpass("管理员密码: ")
        ok, msg = validate_password(password)
        if ok:
            break
        print(f"  [提示] {msg}")

    while True:
        email = input("管理员邮箱: ").strip()
        ok, msg = validate_email(email)
        if ok:
            break
        print(f"  [提示] {msg}")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ---- 4) 写入管理员（已存在则更新，否则插入）----
    tbl = f"`{DB_NAME}`.`users`"
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {tbl} WHERE username = %s", (username,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    f"UPDATE {tbl} SET password_hash=%s, email=%s, role='admin', status=1 WHERE id=%s",
                    (password_hash, email, row[0]),
                )
                print(f"[OK] 管理员 {username} 已更新")
            else:
                cur.execute(
                    f"INSERT INTO {tbl} (username, password_hash, email, role, status) VALUES (%s,%s,%s,'admin',1)",
                    (username, password_hash, email),
                )
                print(f"[OK] 管理员 {username} 已创建")
        print("[完成] 数据库安装成功，可使用该管理员账号登录系统。")
    except Exception as e:
        print(f"[错误] 写入管理员失败: {e}", file=sys.stderr)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
