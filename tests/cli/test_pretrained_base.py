"""dbv4 基模：发现、加载、key 匹配（离线，不需要网络/safetensors 库）。"""

import torch
from torchvision.models import resnet18

from models import pretrained as P


def test_dbv4_base_is_discovered():
    bases = {b["id"]: b for b in P.list_bases()}
    assert "dbv4-resnet18" in bases, "saves/models/pretrained/dbv4-resnet18 应被识别"
    b = bases["dbv4-resnet18"]
    assert b["arch"] == "resnet18"
    assert b["weights"], "应找到权重文件"
    assert b["weights_mb"] > 50
    assert b["input_size"] == 384
    assert b["mean"] == [0.485, 0.456, 0.406]
    assert b["std"] == [0.229, 0.224, 0.225]


def test_base_weights_load_into_torchvision_resnet18():
    """基模 key 必须与 torchvision resnet18 对齐，且 fc 被剔除。"""
    state = P.load_base_state_dict("dbv4-resnet18")

    assert state, "基模权重读取失败"
    assert "conv1.weight" in state and "layer4.1.conv2.weight" in state
    assert not [k for k in state if k.startswith("fc.")], "fc 应被剔除（类别数不同）"

    model = resnet18(weights=None)
    result = P.apply_base_to_model(model, "dbv4-resnet18")

    assert result["applied"] is True
    # 只应缺 fc（基模是 12476 类，我们换自己的分类头）；其余 backbone 权重必须全部命中
    assert set(result["missing_keys"]) == {"fc.weight", "fc.bias"}, result["missing_keys"]
    assert result["unexpected"] == 0
    # 关键验证：模型里的 conv1 与基模完全一致（说明确实用基模初始化，而非随机）
    assert torch.allclose(model.conv1.weight.cpu(), state["conv1.weight"].float(), atol=0)
    assert torch.allclose(model.layer4[1].conv2.weight.cpu(), state["layer4.1.conv2.weight"].float(), atol=0)


def test_mean_std_follows_base():
    mean, std = P.mean_std("dbv4-resnet18")
    assert mean == (0.485, 0.456, 0.406) and std == (0.229, 0.224, 0.225)


def test_builtin_base_returns_empty_state():
    assert P.load_base_state_dict("imagenet-resnet18") == {}
    assert P.get_base("不存在的基模")["builtin"] is True     # 自动回退内置
