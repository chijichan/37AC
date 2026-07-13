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
        state_dict = torch.load(load_path, map_location=get_device())
        self.model = self._build_model(num_classes, self.pretrained)
        self.model.load_state_dict(state_dict)
        return self.model
