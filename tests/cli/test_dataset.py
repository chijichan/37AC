"""测试数据集模块"""

from pathlib import Path

import pytest


class TestIPRoleImageFolder:
    """测试 IPRoleImageFolder 数据集"""

    def test_find_classes(self, mock_dataset_dir: Path):
        """测试 find_classes 返回正确的 IP/角色 格式"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        # 使用最小变换（避免加载 transformers 等）
        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=tf)

        classes = dataset.classes
        assert "原神/荧" in classes
        assert "原神/空" in classes
        assert "蔚蓝档案/白子" in classes
        assert len(classes) == 3

    def test_class_to_idx(self, mock_dataset_dir: Path):
        """测试类别到索引映射"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=tf)

        # 检查映射
        assert "原神/荧" in dataset.class_to_idx
        assert "原神/空" in dataset.class_to_idx
        assert "蔚蓝档案/白子" in dataset.class_to_idx

        # 索引应连续
        idxs = sorted(dataset.class_to_idx.values())
        assert idxs == list(range(len(classes := dataset.classes)))

    def test_dataset_length(self, mock_dataset_dir: Path):
        """测试数据集长度"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=tf)

        # 荧 2 + 空 1 + 白子 1 = 4
        assert len(dataset) == 4

    def test_getitem(self, mock_dataset_dir: Path):
        """测试获取单个样本"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=tf)

        img, label = dataset[0]
        # 应为 tensor 和 int
        import torch
        assert isinstance(img, torch.Tensor)
        assert isinstance(label, int)
        assert img.shape == (3, 224, 224)

    def test_samples_contain_correct_paths(self, mock_dataset_dir: Path):
        """测试样本路径正确"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=tf)

        # 检查所有样本路径
        for path, label in dataset.samples:
            assert path.startswith(str(mock_dataset_dir))
            # 标签应在有效范围内
            assert 0 <= label < len(dataset.classes)

    def test_skips_hidden_directories(self, tmp_path: Path):
        """测试跳过隐藏目录"""
        from data.dataset import IPRoleImageFolder
        from torchvision import transforms

        # 创建包含隐藏目录的数据集
        ds = tmp_path / "dataset"
        normal = ds / "原神" / "荧"
        normal.mkdir(parents=True)
        from PIL import Image
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(str(normal / "test.jpg"))

        hidden = ds / ".hidden" / "角色"
        hidden.mkdir(parents=True)
        img2 = Image.new("RGB", (100, 100), (0, 255, 0))
        img2.save(str(hidden / "test2.jpg"))

        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        dataset = IPRoleImageFolder(root=str(ds), transform=tf)
        # 隐藏目录应被跳过
        assert len(dataset.classes) == 1
        assert len(dataset) == 1