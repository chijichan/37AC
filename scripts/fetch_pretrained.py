# -*- coding: utf-8 -*-
r"""下载动漫域基模并打印接入所需的诊断信息（在**能联网**的机器上运行）。

用法（在仓库根目录执行，即 C:\pj\37AC）：
    .\.venv\Scripts\python.exe scripts\fetch_pretrained.py animetimm/resnet18.dbv4-full
    # 国内网络：先 $env:HF_ENDPOINT = "https://hf-mirror.com"

它会：
  1. 下载整个仓库到 src/cli/saves/models/pretrained/<短名>/
  2. 列出文件清单与体积
  3. 读取权重，打印 state_dict 前 10 个 key、参数量、以及 config 里的 mean/std/输入尺寸
  4. 生成 meta.json 草稿（mean/std/input_size 需人工确认后填）
"""
import sys, json, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_ROOT = REPO_ROOT / "src" / "cli" / "saves" / "models" / "pretrained"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
local_only = "--local-only" in sys.argv          # 只诊断已存在的目录，不联网下载
repo_id = args[0] if args else "animetimm/resnet18.dbv4-full"
short = repo_id.split("/")[-1]
target = TARGET_ROOT / short
if local_only:
    print("[0/4] --local-only：跳过下载，仅诊断", target)

if local_only:
    if not target.is_dir():
        print("[x] 目录不存在: %s" % target)
        raise SystemExit(1)
    path = str(target)
else:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[x] 未安装 huggingface_hub：")
        print("    .\\.venv\\Scripts\\python.exe -m pip install -U huggingface_hub")
        print("    或：py -m pip install -U huggingface_hub")
        raise SystemExit(1)

    print("[1/4] 下载 %s → %s" % (repo_id, target))
    path = snapshot_download(repo_id=repo_id, local_dir=str(target), local_dir_use_symlinks=False)
    print("      完成:", path)

print("[2/4] 文件清单")
for p in sorted(Path(path).rglob("*")):
    if p.is_file():
        print("      %-46s %8.2f MB" % (p.relative_to(path), p.stat().st_size / 1024 / 1024))

print("[3/4] 权重诊断")
import torch
weights = None
for cand in sorted(Path(path).glob("*.pth")) + sorted(Path(path).glob("*.bin")):
    weights, _ = cand, print("      尝试:", cand.name)
    break
for cand in sorted(Path(path).glob("*.safetensors")):
    weights = cand
    break
if weights is None:
    print("      [x] 没找到 .pth/.bin/.safetensors")
else:
    if weights.suffix == ".safetensors":
        from safetensors.torch import load_file
        sd = load_file(str(weights))
    else:
        sd = torch.load(str(weights), map_location="cpu", weights_only=False)
        for key in ("state_dict", "model", "model_state_dict"):
            if isinstance(sd, dict) and key in sd and isinstance(sd[key], dict):
                sd = sd[key]
    print("      文件:", weights.name, "| 张量数:", len(sd))
    for i, k in enumerate(list(sd)[:10]):
        print("        %-52s %s" % (k, tuple(sd[k].shape) if hasattr(sd[k], "shape") else type(sd[k]).__name__))
    print("      参数量: %.1f M" % (sum(v.numel() for v in sd.values() if hasattr(v, "numel")) / 1e6))

print("[4/4] config / 预处理信息")
for name in ("config.json", "preprocessor_config.json", "README.md"):
    f = Path(path) / name
    if f.exists():
        if name.endswith(".md"):
            print("      %s: 存在（%d 字节，请人工确认 license）" % (name, f.stat().st_size))
            continue
        cfg = json.loads(f.read_text(encoding="utf-8"))
        keep = {k: cfg[k] for k in ("architecture", "architectures", "input_size", "mean", "std",
                                    "crop_size", "image_mean", "image_std", "num_classes",
                                    "model_type", "pretrained_cfg")
                if k in cfg}
        print("      %s: %s" % (name, json.dumps(keep, ensure_ascii=False)))

meta = {
    "id": short,
    "arch": "resnet18",
    "source": repo_id,
    "input_size": 224,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "state_dict_prefix": "",
    "weights": weights.name if weights else "",
    "license": "待确认",
    "note": "mean/std/input_size 以模型卡为准，确认后修改本文件",
}
meta_path = target / "meta.json"
if not meta_path.exists():
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("      已生成 meta.json 草稿:", meta_path)
print("\n把上面的清单与 key 前 10 行贴回对话，即可完成第 ③ 步（基模接入）。")
