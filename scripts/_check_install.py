# -*- coding: utf-8 -*-
"""静态核对 install.sql 与源 dump 的表结构一致性（不连接数据库）"""
import re

def tables(path):
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"CREATE TABLE[^(]*`(\w+)`\s*\((.*?)\)\s*ENGINE", txt, re.S):
        name = m.group(1)
        body = m.group(2)
        fields = re.findall(r"\n\s*`(\w+)`", body)
        out[name] = fields
    return out

a = tables(r"d:\下载\37ac.sql")
b = tables(r"scripts/install.sql")
print("源dump 表:", list(a.keys()))
print("安装脚本表:", list(b.keys()))
print("表集合一致:", set(a.keys()) == set(b.keys()))
for k in a:
    ok = set(a[k]) == set(b.get(k, []))
    print(f"  {k}: {'一致' if ok else '不一致 ' + str(set(a[k]) ^ set(b.get(k, [])))}")

# 额外确认：安装脚本不含 INSERT 业务数据
txt = open(r"scripts/install.sql", encoding="utf-8").read()
ins = re.findall(r"^\s*INSERT INTO", txt, re.M)
print("安装脚本 INSERT 语句数（应为0）:", len(ins))
