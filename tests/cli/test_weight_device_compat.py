"""权重保存/加载的设备兼容性（DirectML 旧文件 + CPU 新文件）。"""

import torch

from models.character_model import CharacterRecognitionModel, _load_state_dict_any


def test_saved_weights_are_cpu_and_strict_loadable(tmp_path):
    """保存的文件必须能在 CPU 上被严格模式（weights_only=True）加载。"""
    path = tmp_path / "m.pth"
    CharacterRecognitionModel(3, pretrained=False).save_model(str(path))

    loaded = _load_state_dict_any(str(path))          # 严格模式直接过
    assert loaded, "加载出来是空的"
    assert all(not t.is_cuda for t in loaded.values() if isinstance(t, torch.Tensor))


def test_load_falls_back_for_legacy_dml_file(tmp_path, monkeypatch):
    """模拟旧文件：严格模式抛错时，应回退到兼容模式（而不是直接失败）。"""
    path = tmp_path / "legacy.pth"
    torch.save({"fc.weight": torch.zeros(2, 2)}, str(path))

    real_load = torch.load
    calls = []

    def fake_load(p, map_location=None, weights_only=True, **kwargs):
        calls.append(weights_only)
        if weights_only:
            raise RuntimeError("WeightsUnpickler error: Unsupported global")
        return real_load(p, map_location=map_location, weights_only=False)

    monkeypatch.setattr(torch, "load", fake_load)

    state = _load_state_dict_any(str(path))
    assert "fc.weight" in state
    assert False in calls and True in calls        # 先严格、后兼容


def test_load_model_roundtrip(tmp_path):
    path = tmp_path / "m.pth"
    CharacterRecognitionModel(4, pretrained=False).save_model(str(path))
    model = CharacterRecognitionModel(4, pretrained=False).load_model(str(path), 4)
    assert model is not None
