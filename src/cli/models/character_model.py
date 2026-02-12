# models/character_model.py
import torch
import torch.nn as nn
from torchvision.models import resnet18
from config import *


class CharacterRecognitionModel:
    def __init__(self, num_classes):
        self.model = resnet18(weights=None)
        self.model.fc = nn.Linear(self.model.fc.in_features, num_classes)
        self.model = self.model.to(DEVICE)

    def get_model(self):
        return self.model

    def save_model(self, save_path):
        torch.save(self.model.state_dict(), save_path)

    def load_model(self, load_path, num_classes):
        self.model = resnet18(weights=None)
        self.model.fc = nn.Linear(self.model.fc.in_features, num_classes)
        state_dict = torch.load(load_path, map_location=DEVICE)
        self.model.load_state_dict(state_dict)
        self.model = self.model.to(DEVICE)
        return self.model
