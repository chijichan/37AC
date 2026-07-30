"""测试角色识别模型"""

import pytest


class TestCharacterRecognitionModel:
    """CharacterRecognitionModel 基础测试"""

    def test_model_creation(self):
        """测试模型创建（不加载预训练权重）"""
        from models.character_model import CharacterRecognitionModel
        model_handler = CharacterRecognitionModel(num_classes=10, pretrained=False)
        model = model_handler.get_model()
        assert model is not None
        # 检查最后一层输出维度
        assert model.fc.out_features == 10

    def test_model_with_different_classes(self):
        """测试不同类别数"""
        from models.character_model import CharacterRecognitionModel
        for n in [1, 5, 100]:
            model_handler = CharacterRecognitionModel(num_classes=n, pretrained=False)
            model = model_handler.get_model()
            assert model.fc.out_features == n

    def test_model_forward(self):
        """测试前向传播"""
        import torch
        from models.character_model import CharacterRecognitionModel
        model_handler = CharacterRecognitionModel(num_classes=5, pretrained=False)
        model = model_handler.get_model()
        model.eval()

        batch = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            output = model(batch)
        assert output.shape == (2, 5)

    def test_freeze_backbone(self):
        """测试冻结 backbone"""
        from models.character_model import CharacterRecognitionModel
        model_handler = CharacterRecognitionModel(num_classes=5, pretrained=False)
        model_handler.freeze_backbone()

        for name, param in model_handler.get_model().named_parameters():
            if name.startswith(("conv1", "bn1", "layer1", "layer2", "layer3", "layer4")):
                assert param.requires_grad is False, f"{name} 应被冻结"

    def test_unfreeze_all(self):
        """测试解冻所有参数"""
        from models.character_model import CharacterRecognitionModel
        model_handler = CharacterRecognitionModel(num_classes=5, pretrained=False)
        model_handler.freeze_backbone()
        model_handler.unfreeze_all()

        for param in model_handler.get_model().parameters():
            assert param.requires_grad is True

    def test_save_and_load_model(self, tmp_path):
        """测试模型保存与加载"""
        from models.character_model import CharacterRecognitionModel
        import torch

        # 保存模型
        handler1 = CharacterRecognitionModel(num_classes=5, pretrained=False)
        save_path = str(tmp_path / "test_model.pth")
        handler1.save_model(save_path)

        # 检查文件存在
        import os
        assert os.path.exists(save_path)

        # 加载模型（相同类别数）
        handler2 = CharacterRecognitionModel(num_classes=5, pretrained=False)
        loaded_model = handler2.load_model(save_path, num_classes=5)
        assert loaded_model is not None
        assert loaded_model.fc.out_features == 5

        # 验证权重已加载（比较 state_dict 的 key 子集）
        sd1 = torch.load(save_path, map_location="cpu")
        sd2 = handler2.get_model().state_dict()
        for key in sd1:
            if key in sd2:
                assert sd1[key].shape == sd2[key].shape, f"{key} 形状不一致"

    def test_load_model_different_classes(self, tmp_path):
        """测试加载不同类别数的模型（应跳过 fc 层）"""
        from models.character_model import CharacterRecognitionModel

        # 保存 5 类模型
        handler1 = CharacterRecognitionModel(num_classes=5, pretrained=False)
        save_path = str(tmp_path / "test_model.pth")
        handler1.save_model(save_path)

        # 加载为 10 类（类别数变化）
        handler2 = CharacterRecognitionModel(num_classes=10, pretrained=False)
        loaded_model = handler2.load_model(save_path, num_classes=10)
        assert loaded_model is not None
        # fc 层应为新的 10 类
        assert loaded_model.fc.out_features == 10

    def test_layer_structure(self):
        """测试 CBAM 层是否正确插入到各 layer 后"""
        from models.character_model import CharacterRecognitionModel

        model_handler = CharacterRecognitionModel(num_classes=5, pretrained=False)
        model = model_handler.get_model()

        # 检查每个 layer 后都有 CBAM
        assert hasattr(model.layer1, "_modules")
        # layer1 的最后一项应为 CBAM
        last_layer1 = list(model.layer1.named_children())[-1][1]
        assert "CBAM" in type(last_layer1).__name__

        last_layer2 = list(model.layer2.named_children())[-1][1]
        assert "CBAM" in type(last_layer2).__name__

        last_layer3 = list(model.layer3.named_children())[-1][1]
        assert "CBAM" in type(last_layer3).__name__

        last_layer4 = list(model.layer4.named_children())[-1][1]
        assert "CBAM" in type(last_layer4).__name__