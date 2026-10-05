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


def test_evaluate_raw_moves_input_to_model_device(monkeypatch, tmp_path):
    """评估时必须把张量搬到模型所在设备，否则 DirectML/私有设备会报 type mismatch。"""
    from PIL import Image

    from services import eval_service

    dataset_root = tmp_path / "dataset" / "IP-1" / "role-1"
    dataset_root.mkdir(parents=True)
    image_path = dataset_root / "sample.jpg"
    Image.new("RGB", (8, 8), color="red").save(image_path)

    class DeviceGuardModel:
        device = torch.device("meta")

        def eval(self):
            return None

        def __call__(self, x):
            assert x.device == self.device, f"input device mismatch: {x.device} != {self.device}"
            return torch.tensor([[1.0]], device="cpu")

    model = DeviceGuardModel()

    def fake_classifier():
        return model, ["IP-1/role-1"], lambda im: torch.randn(3, 8, 8), torch

    monkeypatch.setattr(eval_service, "_classifier", fake_classifier)
    monkeypatch.setattr(eval_service, "DATASET_DIR", str(tmp_path / "dataset"))

    result = eval_service.evaluate(mode="raw", per_class=1, limit=1)
    assert result["total"] == 1
    assert result["top1"] == 1
