# -*- coding: utf-8 -*-
r"""Hugging Face 基模下载与探测：一条命令把外部基模装进 saves/models/pretrained/。

流程：snapshot_download（可走 hf-mirror）→ 探测 架构/权重文件/输入尺寸/mean·std →
生成 37ac-base.json（含可选 key_map 规则）→ 立刻可在"模型管理 → 训练基模"里选择。

依赖：huggingface_hub（只在**下载时**需要；训练/推理不需要）。
    .\.venv\Scripts\python.exe -m pip install -U huggingface_hub
国内网络：HF_ENDPOINT=https://hf-mirror.com（本模块默认开启镜像，可用 use_mirror=False 关闭）
"""

import json
import os
from pathlib import Path

from config.base import MODEL_DIR
from config.log_config import get_logger

logger = get_logger("hf_download")

PRETRAINED_DIR = Path(MODEL_DIR) / "pretrained"
DESC_NAME = "37ac-base.json"
MIRROR = "https://hf-mirror.com"
# torchvision 支持的架构（可被本项目直接构建）
SUPPORTED_ARCHS = ("resnet18", "efficientnet_b0", "efficientnet_b3")
DEFAULT_MEAN = [0.485, 0.456, 0.406]
DEFAULT_STD = [0.229, 0.224, 0.225]


def _read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _guess_arch(folder: Path) -> str:
    """从 config.json / 文件名 / 目录名猜架构。"""
    cfg = _read_json(folder / "config.json", {}) or {}
    for key in ("architecture", "architectures", "model_type", "arch"):
        val = cfg.get(key)
        if isinstance(val, list):
            val = val[0] if val else None
        if val:
            name = str(val).lower()
            for arch in SUPPORTED_ARCHS:
                if arch in name:
                    return arch
            if "efficientnet" in name and "b3" in name:
                return "efficientnet_b3"
            if "efficientnet" in name and "b0" in name:
                return "efficientnet_b0"
    low = folder.name.lower()
    for arch in SUPPORTED_ARCHS:
        if arch in low:
            return arch
    if "effb3" in low or "b3" in low:
        return "efficientnet_b3"
    if "effb0" in low or "b0" in low:
        return "efficientnet_b0"
    return "resnet18"


def _find_weights(folder: Path):
    for pattern in ("pytorch_model.bin", "model.pth", "*.bin", "model.safetensors", "*.safetensors", "*.pth"):
        hits = sorted(folder.glob(pattern))
        if hits:
            return hits[0].name
    return None


def detect_base_meta(folder: Path, arch: str = None) -> dict:
    """探测一个已下载目录：架构、权重文件、输入尺寸、mean/std、标签数。"""
    folder = Path(folder)
    cfg = _read_json(folder / "config.json", {}) or {}
    pc = cfg.get("pretrained_cfg") or {}
    pre = _read_json(folder / "preprocess.json", {}) or {}

    mean = pc.get("mean") or cfg.get("mean") or DEFAULT_MEAN
    std = pc.get("std") or cfg.get("std") or DEFAULT_STD
    input_size = pc.get("input_size") or cfg.get("input_size")
    if isinstance(input_size, (list, tuple)) and len(input_size) == 3:
        input_size = int(input_size[1])
    if not input_size:
        test = (pre.get("test") or [{}])[-1]
        input_size = test.get("size") if isinstance(test.get("size"), int) else 224

    return {
        "arch": arch or _guess_arch(folder),
        "weights": _find_weights(folder),
        "input_size": int(input_size or 224),
        "mean": [float(x) for x in mean],
        "std": [float(x) for x in std],
        "num_classes_pretrained": cfg.get("num_classes") or ((cfg.get("pretrained_cfg") or {}).get("num_classes")),
        "interpolation": pc.get("interpolation"),
    }


def write_base_desc(folder: Path, repo_id: str, meta: dict, key_map=None, drop_prefixes=None) -> dict:
    """写 37ac-base.json（不覆盖已存在的手工描述）。"""
    folder = Path(folder)
    desc = {
        "id": folder.name,
        "arch": meta.get("arch") or "resnet18",
        "source": repo_id,
        "weights": meta.get("weights"),
        "fallback_weights": ["model.safetensors"],
        "state_dict_prefix": "",
        "drop_prefixes": drop_prefixes or ["fc.", "classifier.", "head."],
        "input_size": meta.get("input_size") or 224,
        "mean": meta.get("mean") or DEFAULT_MEAN,
        "std": meta.get("std") or DEFAULT_STD,
        "num_classes_pretrained": meta.get("num_classes_pretrained"),
        "interpolation": meta.get("interpolation"),
        "license": "待确认（见仓库 README）",
        "note": "由 hf_download 自动探测生成；timm 命名与 torchvision 不一致时用 key_map 修正",
    }
    if key_map:
        desc["key_map"] = key_map
    path = folder / DESC_NAME
    if path.exists():
        logger.warning("已存在 %s，跳过描述生成（如需覆盖请先删除）", path)
        return _read_json(path, desc)
    path.write_text(json.dumps(desc, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已生成基模描述: %s（arch=%s, 输入 %s）", path, desc["arch"], desc["input_size"])
    return desc


def apply_endpoint(use_mirror: bool = True) -> str:
    """**在导入 huggingface_hub 之前**设置端点（镜像），并覆盖已导入模块的常量。"""
    if use_mirror:
        os.environ.setdefault("HF_ENDPOINT", MIRROR)
    endpoint = os.environ.get("HF_ENDPOINT") or MIRROR
    try:
        import huggingface_hub.constants as C

        C.HF_ENDPOINT = endpoint
        C.ENDPOINT = endpoint
        if hasattr(C, "HUGGINGFACE_CO_URL_TEMPLATE"):
            C.HUGGINGFACE_CO_URL_TEMPLATE = endpoint + "/{repo_id}/resolve/{revision}/{filename}"
    except Exception:
        pass
    return endpoint


def hf_import():
    """按需导入 huggingface_hub（缺失时给出安装命令）。"""
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        raise RuntimeError("未安装 huggingface_hub：py -m pip install -U huggingface_hub")
    return True


def login(token: str = None, use_mirror: bool = True, save_env: bool = True) -> dict:
    """登录 Hugging Face（受限/gated 仓库必需）；token 默认写入 .env 长期生效。"""
    hf_import()
    endpoint = apply_endpoint(use_mirror)
    token = (token or os.environ.get("HF_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("未提供 token：请到 https://huggingface.co/settings/tokens 生成后粘贴")

    from huggingface_hub import login as hf_login
    from huggingface_hub import whoami

    os.environ["HF_TOKEN"] = token
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    hf_login(token=token, add_to_git_credential=False)
    info = whoami(token=token) or {}
    name = info.get("name") or info.get("fullname") or "未知"
    logger.info("HF 登录成功: %s（端点 %s）", name, endpoint)
    if save_env:
        try:
            from services.menu_service import _write_env_value

            _write_env_value("HF_TOKEN", token)
            logger.info("token 已写入 .env（下次启动自动生效）")
        except Exception as e:
            logger.warning("写入 .env 失败: %s", e)
    return {"name": name, "endpoint": endpoint}


def download_base(repo_id: str, name: str = None, use_mirror: bool = True,
                  token: str = None, revision: str = None) -> dict:
    """下载 HF 仓库到 saves/models/pretrained/<短名>/ 并生成基模描述。"""
    if use_mirror or os.environ.get("HF_ENDPOINT"):
        logger.info("使用镜像: %s", apply_endpoint(use_mirror))
    if token:
        os.environ["HF_TOKEN"] = token
    hf_import()                     # 依赖检查
    apply_endpoint(use_mirror)      # 端点必须在导入 huggingface_hub 之前/同时生效
    from huggingface_hub import snapshot_download
    token = token or os.environ.get("HF_TOKEN") or None

    short = name or repo_id.split("/")[-1]
    target = PRETRAINED_DIR / short
    target.mkdir(parents=True, exist_ok=True)
    logger.info("开始下载 %s → %s", repo_id, target)
    try:
        path = snapshot_download(repo_id=repo_id, revision=revision, local_dir=str(target),
                                 local_dir_use_symlinks=False, token=token)
    except Exception as e:
        # 失败时清掉没下到权重的目录，避免"训练基模"列表出现 0MB 幽灵项
        if target.is_dir() and not any(target.rglob("*.bin")) and not any(target.rglob("*.safetensors")) and not any(target.rglob("*.pth")):
            import shutil

            shutil.rmtree(target, ignore_errors=True)
            logger.info("已清理未完成目录: %s", target)
        raise RuntimeError("下载失败: %s（端点 %s；受限仓库请先登录 HF）" % (e, os.environ.get("HF_ENDPOINT")))
    meta = detect_base_meta(Path(path))
    desc = write_base_desc(Path(path), repo_id, meta)
    logger.info("下载完成: %s（%s, %s）", short, desc["arch"], desc.get("weights"))
    return {"id": short, "dir": str(path), "meta": meta, "desc": desc}
