# -*- coding: utf-8 -*-
r"""从备份恢复 classes.json 的 features_used / tags（合并式，不覆盖已有非空元数据）。

用法（仓库根目录执行）：
    .\.venv\Scripts\python.exe scripts\restore_classes_meta.py            # 自动选元数据最全的备份
    .\.venv\Scripts\python.exe scripts\restore_classes_meta.py --list     # 只列出备份情况
    .\.venv\Scripts\python.exe scripts\restore_classes_meta.py --from saves\models\_bak\classes_bak_xxx.json
"""
import argparse
import glob
import json
import shutil
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "src" / "cli" / "saves" / "models" / "classes.json"
BAK_DIR = TARGET.parent / "_bak"


def _load(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _meta_count(data: dict) -> int:
    return sum(1 for v in data.values() if isinstance(v, dict) and (v.get("features_used") or v.get("tags")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=None, help="指定备份文件")
    ap.add_argument("--list", action="store_true", help="只列出备份")
    args = ap.parse_args()

    baks = sorted(glob.glob(str(BAK_DIR / "classes_bak_*.json")))
    rows = []
    for b in baks:
        d = _load(Path(b))
        rows.append((b, len(d), _meta_count(d)))
    rows.sort(key=lambda r: r[2], reverse=True)

    print("备份文件（按元数据完整度排序，前 8 个）：")
    for b, total, meta in rows[:8]:
        print("  %-56s %3d 类 / %3d 含特征" % (Path(b).name, total, meta))
    if args.list or not rows:
        return

    src = Path(args.src) if args.src else Path(rows[0][0])
    backup_data = _load(src)
    current = _load(TARGET)
    if not backup_data or not current:
        print("[x] 数据缺失：备份 %s，当前 %s" % (bool(backup_data), bool(current)))
        return

    filled = 0
    for key, entry in current.items():
        old = backup_data.get(key)
        if not isinstance(old, dict) or not isinstance(entry, dict):
            continue
        for field in ("features_used", "tags"):
            if (not entry.get(field)) and old.get(field):
                entry[field] = list(old[field])
                filled += 1
    if not filled:
        print("无需恢复：当前 classes.json 的元数据已经完整（或缺备份里也没有）")
        return

    shutil.copy2(TARGET, BAK_DIR / ("classes_before_restore_%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S")))
    TARGET.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已从 %s 恢复 %d 个字段；现在 %d/%d 个类含 features_used/tags"
          % (src.name, filled, _meta_count(current), len(current)))
    print("恢复前状态已另存到 _bak/classes_before_restore_*.json")


if __name__ == "__main__":
    main()
