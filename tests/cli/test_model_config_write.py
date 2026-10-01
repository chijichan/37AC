"""模型保存后 config.json 必须同步更新（节点同步靠 version + sha256 比对）。"""

import json
import re
from pathlib import Path

from training import trainer as T

TRAINER_SRC = Path(T.__file__).read_text(encoding="utf-8")


def test_every_model_save_updates_config():
    """每个 save_model(MODEL_PATH) 附近都必须调用 _write_model_config（防回归）。"""
    lines = TRAINER_SRC.splitlines()
    save_lines = [i for i, line in enumerate(lines) if "save_model(MODEL_PATH)" in line]
    assert save_lines, "没找到模型保存点，测试需要更新"

    missing = []
    for idx in save_lines:
        window = "\n".join(lines[idx: idx + 12])
        if "_write_model_config(" not in window:
            missing.append(idx + 1)
    assert not missing, "这些保存点没有同步写 config.json（行号）: %s" % missing


def test_training_end_writes_config_after_enrich():
    """训练收尾也要写一次，且必须在 LLM 补全（可能改 classes.json）之后。"""
    enrich_idx = TRAINER_SRC.index("_enrich_classes_with_llm_features(full_dataset, class_names)")
    tail = TRAINER_SRC[enrich_idx: enrich_idx + 600]
    assert "_write_model_config(" in tail


def test_write_model_config_records_version_and_hashes(tmp_path, monkeypatch):
    model = tmp_path / "m.pth"
    classes = tmp_path / "classes.json"
    info = tmp_path / "config.json"
    model.write_bytes(b"WEIGHTS-V1")
    classes.write_text('{"a": 1}', encoding="utf-8")

    monkeypatch.setattr(T, "MODEL_PATH", model)
    monkeypatch.setattr(T, "CLASSES_JSON_PATH", classes)
    monkeypatch.setattr(T, "MODEL_INFO_PATH", info)

    T._write_model_config("v1.0.0")
    first = json.loads(info.read_text(encoding="utf-8"))
    assert first["version"] == "v1.0.0"
    assert first["model"]["sha256"] == T._file_sha256(model)
    assert first["classes"]["sha256"] == T._file_sha256(classes)

    # 权重变了：重新写入后哈希必须跟着变（否则节点会以为没更新）
    model.write_bytes(b"WEIGHTS-V2")
    T._write_model_config("v1.0.1")
    second = json.loads(info.read_text(encoding="utf-8"))
    assert second["version"] == "v1.0.1"
    assert second["model"]["sha256"] != first["model"]["sha256"]
    assert second["model"]["sha256"] == T._file_sha256(model)
    assert second["trained_at"]
