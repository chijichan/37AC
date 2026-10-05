# -*- coding: utf-8 -*-
"""真实口径评估：同一批图，跑四种口径，回答"模型在线上到底行不行"。

口径（mode）：
  cropped      数据集裁剪图，仅分类器          ← 训练日志里的 val 就是这个口径（最乐观）
  raw          原始未裁剪图，仅分类器          ← 只有域差异，没有检测误差
  detect       原始图 + 完整流程（YOLO 裁剪 + 质量门控）
  detect_nogate 同上但**关闭**质量门控          ← 与 detect 构成门控 A/B

用法见 scripts/eval_pipeline.py；结果可写进训练报告与 config.json。
"""

import random
from pathlib import Path

from config.base import CLASSES_JSON_PATH, DATASET_DIR, MODEL_PATH, CROPPED_DATASET_DIR
from config.log_config import get_logger

logger = get_logger("eval")

MODES = ("cropped", "raw", "detect", "detect_nogate")
MODE_LABELS = {
    "cropped": "数据集裁剪图",
    "raw": "原始图·仅分类",
    "detect": "原始图+检测(门控开)",
    "detect_nogate": "原始图+检测(门控关)",
}
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _scan(root: Path) -> dict:
    """扫描 <root>/<IP>/<角色>/ 结构 → {label: [图片路径]}。"""
    groups = {}
    root = Path(root)
    if not root.is_dir():
        return groups
    for ip_dir in sorted(root.iterdir()):
        if not ip_dir.is_dir():
            continue
        for role_dir in sorted(ip_dir.iterdir()):
            if not role_dir.is_dir():
                continue
            imgs = [p for p in role_dir.iterdir() if p.suffix.lower() in EXTS]
            if imgs:
                groups["%s/%s" % (ip_dir.name, role_dir.name)] = imgs
    return groups


def pick_samples(per_class: int = 1, limit: int = None, source: str = "raw", seed: int = 7):
    """按固定种子抽样：source=raw 用 DATASET_DIR（原始图），cropped 用 CROPPED_DATASET_DIR。"""
    root = Path(DATASET_DIR) if source == "raw" else Path(CROPPED_DATASET_DIR)
    groups = _scan(root)
    rnd = random.Random(seed)
    samples = []
    for label, imgs in groups.items():
        take = min(per_class, len(imgs))
        for p in rnd.sample(imgs, take):
            samples.append((label, str(p)))
    if limit:
        samples = samples[: int(limit)]
    logger.info("抽样: %d 张（%s，每类 %d 张，共 %d 类）", len(samples), root, per_class, len(groups))
    return samples


def _model_device(model):
    """返回模型实际运行设备；优先读取参数设备，兼容包装模型/DirectML 私有设备。"""
    import torch

    try:
        params = list(getattr(model, "parameters", lambda: [])())
        if params:
            return params[0].device
    except Exception:
        pass

    device = getattr(model, "device", None)
    if device is None:
        return None
    try:
        return torch.device(device)
    except Exception:
        return device


def _classifier():
    """加载分类器（仅分类器口径用，不经过 YOLO）。"""
    import torch
    from models.character_model import CharacterRecognitionModel
    from prediction.predictor import get_predict_transforms
    from utils.file_utils import load_classes_from_file

    # 必须按 classes.json 里的 id 排序还原**训练时的类别顺序**：
    # 直接用文件返回的顺序会导致 top-1 索引与名称错位（表现为 193 张全错、0%）
    from utils.file_utils import load_classes_json_data

    data = load_classes_json_data(str(CLASSES_JSON_PATH)) or {}

    def _order(kv):
        # 正常类别 id 是数字（训练时的索引）；脏数据/手工条目可能是字符串 → 排到后面且不报错
        try:
            return (0, int((kv[1] or {}).get("id")))
        except Exception:
            return (1, 0)

    classes = [k for k, _v in sorted(data.items(), key=_order)] \
        or (load_classes_from_file(str(CLASSES_JSON_PATH)) or [])
    model = CharacterRecognitionModel(len(classes)).load_model(str(MODEL_PATH), len(classes))
    model.eval()
    return model, classes, get_predict_transforms(), torch


def evaluate(mode: str = "raw", per_class: int = 1, limit: int = None):
    """跑一种口径，返回 {mode,total,top1,top3,detected,no_detect,acc_detected,acc_missed}。"""
    assert mode in MODES, "未知口径: %s" % mode
    if mode == "cropped":
        samples = pick_samples(per_class, limit, source="cropped")
    else:
        samples = pick_samples(per_class, limit, source="raw")

    result = {"mode": mode, "label": MODE_LABELS[mode], "total": len(samples),
              "top1": 0, "top3": 0, "detected": 0, "no_detect": 0,
              "acc_detected": 0, "acc_missed": 0, "failures": [], "ok": 0}

    if mode in ("cropped", "raw"):
        model, classes, transform, torch = _classifier()
        idx = {name: i for i, name in enumerate(classes)}
        with torch.no_grad():
            for label, path in samples:
                try:
                    from PIL import Image
                    with Image.open(path) as im:
                        x = transform(im.convert("RGB")).unsqueeze(0)
                    model_device = _model_device(model)
                    if model_device is not None:
                        x = x.to(model_device)
                    probs = torch.softmax(model(x), dim=1)[0]
                    k = min(3, len(classes))
                    top = torch.topk(probs, k).indices.tolist()
                    top_names = [classes[i] for i in top]
                    hit = top_names[0] == label
                    result["top1"] += int(hit)
                    result["top3"] += int(label in top_names)
                    if not hit:
                        result["failures"].append({"true": label, "pred": top_names[0], "path": path})
                except Exception as e:
                    logger.debug("评估失败 %s: %s", path, e)
    else:
        # 完整流程；detect_nogate 临时关掉质量门控
        import config.base as cfg
        from prediction.predictor import predict_image
        saved_gate = getattr(cfg, "CROP_QUALITY_GATE", True)
        if mode == "detect_nogate":
            cfg.CROP_QUALITY_GATE = False
        try:
            for label, path in samples:
                try:
                    res = predict_image(path)
                except Exception as e:
                    logger.debug("评估失败 %s: %s", path, e)
                    continue
                names = [p.get("name") for p in (res.get("class_probs") or [])]
                hit = bool(names) and names[0] == label
                result["top1"] += int(hit)
                result["top3"] += int(label in names[:3])
                found = bool(res.get("characters"))
                result["detected"] += int(found)
                result["no_detect"] += int(not found)
                if found:
                    result["acc_detected"] += int(hit)
                else:
                    result["acc_missed"] += int(hit)
                if not hit:
                    result["failures"].append({"true": label, "pred": (names or [None])[0],
                                               "path": path, "detected": found})
        finally:
            cfg.CROP_QUALITY_GATE = saved_gate

    total = max(1, result["total"])
    result["ok"] = result["top1"]
    result["acc"] = round(100.0 * result["top1"] / total, 2)
    result["acc_top3"] = round(100.0 * result["top3"] / total, 2)
    if result["detected"]:
        result["acc_detected"] = round(100.0 * result["acc_detected"] / result["detected"], 2)
    if result["no_detect"]:
        result["acc_missed"] = round(100.0 * result["acc_missed"] / result["no_detect"], 2)
        result["detect_rate"] = round(100.0 * result["detected"] / total, 2)
    result["failures"] = result["failures"][:20]
    logger.info("口径 %s: top-1 %.2f%%（%d/%d）", result["label"], result["acc"], result["top1"], result["total"])
    return result


def compare(modes=None, per_class: int = 1, limit: int = None) -> dict:
    """依次跑多个口径，返回 {mode: result} 与最大值对比摘要。"""
    modes = modes or ("cropped", "raw", "detect")
    results = {}
    for mode in modes:
        try:
            results[mode] = evaluate(mode, per_class=per_class, limit=limit)
        except Exception as e:
            logger.error("口径 %s 评估失败: %s", mode, e)
            results[mode] = {"mode": mode, "label": MODE_LABELS.get(mode, mode), "acc": None,
                             "total": 0, "error": str(e)}
    return results
