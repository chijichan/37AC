# -*- coding: utf-8 -*-
"""训练基模（pretrained base）管理。

一个"基模"= saves/models/pretrained/<id>/ 目录，描述文件优先 37ac-base.json（本项目的字段），
其次回退读仓库自带的 meta.json（animetimm 的 Danbooru 标签元数据，字段不同、缺字段时用 ImageNet 默认）。

注意：预训练权重是大文件，**不入 git**（saves/models/pretrained/ 已在 .gitignore）。
"""

import json
import struct
from pathlib import Path

from config.base import MODEL_DIR
from config.log_config import get_logger

logger = get_logger("pretrained")

PRETRAINED_DIR_NAME = "pretrained"
DESC_NAME = "37ac-base.json"
DEFAULT_BASE = "imagenet-resnet18"
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

_SAFETENSORS_DTYPES = {
    "F64": "float64", "F32": "float32", "F16": "float16", "BF16": "bfloat16",
    "I64": "int64", "I32": "int32", "I16": "int16", "I8": "int8", "U8": "uint8", "BOOL": "bool",
}


def pretrained_dir() -> Path:
    return Path(MODEL_DIR) / PRETRAINED_DIR_NAME


def _read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def read_desc(folder: Path) -> dict:
    """读取基模描述：37ac-base.json 优先，其次 meta.json（不同仓库字段各异）。"""
    desc = _read_json(Path(folder) / DESC_NAME)
    if isinstance(desc, dict) and desc:
        return desc
    fallback = _read_json(Path(folder) / "meta.json") or {}
    return fallback if isinstance(fallback, dict) else {}


def list_bases() -> list:
    bases = []
    root = pretrained_dir()
    if not root.is_dir():
        return bases
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        desc = read_desc(d)
        weights = _find_weights(d, desc)
        bases.append({
            "id": d.name,
            "dir": str(d),
            "has_desc": (d / DESC_NAME).exists(),
            "weights": weights.name if weights else None,
            "weights_mb": round(weights.stat().st_size / 1024 / 1024, 1) if weights else 0,
            "arch": desc.get("arch") or desc.get("architecture"),
            "source": desc.get("source") or desc.get("hf_hub_id"),
            "input_size": desc.get("input_size"),
            "mean": desc.get("mean") or list(IMAGENET_MEAN),
            "std": desc.get("std") or list(IMAGENET_STD),
            "license": desc.get("license"),
        })
    return bases


def get_base(base_id: str) -> dict:
    if not base_id or base_id == DEFAULT_BASE:
        return {"id": DEFAULT_BASE, "builtin": True, "mean": list(IMAGENET_MEAN),
                "std": list(IMAGENET_STD), "input_size": 224, "arch": "resnet18"}
    for item in list_bases():
        if item["id"] == base_id:
            item["builtin"] = False
            return item
    logger.warning("基模不存在: %s（回退 %s）", base_id, DEFAULT_BASE)
    return {"id": DEFAULT_BASE, "builtin": True, "mean": list(IMAGENET_MEAN),
            "std": list(IMAGENET_STD), "input_size": 224, "arch": "resnet18"}


def mean_std(base_id: str):
    base = get_base(base_id)
    return (tuple(base.get("mean") or IMAGENET_MEAN), tuple(base.get("std") or IMAGENET_STD))


def _find_weights(folder: Path, desc: dict):
    for name in [desc.get("weights")] + list(desc.get("fallback_weights") or []):
        if name and (folder / name).exists():
            return folder / name
    for pattern in ("*.bin", "*.safetensors", "*.pth"):
        hits = sorted(folder.glob(pattern))
        if hits:
            return hits[0]
    return None


def _load_safetensors(path: Path) -> dict:
    """不依赖 safetensors 库：8 字节头长 + JSON 头 + 连续数据。"""
    import torch

    with open(path, "rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_len).decode("utf-8"))
        blob = f.read()
    out = {}
    for name, info in header.items():
        if name == "__metadata__":
            continue
        dtype = _SAFETENSORS_DTYPES.get(info.get("dtype"))
        if dtype is None:
            continue
        start, end = info["data_offsets"]
        tensor = torch.frombuffer(bytearray(blob[start:end]), dtype=getattr(torch, dtype))
        out[name] = tensor.reshape(info["shape"]).clone()
    return out


def load_base_state_dict(base_id: str) -> dict:
    """读取基模权重（已剔除 fc/head）；失败返回空 dict（调用方回退 ImageNet 预训练）。"""
    base = get_base(base_id)
    if base.get("builtin"):
        return {}
    folder = Path(base["dir"])
    desc = read_desc(folder)
    weights = _find_weights(folder, desc)
    if weights is None:
        logger.warning("基模 %s 无权重文件，回退 ImageNet 预训练", base_id)
        return {}

    import torch

    logger.info("载入基模权重: %s（%s）", base_id, weights.name)
    if weights.suffix == ".safetensors":
        state = _load_safetensors(weights)
    else:
        state = torch.load(str(weights), map_location="cpu", weights_only=False)
        for key in ("state_dict", "model", "model_state_dict"):
            if isinstance(state, dict) and isinstance(state.get(key), dict):
                state = state[key]
                break
    if not isinstance(state, dict):
        logger.warning("基模权重格式无法识别: %s", weights)
        return {}

    prefix = str(desc.get("state_dict_prefix") or "")
    drop = tuple(desc.get("drop_prefixes") or ("fc.", "head.", "classifier."))
    cleaned = {}
    for key, value in state.items():
        name = key[len(prefix):] if prefix and key.startswith(prefix) else key
        if any(name.startswith(p) for p in drop):
            continue
        if hasattr(value, "float"):
            value = value.float()          # 统一 fp32（有些仓库存 fp16）
        cleaned[name] = value
    logger.info("基模权重就绪: %d 个张量（已剔除 %s）", len(cleaned), ", ".join(map(str, drop)))
    return cleaned


def apply_base_to_model(model, base_id: str) -> dict:
    """把基模权重灌进（尚未插 CBAM / 换 fc 的）resnet18。"""
    state = load_base_state_dict(base_id)
    if not state:
        return {"applied": False, "reason": "no_weights"}
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        logger.warning("基模加载差异: 缺失 %d（如 %s）/ 多余 %d（如 %s）",
                       len(missing), ", ".join(list(missing)[:3]),
                       len(unexpected), ", ".join(list(unexpected)[:3]))
    logger.info("已用基模 %s 初始化 backbone（%d 个张量）", base_id, len(state))
    return {
        "applied": True,
        "loaded": len(state),
        "missing": len(missing),
        "unexpected": len(unexpected),
        # 带上名单便于精确判断（例如只缺 fc.* 属正常：基模类别数与本项目不同）
        "missing_keys": list(missing)[:10],
        "unexpected_keys": list(unexpected)[:10],
    }
