# -*- coding: utf-8 -*-
r"""真实口径评估（含裁剪质量门控 A/B）。

在仓库根目录执行：
    .\.venv\Scripts\python.exe scripts\eval_pipeline.py                     # 默认三档，每类 1 张
    .\.venv\Scripts\python.exe scripts\eval_pipeline.py --per-class 3
    .\.venv\Scripts\python.exe scripts\eval_pipeline.py --modes detect,detect_nogate   # 门控 A/B
    .\.venv\Scripts\python.exe scripts\eval_pipeline.py --limit 20           # 快速冒烟
结果同时写入 saves/reports/eval-<时间戳>.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "cli"))
sys.path.insert(0, str(ROOT / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="cropped,raw,detect",
                    help="cropped,raw,detect,detect_nogate 逗号分隔")
    ap.add_argument("--per-class", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 张（冒烟用）")
    args = ap.parse_args()

    from services.eval_service import MODE_LABELS, compare

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    results = compare(modes, per_class=args.per_class, limit=args.limit)

    print("\n" + "=" * 68)
    print("  真实口径评估（每类 %d 张%s）" % (args.per_class, "，限制 %d 张" % args.limit if args.limit else ""))
    print("=" * 68)
    print("  %-26s %8s %8s %8s" % ("口径", "样本", "top-1", "top-3"))
    for mode, r in results.items():
        print("  %-26s %8s %7s%% %7s%%" % (MODE_LABELS.get(mode, mode), r.get("total"),
                                           r.get("acc"), r.get("acc_top3")))
    base = results.get("cropped", {}).get("acc")
    for mode, r in results.items():
        if base and r.get("acc") is not None and mode != "cropped":
            print("  · %s 相对数据集口径: %+.2f 点" % (MODE_LABELS.get(mode, mode), r["acc"] - base))
    gate_on = results.get("detect", {}).get("acc")
    gate_off = results.get("detect_nogate", {}).get("acc")
    if gate_on is not None and gate_off is not None:
        verdict = "门控有效（开启更高）" if gate_on > gate_off else (
            "门控无效/有害（关闭更高）" if gate_on < gate_off else "门控无影响")
        print("  → 裁剪质量门控 A/B: 开 %.2f%% vs 关 %.2f%% ⇒ %s" % (gate_on, gate_off, verdict))

    out_dir = ROOT / "src" / "cli" / "saves" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / ("eval-%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_file.write_text(json.dumps({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "per_class": args.per_class, "limit": args.limit,
                                    "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  结果已保存: %s" % out_file)
    print("=" * 68)


if __name__ == "__main__":
    main()
