# models/character_model.py
import torch
import torch.nn as nn
from torchvision.models import resnet18
from config.base import get_device


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
        weights = "IMAGENET1K_V1" if pretrained else None
        model = resnet18(weights=weights)

        # 在每个残差阶段后插入 CBAM 注意力
        model.layer1 = nn.Sequential(model.layer1, CBAM(64))    # 64 → 64
        model.layer2 = nn.Sequential(model.layer2, CBAM(128))   # 64 → 128
        model.layer3 = nn.Sequential(model.layer3, CBAM(256))   # 128 → 256
        model.layer4 = nn.Sequential(model.layer4, CBAM(512))   # 256 → 512

        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model.to(get_device())

    def freeze_backbone(self):
        """冻结 ResNet backbone，仅训练 FC + CBAM（阶段1）。"""
        for name, param in self.model.named_parameters():
            # 冻结 ResNet backbone
            if name.startswith(("conv1", "bn1", "layer1", "layer2", "layer3", "layer4")):
                param.requires_grad = False
            # CBAM 和 fc 保持可训练
            else:
                param.requires_grad = True

    def unfreeze_all(self):
        """解冻所有参数（阶段2）。"""
        for param in self.model.parameters():
            param.requires_grad = True

    def get_model(self) -> nn.Module:
        return self.model

    def save_model(self, save_path: str) -> None:
        torch.save(self.model.state_dict(), save_path)

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
        state_dict = torch.load(load_path, map_location=get_device())

        # 仅当模型未构建或类别数不匹配时才重建，避免重复构建
        if not hasattr(self, 'model') or self.model is None \
                or self.model.fc.out_features != num_classes:
            self.model = self._build_model(num_classes, self.pretrained)

        # 检查 fc 层权重尺寸是否匹配
        fc_key = "fc.weight"
        if fc_key in state_dict:
            old_num_classes = state_dict[fc_key].size(0)
            if old_num_classes != num_classes:
                # 类别数变化：移除 fc 相关键，随机初始化新 fc 层
                logger = __import__('logging').getLogger(__name__)
                logger.info("类别数变化: %d → %d，跳过 fc 层权重，保留 backbone + CBAM",
                            old_num_classes, num_classes)
                # 移除 fc 层的 weight 和 bias（如果有）
                keys_to_remove = [k for k in state_dict if k.startswith("fc.")]
                for k in keys_to_remove:
                    del state_dict[k]

                # 加载 backbone + CBAM，fc 层保持随机初始化
                self.model.load_state_dict(state_dict, strict=False)
            else:
                self.model.load_state_dict(state_dict)
        else:
            self.model.load_state_dict(state_dict, strict=False)

        return self.model
