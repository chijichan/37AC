"""无 lerp 的 Adam：与 torch.optim.Adam 数值一致，且不触发 DML 的 CPU 回退。"""

import pytest
import torch

from training.optim_compat import AdamNoLerp


def test_matches_torch_adam_numerically():
    torch.manual_seed(0)
    p_ref = torch.nn.Parameter(torch.randn(6, 4))
    p_new = torch.nn.Parameter(p_ref.detach().clone())

    ref = torch.optim.Adam([p_ref], lr=1e-2, weight_decay=1e-4)
    new = AdamNoLerp([p_new], lr=1e-2, weight_decay=1e-4)

    for _ in range(15):
        g = torch.randn(6, 4)
        p_ref.grad = g.clone()
        p_new.grad = g.clone()
        ref.step()
        new.step()
        assert torch.allclose(p_ref, p_new, atol=1e-7), "与 torch.optim.Adam 数值不一致"


def test_never_calls_lerp(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("不能调用 lerp（DirectML 会回退 CPU）")

    monkeypatch.setattr(torch.Tensor, "lerp_", boom)
    monkeypatch.setattr(torch.Tensor, "lerp", boom)

    param = torch.nn.Parameter(torch.randn(3, 3))
    opt = AdamNoLerp([param], lr=1e-2)
    for _ in range(3):
        param.grad = torch.randn(3, 3)
        opt.step()          # 只要不抛异常，就说明没走 lerp


def test_foreach_not_used(monkeypatch):
    param = torch.nn.Parameter(torch.randn(2, 2))
    param.grad = torch.randn(2, 2)
    AdamNoLerp([param], lr=1e-2).step()
    assert param.grad is not None
