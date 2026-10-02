# -*- coding: utf-8 -*-
r"""批量识别源数据集（**直接调用本地识别模块**，不走 HTTP 接口）

用途：源目录里的图没标注，按角色清理 ——
  · 识别结果 = 目标角色且置信度达标        -> 保留（不动）
  · 其他情况（别的角色 / 置信度低 / 失败） -> 移到 <quarantine-dir>\<角色名>\

默认是「预览模式」，只打印不移动；确认无误后加 --apply 才真正移动文件。

调用的是 CLI 里的识别模块：
  · --channel 37ac（默认）：prediction.predictor.predict_image      —— 本地 YOLO + ResNet
  · --channel llm         ：prediction.predictor.predict_image_llm  —— 多模态大模型
模型与类别取自 src/cli/saves/models/（classes.json 里的类别名，如 蔚蓝档案/安守实里）。

示例（先预览，再执行）：
  python scripts/batch_recognize.py --character 安守实里
  python scripts/batch_recognize.py --character 安守实里 --apply
  python scripts/batch_recognize.py --dir "D:\datasets\Img\蔚蓝档案\安守实里" --character 安守实里 --threshold 0.75 --apply

说明：不需要服务端/节点在线；模型是进程内加载（首次约 5~15 秒）。
"""

import argparse
import csv
import json
import os
import shutil
import sys
import time
from pathlib import Path

# ---------- 屏蔽 MediaPipe / TensorFlow Lite 的 C++ 警告 ----------
# W0000 ... inference_feedback_manager.cc: "Disabling support for feedback tensors"
# 只是 TFLite 的微优化提示，不影响结果；下面三个环境变量必须在 import mediapipe 之前设置
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")   # TensorFlow/TFLite：只留 fatal
os.environ.setdefault("ABSL_MIN_LOG_LEVEL", "3")     # absl 的 C++ 日志（W0000 就来自它）
os.environ.setdefault("GLOG_minloglevel", "3")       # glog 风格日志：ERROR 以上

# ---------- 把 CLI 源码目录加入导入路径（脚本位于仓库根的 scripts/ 下）----------
REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_DIR = REPO_ROOT / "src" / "cli"
for _p in (str(CLI_DIR), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 支持的图片扩展名
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
# 源数据集根目录（角色目录默认在这里下面）
SOURCE_ROOT = Path(r"D:\datasets\Img\蔚蓝档案")
# 默认移出目录
DEFAULT_QUARANTINE = Path(r"D:\datasets\_tmp")


def parse_args():
    p = argparse.ArgumentParser(description="批量识别源数据集并分流（默认预览，--apply 才移动）")
    p.add_argument("--character", "-c", default=None,
                   help="角色名；源目录默认 <源根目录>\\<角色>，期望类别默认 蔚蓝档案/<角色>")
    p.add_argument("--dir", "-d", default=None, help="直接指定源目录（优先于按 --character 拼路径）")
    p.add_argument("--channel", default="37ac", choices=["37ac", "llm"], help="识别方式：37ac=本地模型，llm=大模型")
    p.add_argument("--threshold", type=float, default=0.70, help="置信度下限（0-1），低于它视为不确定")
    p.add_argument("--quarantine-dir", default=str(DEFAULT_QUARANTINE),
                   help="移出根目录（默认 W:\\临时文件夹），实际移动到 <该目录>\\<角色>\\")
    p.add_argument("--expect", default=None, help="期望的完整类别名（默认 蔚蓝档案/<角色>）")
    p.add_argument("--apply", action="store_true", help="真正移动文件（不加就是预览）")
    p.add_argument("--recursive", action="store_true", help="递归处理子目录")
    p.add_argument("--limit", type=int, default=0, help="只处理前 N 张（调试用，0=全部）")
    p.add_argument("--sleep", type=float, default=0.0, help="每张之间额外等待秒数（降负载用）")
    p.add_argument("--detect", action="store_true",
                   help="启用 YOLO 检测裁剪（**默认关闭**：整图分类，实测更准且规避 YOLO 推理报错）")
    p.add_argument("--unknown-dir", default="未识别",
                   help="识别失败时的移出子目录名（默认 未识别）；能识别出的按【识别到的角色名】建子目录")
    p.add_argument("--csv", action="store_true",
                   help="额外写一份 CSV 到 <仓库>/saves/reports（默认只打印到控制台）")
    p.add_argument("--show-keep", action="store_true",
                   help="逐条打印『保留』的图片（默认只统计，避免刷屏）")
    p.add_argument("--temp-dir", default=None,
                   help="裁剪暂存根目录（默认 <仓库>/saves/tmp_crops）；裁剪图会留在这里备用")
    return p.parse_args()


def redirect_temp_dirs(temp_root: Path):
    r"""把临时目录**彻底接管**到 temp_root（不依赖环境变量是否生效）。

    1) TEMP / TMP / tempfile.tempdir 一律指向 temp_root；
    2) 直接把 tempfile.mkdtemp 换成"只在 temp_root 下建子目录"的实现 ——
       这样无论环境变量、缓存怎么变，裁剪图都只会落到这里（可保留备用、可一键清理），
       不会再出现在工作区根目录。
    """
    import itertools
    import tempfile

    temp_root.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(temp_root)
    os.environ["TMP"] = str(temp_root)
    tempfile.tempdir = str(temp_root)

    counter = itertools.count(1)

    def _mkdtemp(prefix=None, suffix=None, dir=None):
        for _ in range(1000):
            path = temp_root / ("%s%04d%s" % (prefix or "tmp", next(counter), suffix or ""))
            try:
                path.mkdir()
                return str(path)
            except FileExistsError:
                continue
        raise FileExistsError("无法在 %s 下创建临时目录" % temp_root)

    tempfile.mkdtemp = _mkdtemp
    return temp_root


def iter_images(root: Path, recursive: bool):
    """遍历目录下的图片文件（可选递归），按名称排序。"""
    it = root.rglob("*") if recursive else root.glob("*")
    for path in sorted(it):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            yield path


def to_ratio(value):
    """把置信度统一成 0-1（模块可能给 0-100 或 0-1）。"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return num / 100.0 if num > 1.0 else num


def load_predictor(channel: str):
    """按需导入识别函数（导入会加载 torch/模型，--help 时不必付这个代价）。"""
    if channel == "llm":
        from prediction.predictor import predict_image_llm as fn
    else:
        from prediction.predictor import predict_image as fn
    return fn


def recognize(fn, path: Path, channel: str):
    """识别单张图，返回 (类别名|None, 置信度 0-1, 明细)。"""
    result = fn(str(path))
    if not isinstance(result, dict) or not result.get("success"):
        return None, 0.0, {"error": (result or {}).get("error") or "识别失败"}
    probs = result.get("class_probs") or []
    if not probs:
        return None, 0.0, {"error": "无候选结果"}
    top = probs[0]
    name = str(top.get("name") or top.get("label") or "").strip()
    prob = to_ratio(top.get("prob", top.get("confidence", 0)))
    return (name or None), prob, {
        "source": "class_probs",
        "top": probs[:3],
        "crop_method": result.get("crop_method"),
        "character_count": result.get("character_count"),
    }


def move_aside(path: Path, quarantine: Path, subdir: str):
    r"""移到 <quarantine>\<subdir>\（subdir = 识别到的角色名），同名自动加 _dupN，绝不覆盖。"""
    dest_dir = quarantine / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    index = 1
    while dest.exists():
        dest = dest_dir / ("%s_dup%d%s" % (path.stem, index, path.suffix))
        index += 1
    shutil.move(str(path), str(dest))
    return dest


def main():
    args = parse_args()
    character = (args.character or "").strip()
    source = Path(args.dir) if args.dir else SOURCE_ROOT / character
    if not source.is_dir():
        print("源目录不存在: %s" % source)
        return 2
    if not character:
        character = source.name
    expected = args.expect or ("蔚蓝档案/" + character)
    quarantine = Path(args.quarantine_dir)

    # 裁剪暂存：固定位置、保留备用（每张一个 37ac_yolo_* 子目录）
    temp_root = Path(args.temp_dir) if args.temp_dir else (REPO_ROOT / "saves" / "tmp_crops")
    temp_used = redirect_temp_dirs(temp_root)

    images = list(iter_images(source, args.recursive))
    if args.limit > 0:
        images = images[: args.limit]

    print("=" * 64)
    print("源目录   : %s" % source)
    print("目标角色 : %s（期望类别 %s，阈值 %.2f）" % (character, expected, args.threshold))
    print("识别方式 : %s（进程内直调识别模块，不经接口）" % args.channel)
    print("移出目录 : %s\【识别到的角色名】（识别失败 → %s）" % (quarantine, args.unknown_dir))
    print("裁剪暂存 : %s（识别过程中的裁剪图留在这里，可随时清理）" % temp_used)
    print("图片数量 : %d 张 | 模式: %s"
          % (len(images), "执行移动（--apply）" if args.apply else "预览（不动文件）"))
    print("=" * 64)

    print("正在加载识别模块（首次较慢，请稍候）...")
    fn = load_predictor(args.channel)

    if not args.detect and args.channel != "llm":
        # 默认关掉 YOLO 检测裁剪：predict_image 运行时读取该开关 → 直接整图分类
        # （实测整图 79.0% 优于 YOLO 裁剪 71.3%，且可规避 'Cannot set version_counter' 报错）
        import prediction.predictor as _predictor
        _predictor.YOLO_ENABLED = False          # 关闭单张最佳人物裁剪
        _predictor.MULTI_CHARACTER_ENABLED = False   # ★ 关闭多人检测分支（否则仍会调 YOLO）
        _predictor.YOLO_AVAILABLE = False        # 双保险：任何依赖 YOLO 的分支都跳过
        print("识别模式 : 整图分类（已关闭 YOLO 检测裁剪；要开启加 --detect）")

    stats = {"keep": 0, "move": 0, "error": 0}
    rows = []
    started = time.time()

    for done, path in enumerate(images, 1):
        try:
            name, prob, detail = recognize(fn, path, args.channel)
        except Exception as exc:
            name, prob, detail = None, 0.0, {"error": "%s: %s" % (type(exc).__name__, exc)}

        if name is None:
            verdict = "error"                      # 识别失败：留在原地，人工再看
        elif name == expected and prob >= args.threshold:
            verdict = "keep"                       # 确定是目标角色：保留
        else:
            verdict = "move"                       # 别的角色或置信度不足：移出
        # 移出子目录 = 识别到的角色名（类别名 "IP/角色" 取后半段）；识别失败归到 未识别
        dest_subdir = (name.split("/")[-1].strip() or name) if name else args.unknown_dir
        if args.apply and verdict == "move":
            try:
                moved_to = move_aside(path, quarantine, dest_subdir)
                detail["moved_to"] = str(moved_to)
            except Exception as exc:
                verdict = "error"
                detail = {"error": "移动失败: %s" % exc}

        stats[verdict] = stats.get(verdict, 0) + 1
        rows.append({
            "file": path.name,
            "verdict": verdict,
            "predicted": name or "",
            "confidence": "%.3f" % prob,
            "dest": dest_subdir if verdict == "move" else "",
            "detail": json.dumps(detail, ensure_ascii=False)[:200],
        })
        if done % 20 == 0 or done == len(images):
            print("  进度 %d/%d | 保留 %d 移出 %d 失败 %d | %.1fs"
                  % (done, len(images), stats["keep"], stats["move"], stats["error"],
                     time.time() - started))
        if args.sleep > 0:
            time.sleep(args.sleep)

    # ---------- 报告：直接打印到控制台（不往源目录写文件，避免权限问题）----------
    moved = [r for r in rows if r["verdict"] == "move"]
    errors = [r for r in rows if r["verdict"] == "error"]
    kept = [r for r in rows if r["verdict"] == "keep"]

    print("-" * 64)
    print("判定明细（目标角色 %s，阈值 %.2f）:" % (expected, args.threshold))
    if args.show_keep:
        for r in kept:
            print("  [保留] %-44s %s %s" % (r["file"], r["predicted"] or "-", r["confidence"]))
    else:
        print("  [保留] %d 张（不逐条打印；要看全部加 --show-keep）" % len(kept))
    for r in moved:
        dest = r.get("dest") or ""
        if not dest:                      # 兜底：按预测角色名推出去处
            pred = (r.get("predicted") or "").strip()
            dest = pred.split("/")[-1].strip() if pred else args.unknown_dir
        print("  [移出] %-40s -> %-14s 预测=%s 置信度=%s"
              % (r["file"], dest, r["predicted"] or "(无)", r["confidence"]))
    for r in errors:
        print("  [失败] %-44s %s" % (r["file"], (r["detail"] or "")[:90]))
    print("-" * 64)

    if args.csv:
        report_dir = REPO_ROOT / "saves" / "reports"
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            report = report_dir / ("recognize_%s_%s.csv" % (character, time.strftime("%Y%m%d_%H%M%S")))
            with open(report, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=["file", "verdict", "predicted", "confidence", "detail"])
                writer.writeheader()
                writer.writerows(rows)
            print("CSV 报告: %s" % report)
        except Exception as exc:
            print("CSV 报告写入失败（已忽略，控制台明细仍然完整）: %s" % exc)

    print("=" * 64)
    print("完成：保留 %d 张，移出 %d 张，失败 %d 张（%.1fs）"
          % (stats["keep"], stats["move"], stats["error"], time.time() - started))
    if not args.apply and stats["move"]:
        print("提示：这是预览。确认无误后加 --apply 再跑一次即可真正移动。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
