# models/character_model.py
import torch
import torch.nn as nn
from torchvision.models import resnet18
from config.base import get_device


def _load_state_dict_any(load_path: str) -> dict:
    """加载权重字典，兼容历史文件。

    严格模式（weights_only=True）优先；失败时说明文件里带有非白名单 global ——
    典型是**在 DirectML 上直接保存**的旧权重（torch._utils._rebuild_device_tensor_from_numpy）。
    这种情况下依次尝试：
      1) 把该重建函数加入安全白名单后再用严格模式；
      2) 最后退回 weights_only=False（文件是自己训练产生的，可信），日志留痕。
    """
    import logging

    _logger = logging.getLogger(__name__)
    try:
        return torch.load(load_path, map_location="cpu", weights_only=True)
    except Exception as strict_error:
        _logger.warning(
            "严格加载失败（多为 DirectML 上保存的旧权重），改用兼容模式: %s",
            str(strict_error)[:200],
        )
        try:
            from torch.serialization import add_safe_globals
            import torch._utils as _torch_utils

            rebuild = getattr(_torch_utils, "_rebuild_device_tensor_from_numpy", None)
            if rebuild is not None:
                add_safe_globals([rebuild])
                return torch.load(load_path, map_location="cpu", weights_only=True)
        except Exception:
            pass
        return torch.load(load_path, map_location="cpu", weights_only=False)


# ==================== CBAM 注意力模块 ====================


class ChannelAttention(nn.Module):
    """通道注意力模块 — 关注"什么"特征更有意义"""

    def __init__(self, in_channels: int, reduction: int = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(in_channels, in_channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(in_channels // reduction, in_channels, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        avg_out = self.fc(self.avg_pool(x).view(b, c))
        # 手动全局最大池化（避免 AdaptiveMaxPool2d 在 DML 上回退到 CPU）
        max_pooled, _ = torch.max(x.view(b, c, -1), dim=2)
        max_out = self.fc(max_pooled)
        out = self.sigmoid(avg_out + max_out).view(b, c, 1, 1)
        return x * out


class SpatialAttention(nn.Module):
    """空间注意力模块 — 关注"哪里"是重要区域"""

    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        out = torch.cat([avg_out, max_out], dim=1)
        out = self.sigmoid(self.conv(out))
        return x * out


class CBAM(nn.Module):
    """卷积注意力模块 — 通道注意力 + 空间注意力串联"""

    def __init__(self, in_channels: int, reduction: int = 16):
        super().__init__()
        self.channel_attention = ChannelAttention(in_channels, reduction)
        self.spatial_attention = SpatialAttention()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


# ==================== 带注意力的 ResNet18 ====================


class CharacterRecognitionModel:
    """基于 ResNet18(ImageNet预训练) + CBAM 注意力的角色识别模型。"""

    def __init__(self, num_classes: int, pretrained: bool = True):
        self.pretrained = pretrained
        self.model = self._build_model(num_classes, pretrained)

    @staticmethod
    def _build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
        """构建 ResNet18 模型，每层后插入 CBAM 注意力，再替换全连接层。"""
        import logging

        from config.base import PRETRAINED_BASE

        _log = logging.getLogger(__name__)
        _log_warn = None
        try:
            from models.pretrained import get_base, is_builtin

            if not is_builtin(PRETRAINED_BASE):
                _info = get_base(PRETRAINED_BASE)
                if _info.get("builtin"):
                    # 指定的基模不存在/已丢失 → 回退内置 resnet18 + ImageNet 权重
                    _log_warn = "基模 %s 不可用（目录缺失或无权重），已回退 imagenet-resnet18" % PRETRAINED_BASE
                    use_base = False
                else:
                    use_base = bool(pretrained) and bool(_info.get("weights"))
                    if pretrained and not use_base:
                        _log_warn = "基模 %s 没有权重文件，已回退 ImageNet 预训练" % PRETRAINED_BASE
            else:
                use_base = False
        except Exception as e:
            use_base = bool(pretrained) and PRETRAINED_BASE not in ("", "imagenet-resnet18")
            _log_warn = "基模解析失败: %s" % e

        try:
            from models.pretrained import current_arch

            arch = current_arch()
        except Exception:
            arch = "resnet18"
        if _log_warn:
            _log.warning(_log_warn)

        # DML_ARCH_BLOCK: torch-directml 对 torchvision EfficientNet 算子覆盖不全，
        # 前向 conv2d 会抛 "unbox expects Dml at::Tensor as inputs"（实测 batch 88 才炸，
        # 白等一场）。这里在构建时就拦下并给出可行方案。
        if arch.startswith("efficientnet"):
            try:
                # 用别名导入：否则函数内的 get_device 会被当成局部变量，
                # 导致下面的 model.to(get_device()) 抛 UnboundLocalError
                from config.base import get_device as _resolve_device

                _dev = _resolve_device()
                _dev_type = getattr(_dev, "type", str(_dev))
            except Exception:
                _dev_type = "cpu"
            if _dev_type == "privateuseone":
                raise RuntimeError(
                    "架构 %s 无法在 DirectML 上运行（torch-directml 算子不完整，前向 conv2d 会断言失败）。"
                    "解决：① .env 设 PRETRAINED_BASE=dbv4-resnet18（或 imagenet-resnet18）用 ResNet 训练；"
                    "② 或改用 CPU 训练（.env: AUTO_DEVICE=False + DEVICE=cpu）。" % arch)

        # ---------- EfficientNet 分支（b0/b3）：无 CBAM，换 classifier 头 ----------
        if arch.startswith("efficientnet"):
            from torchvision.models import efficientnet_b0, efficientnet_b3

            factory = {"efficientnet_b0": efficientnet_b0, "efficientnet_b3": efficientnet_b3}.get(arch)
            if factory is None:
                _log.warning("未知架构 %s，回退 resnet18", arch)
                arch = "resnet18"
            else:
                # 内置基模：直接用 torchvision 的 ImageNet 权重（零下载 HF 权重）
                imagenet_weights = None if use_base else ("IMAGENET1K_V1" if pretrained else None)
                model = factory(weights=imagenet_weights)
                if use_base:
                    try:
                        from models.pretrained import apply_base_to_model

                        result = apply_base_to_model(model, PRETRAINED_BASE)
                        if not result.get("applied"):
                            _log.warning("基模 %s 未能应用（%s），backbone 为随机初始化",
                                         PRETRAINED_BASE, result.get("reason"))
                    except Exception as e:
                        _log.warning("基模 %s 加载失败: %s（回退随机初始化）", PRETRAINED_BASE, e)
                elif not pretrained:
                    _log.warning("架构 %s：pretrained=False，backbone 为随机初始化", arch)
                in_features = model.classifier[1].in_features
                model.classifier[1] = nn.Linear(in_features, num_classes)
                _log.info("已构建 %s（无 CBAM，%s）：%d 类，分类头 %d→%d", arch,
                          "ImageNet 预训练" if imagenet_weights else "随机初始化",
                          num_classes, in_features, num_classes)
                return model

        # ---------- ResNet18 分支（默认）：裸 resnet18 → 灌基模 → 插 CBAM → 换 fc ----------
        model = resnet18(weights=None if use_base else ("IMAGENET1K_V1" if pretrained else None))
        if use_base:
            try:
                from models.pretrained import apply_base_to_model

                result = apply_base_to_model(model, PRETRAINED_BASE)
                if not result.get("applied"):
                    _log.warning("基模 %s 未能应用（%s），本次使用随机初始化 backbone",
                                 PRETRAINED_BASE, result.get("reason"))
            except Exception as e:
                _log.warning("基模 %s 加载失败: %s（回退随机初始化）", PRETRAINED_BASE, e)

        # 在每个残差阶段后插入 CBAM 注意力
        model.layer1 = nn.Sequential(model.layer1, CBAM(64))    # 64 → 64
        model.layer2 = nn.Sequential(model.layer2, CBAM(128))   # 64 → 128
        model.layer3 = nn.Sequential(model.layer3, CBAM(256))   # 128 → 256
        model.layer4 = nn.Sequential(model.layer4, CBAM(512))   # 256 → 512

        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model.to(get_device())

    def freeze_backbone(self):
        """冻结 backbone（阶段1），仅训练分类头（+CBAM，若有）。

        resnet18：冻结 conv1/bn1/layer1-4；efficientnet_b0/b3：冻结 features.*
        """
        try:
            from models.pretrained import current_arch

            arch = current_arch()
        except Exception:
            arch = "resnet18"
        prefixes = ("features",) if arch.startswith("efficientnet") else (
            "conv1", "bn1", "layer1", "layer2", "layer3", "layer4")
        for name, param in self.model.named_parameters():
            param.requires_grad = not name.startswith(prefixes)

    def unfreeze_all(self):
        """解冻所有参数（阶段2）。"""
        for param in self.model.parameters():
            param.requires_grad = True

    # ---------- 架构无关分类头访问（resnet: fc；efficientnet: classifier[1]） ----------
    @staticmethod
    def _head_of(model):
        if model is None:
            return None
        if hasattr(model, "fc"):
            return model.fc
        if hasattr(model, "classifier") and len(model.classifier) > 1:
            return model.classifier[1]
        return None

    @staticmethod
    def _head_prefix(model) -> str:
        if model is not None and hasattr(model, "classifier") and not hasattr(model, "fc"):
            return "classifier.1."
        return "fc."

    def get_model(self) -> nn.Module:
        return self.model

    def save_model(self, save_path: str) -> None:
        """保存权重（**统一转到 CPU 再存**）。

        直接在 DirectML 上保存会把张量序列化成
        torch._utils._rebuild_device_tensor_from_numpy，导致：
        - 其它环境（CPU/CUDA）加载时依赖 torch-directml 的私有反序列化函数；
        - weights_only=True 的严格加载会直接拒绝该 global。
        转 CPU 后文件与设备无关，任何环境都能安全加载。
        """
        state_dict = self.model.state_dict()
        cpu_state = {
            key: (value.detach().cpu() if isinstance(value, torch.Tensor) else value)
            for key, value in state_dict.items()
        }
        torch.save(cpu_state, save_path)

    def load_model(self, load_path: str, num_classes: int) -> nn.Module:
        """加载模型权重，支持类别数变化的兼容性加载。

        1. 如果新旧类别数一致 → 直接全部加载（最快）
        2. 如果类别数变化 → 跳过 fc 层权重，只加载 backbone + CBAM，
           并重新初始化 fc 层（随机初始化新分类头）

        注意：如果 self.model 的 fc 层输出维度与 num_classes 一致，
        则复用已有模型结构避免重复构建；否则重建模型。

        Args:
            load_path (str): 权重文件路径
            num_classes (int): 新的类别数

        Returns:
            nn.Module: 加载权重后的模型
        """
        # 权重固定加载到 CPU：DirectML(privateuseone) 设备对象传给 torch.load 的 map_location，
        # 会被 torch_directml 的 device() 当成 device_id 解析并抛
        # TypeError: '>=' not supported between instances of 'torch.device' and 'int'。
        # 先加载到 CPU，再由下面的 load_state_dict 拷进模型所在设备（模型已 .to(get_device())）。
        state_dict = _load_state_dict_any(load_path)

        # 仅当模型未构建或类别数不匹配时才重建，避免重复构建
        _head = self._head_of(getattr(self, 'model', None))
        if not hasattr(self, 'model') or self.model is None \
                or _head is None or _head.out_features != num_classes:
            self.model = self._build_model(num_classes, self.pretrained)

        # 检查 fc 层权重尺寸是否匹配
        _hp = self._head_prefix(self.model)
        fc_key = _hp + "weight"
        if fc_key not in state_dict:                     # 兼容另一种架构/命名
            for _alt in ("classifier.1.weight", "fc.weight", "classifier.weight"):
                if _alt in state_dict:
                    _hp = _alt[: -len("weight")]
                    fc_key = _alt
                    break
        if fc_key in state_dict:
            old_num_classes = state_dict[fc_key].size(0)
            if old_num_classes != num_classes:
                # 类别数变化：移除 fc 相关键，随机初始化新 fc 层
                logger = __import__('logging').getLogger(__name__)
                logger.info("类别数变化: %d → %d，跳过 fc 层权重，保留 backbone + CBAM",
                            old_num_classes, num_classes)
                # 移除 fc 层的 weight 和 bias（如果有）
                keys_to_remove = [k for k in state_dict if k.startswith(_hp)]
                for k in keys_to_remove:
                    del state_dict[k]

                # 加载 backbone + CBAM，fc 层保持随机初始化
                self.model.load_state_dict(state_dict, strict=False)
            else:
                self.model.load_state_dict(state_dict)
        else:
            self.model.load_state_dict(state_dict, strict=False)

        return self.model
