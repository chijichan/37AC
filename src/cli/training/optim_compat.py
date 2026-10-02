# -*- coding: utf-8 -*-
"""与 torch.optim.Adam 数值等价、但不使用 lerp 的优化器实现。

背景：DirectML（RX 580 等 AMD GPU）没有实现 aten::lerp.Scalar_out，
而 torch.optim.Adam 的更新式 exp_avg = beta1*exp_avg + (1-beta1)*grad 用的是 lerp，
于是**每一步**都回退到 CPU 并在 GPU/CPU 之间同步：
    UserWarning: The operator 'aten::lerp.Scalar_out' is not currently supported on the DML
    backend and will fall back to run on the CPU.
训练吞吐因此掉到 1~2 it/s。这里用 mul_ + add_ / addcmul_ 表达同样的数学，两个算子
DML 都有实现，同时每次 step 也不再打印那条警告。
"""

import math

import torch
from torch.optim.optimizer import Optimizer


class AdamNoLerp(Optimizer):
    """ADAM（同 torch.optim.Adam，含 bias correction 与 L2 weight_decay），不用 lerp。"""

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0):
        if lr is not None and lr < 0.0:
            raise ValueError("Invalid learning rate: {}".format(lr))
        if not 0.0 <= betas[0] < 1.0 or not 0.0 <= betas[1] < 1.0:
            raise ValueError("Invalid beta parameter: {}".format(betas))
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def _step_group_foreach(self, group):
        """用 foreach 批量更新一组参数；成功返回 True，不支持则返回 False（走逐参数实现）。"""
        params = [p for p in group["params"] if p.grad is not None]
        if not params:
            return True
        beta1, beta2 = group["betas"]
        lr, eps, weight_decay = group["lr"], group["eps"], group["weight_decay"]

        try:
            states = []
            for param in params:
                state = self.state[param]
                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg"] = torch.zeros_like(param)
                    state["exp_avg_sq"] = torch.zeros_like(param)
                states.append(state)

            # 所有参数的 step 必须一致（同一组内总是同时 step），否则不能用共享的偏差校正
            steps = [s["step"] + 1 for s in states]
            if len(set(steps)) != 1:
                return False
            step = steps[0]

            grads = []
            for param in params:
                grad = param.grad
                if weight_decay != 0:
                    grad = grad.add(param, alpha=weight_decay)
                grads.append(grad)

            exp_avgs = [s["exp_avg"] for s in states]
            exp_avg_sqs = [s["exp_avg_sq"] for s in states]

            torch._foreach_mul_(exp_avgs, beta1)
            torch._foreach_add_(exp_avgs, grads, alpha=1 - beta1)
            torch._foreach_mul_(exp_avg_sqs, beta2)
            torch._foreach_addcmul_(exp_avg_sqs, grads, grads, value=1 - beta2)

            bias_correction1 = 1 - beta1 ** step
            bias_correction2 = 1 - beta2 ** step
            step_size = lr / bias_correction1

            denoms = torch._foreach_sqrt(exp_avg_sqs)
            torch._foreach_div_(denoms, math.sqrt(bias_correction2))
            torch._foreach_add_(denoms, eps)
            torch._foreach_addcdiv_(params, exp_avgs, denoms, value=-step_size)

            for state in states:
                state["step"] += 1
            return True
        except Exception:
            # 该后端缺少某个 foreach 算子：本组回退逐参数实现（状态在下面按需初始化）
            return False

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            eps = group["eps"]
            lr = group["lr"]
            weight_decay = group["weight_decay"]

            # 优先走 foreach 批量路径：一次 dispatch 处理整组张量，
            # 显著减少 DML 上的 op 调度与 CPU 开销（逐参数循环约 700 次 dispatch/步）。
            # 任一步不支持（DML 缺某个 foreach 算子）就整体回退到逐参数实现。
            if self._step_group_foreach(group):
                continue

            for param in group["params"]:
                if param.grad is None:
                    continue
                grad = param.grad
                if grad.is_sparse:
                    raise RuntimeError("AdamNoLerp 不支持稀疏梯度")

                # L2 正则：与 torch.optim.Adam 一致，把 wd*p 加进梯度再算动量
                if weight_decay != 0:
                    grad = grad.add(param, alpha=weight_decay)

                state = self.state[param]
                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg"] = torch.zeros_like(param)
                    state["exp_avg_sq"] = torch.zeros_like(param)

                exp_avg, exp_avg_sq = state["exp_avg"], state["exp_avg_sq"]
                state["step"] += 1

                bias_correction1 = 1 - beta1 ** state["step"]
                bias_correction2 = 1 - beta2 ** state["step"]

                # 关键：用 mul_ + add_ / addcmul_ 代替 lerp（DML 支持这两个算子）
                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)
                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

                step_size = lr / bias_correction1
                denom = exp_avg_sq.sqrt().div_(math.sqrt(bias_correction2)).add_(eps)
                param.addcdiv_(exp_avg, denom, value=-step_size)

        return loss


def make_adam(params, lr, weight_decay=0.0, betas=(0.9, 0.999), eps=1e-8):
    """按设备选择 Adam：DirectML 用无 lerp 版本，其它用 torch 原生实现。"""
    device = None
    try:
        from config.base import get_device
        device = get_device()
    except Exception:
        device = None

    is_dml = False
    try:
        is_dml = "privateuseone" in str(device) or type(device).__name__ == "device" and \
            getattr(device, "type", "") == "privateuseone"
    except Exception:
        is_dml = False

    if is_dml:
        return AdamNoLerp(params, lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
    return torch.optim.Adam(params, lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
