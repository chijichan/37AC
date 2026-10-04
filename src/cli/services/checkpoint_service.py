# -*- coding: utf-8 -*-
"""检查点系统：把"一份模型状态"（权重 + classes.json + config.json）作为**原子快照**管理。

为什么需要：这三样原本是分别写入 saves/models/ 的，任何一处漏写就会出现"权重新、config 旧"
（已真实发生过：config.json 停在 9/27 而权重是 10/1，导致节点同步看不到新模型）。
现在一次 create_checkpoint() 就把三者一致地快照下来，回滚也是三者一起回。

布局（**不改动现行文件布局**，节点同步逻辑零影响）：
    saves/models/                        ← current：权重/classes/config 仍在原位
      checkpoints/
        index.json                       ← 索引（按时间倒序）
        <version>-<时间戳>-<kind>/       ← model.pth + classes.json + config.json + meta.json
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from config.base import CLASSES_JSON_PATH, MODEL_DIR, MODEL_INFO_PATH, MODEL_PATH
from config.log_config import get_logger

logger = get_logger("checkpoint")

# 权重文件名（config.base 里是内联读 env 的，这里显式取出来，便于测试替换）
MODEL_FILENAME = Path(MODEL_PATH).name

INDEX_NAME = "index.json"
# 这些 kind 不参与自动清理（迁移基线 / 回滚前的保底）
PROTECTED_KINDS = ("baseline", "pre-restore")
KINDS = ("best", "final", "interrupt", "baseline", "pre-restore", "manual")


# ---------------------------------------------------------------- 路径（便于测试替换）
def checkpoint_dir() -> Path:
    return Path(MODEL_DIR) / "checkpoints"


def index_path() -> Path:
    return checkpoint_dir() / INDEX_NAME


def current_files() -> dict:
    """current 状态对应的三个文件（逻辑名 → 路径）。"""
    return {
        "model": Path(MODEL_DIR) / MODEL_FILENAME,
        "classes": Path(CLASSES_JSON_PATH),
        "config": Path(MODEL_INFO_PATH),
    }


# ---------------------------------------------------------------- 工具
def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    """原子写：先写临时文件再替换，避免中途崩溃留下半个索引。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _dir_size_mb(path: Path) -> float:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return round(total / 1024 / 1024, 2)


def load_index() -> list:
    data = _read_json(index_path(), [])
    if isinstance(data, dict):            # 兼容 {"items": [...]} 形式
        data = data.get("items") or []
    return data if isinstance(data, list) else []


def _save_index(items: list) -> None:
    _write_json(index_path(), items)


def _current_version() -> str:
    info = _read_json(current_files()["config"], {}) or {}
    return str(info.get("version") or "unknown")


# ---------------------------------------------------------------- 核心 API
def create_checkpoint(kind: str = "manual", version: str = None, accuracy=None, note: str = "") -> dict:
    """把当前模型状态快照成一个检查点；权重不存在时跳过（返回 None）。"""
    kind = (kind or "manual").strip().lower()
    if kind not in KINDS:
        kind = "manual"

    files = current_files()
    if not files["model"].exists():
        logger.warning("权重文件不存在，跳过检查点: %s", files["model"])
        return None

    version = str(version or _current_version())
    name = f"{version}-{_stamp()}-{kind}"
    target = checkpoint_dir() / name
    suffix = 1
    while target.exists():
        target = checkpoint_dir() / f"{name}_{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=True)

    saved = {}
    for key, src in files.items():
        if src.exists():
            dst = target / src.name
            shutil.copy2(src, dst)
            saved[key] = {"file": src.name, "size_mb": round(dst.stat().st_size / 1024 / 1024, 2)}

    meta = {
        "name": target.name,
        "kind": kind,
        "version": version,
        "accuracy": accuracy,
        "note": note,
        "created_at": _now(),
        "files": saved,
        "size_mb": _dir_size_mb(target),
    }
    _write_json(target / "meta.json", meta)

    items = [it for it in load_index() if it.get("name") != meta["name"]]
    items.insert(0, meta)
    _save_index(items)
    logger.info("检查点已创建: %s（%s, %.1f MB）", meta["name"], kind, meta["size_mb"])
    return meta


def list_checkpoints() -> list:
    """按创建时间倒序列出检查点，并标注目录是否仍存在。"""
    items = load_index()
    for it in items:
        it["exists"] = (checkpoint_dir() / str(it.get("name"))).is_dir()
    items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return items


def get_checkpoint(name: str) -> dict:
    for it in load_index():
        if it.get("name") == name:
            it["exists"] = (checkpoint_dir() / name).is_dir()
            return it
    return None


def restore_checkpoint(name: str, backup_current: bool = True) -> dict:
    """把检查点回滚为 current（权重/classes/config 三者一起回）。"""
    item = get_checkpoint(name)
    if not item or not item.get("exists"):
        logger.error("检查点不存在或目录已丢失: %s", name)
        return None

    result = {"restored": name}
    if backup_current:
        backup = create_checkpoint(kind="pre-restore", note=f"回滚前保底（将被 {name} 覆盖）")
        result["backup"] = (backup or {}).get("name")

    src_dir = checkpoint_dir() / name
    restored = {}
    for key, dst in current_files().items():
        entry = (item.get("files") or {}).get(key)
        src = src_dir / (entry or {}).get("file", dst.name)
        if not src.exists():
            continue
        shutil.copy2(src, dst)
        restored[key] = dst.name
    result["files"] = restored
    logger.warning("已回滚到检查点 %s → %s", name, ", ".join(restored.values()))
    return result


def delete_checkpoint(name: str, force: bool = False) -> bool:
    item = get_checkpoint(name)
    if not item:
        return False
    if item.get("kind") in PROTECTED_KINDS and not force:
        logger.warning("检查点 %s 属于保护类型（%s），如需删除请加 force=True", name, item.get("kind"))
        return False
    shutil.rmtree(checkpoint_dir() / name, ignore_errors=True)
    _save_index([it for it in load_index() if it.get("name") != name])
    logger.info("检查点已删除: %s", name)
    return True


def prune(keep: int = 10, max_total_mb: float = 2000) -> dict:
    """按"保留最近 N 个 + 总体积上限"清理，保护类型永不自动删。"""
    items = list_checkpoints()
    sizes = {it.get("name"): float(it.get("size_mb") or 0) for it in items}
    total = sum(sizes.values())

    removed = []
    for idx, it in enumerate(items):
        name = it.get("name")
        if it.get("kind") in PROTECTED_KINDS:
            continue
        over_count = idx >= max(0, int(keep))
        over_size = total > float(max_total_mb)
        if not (over_count or over_size):
            continue
        if delete_checkpoint(name):
            removed.append(name)
            total -= sizes.get(name, 0)
    result = {"removed": removed, "kept": len(list_checkpoints()), "total_mb": round(total, 2)}
    logger.info("检查点清理: 删除 %d 个，保留 %d 个，合计 %.1f MB",
                len(removed), result["kept"], result["total_mb"])
    return result


def current_info() -> dict:
    """当前模型信息（版本/类别数/哈希/来源基模/最佳正确率）。"""
    info = _read_json(current_files()["config"], {}) or {}
    classes = _read_json(current_files()["classes"], None)
    weights = current_files()["model"]
    return {
        "version": info.get("version"),
        "trained_at": info.get("trained_at"),
        "class_count": len(classes) if isinstance(classes, dict) else (len(classes) if isinstance(classes, list) else None),
        "model_file": weights.name,
        "model_exists": weights.exists(),
        "model_size_mb": round(weights.stat().st_size / 1024 / 1024, 2) if weights.exists() else 0,
        "model_sha256": ((info.get("model") or {}).get("sha256")) or None,
        # 基模来自 config.json 的 training.base（顶层没有 base 字段，
        # 旧写法会永远显示 imagenet-resnet18，与实际训练用的基模不符）
        "base": ((info.get("training") or {}).get("base")
                 or info.get("base") or info.get("pretrained_base") or "未知（旧模型无记录）"),
        "best_val_acc": (info.get("training") or {}).get("best_val_acc"),
        "dataset": (info.get("training") or {}).get("dataset"),
        "image_size": (info.get("training") or {}).get("image_size"),
        "batch_size": (info.get("training") or {}).get("batch_size"),
        "eval": (info.get("training") or {}).get("eval"),
        "checkpoints": len(load_index()),
    }
