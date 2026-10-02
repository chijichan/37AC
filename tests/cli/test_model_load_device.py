"""权重加载必须走 CPU（DirectML 设备对象不能作为 map_location）。"""

import io
import uuid
from pathlib import Path

import pytest
import torch

from models.character_model import CharacterRecognitionModel


def test_load_model_uses_cpu_map_location(monkeypatch, tmp_path):
    captured = {}
    real_load = torch.load

    def fake_load(path, map_location=None, **kwargs):
        captured["map_location"] = map_location
        return {}          # 空 state_dict：只要不抛异常即可

    monkeypatch.setattr(torch, "load", fake_load)

    handler = CharacterRecognitionModel(2, pretrained=False)
    handler.load_model(str(tmp_path / "m.pth"), 2)

    assert captured["map_location"] == "cpu"      # 绝不能是 DML 设备对象


def test_load_model_accepts_real_state_dict(tmp_path):
    handler = CharacterRecognitionModel(2, pretrained=False)
    path = tmp_path / "m.pth"
    handler.save_model(str(path))

    loaded = CharacterRecognitionModel(2, pretrained=False).load_model(str(path), 2)
    assert loaded is not None
