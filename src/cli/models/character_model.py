# models/character_model.py
import torch
import torch.nn as nn
from torchvision.models import resnet18
from config.base import DEVICE


class CharacterRecognitionModel:
    """基于 ResNet18 的角色识别模型。"""

    def __init__(self, num_classes: int):
        self.model = self._build_model(num_classes)

    @staticmethod
    def _build_model(num_classes: int) -> nn.Module:
        """构建 ResNet18 模型并替换全连接层。"""
        model = resnet18(weights=None)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model.to(DEVICE)

    def get_model(self) -> nn.Module:
        return self.model

    def save_model(self, save_path: str) -> None:
        torch.save(self.model.state_dict(), save_path)

    def load_model(self, load_path: str, num_classes: int) -> nn.Module:
        state_dict = torch.load(load_path, map_location=DEVICE)
        self.model = self._build_model(num_classes)
        self.model.load_state_dict(state_dict)
        return self.model
