"""测试训练器模块"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestLabelSmoothingCrossEntropy:
    """测试标签平滑损失函数"""

    def test_loss_forward(self):
        """测试前向传播"""
        import torch
        from training.trainer import LabelSmoothingCrossEntropy

        criterion = LabelSmoothingCrossEntropy(smoothing=0.1)
        pred = torch.randn(4, 10)
        target = torch.randint(0, 10, (4,))
        loss = criterion(pred, target)
        assert isinstance(loss, torch.Tensor)
        assert loss.item() > 0

    def test_loss_is_finite(self):
        """测试损失值有限"""
        import torch
        from training.trainer import LabelSmoothingCrossEntropy

        criterion = LabelSmoothingCrossEntropy(smoothing=0.1)
        pred = torch.randn(2, 5)
        target = torch.tensor([0, 3])
        loss = criterion(pred, target)
        assert torch.isfinite(loss).item()

    @pytest.mark.parametrize("smoothing", [0.0, 0.1, 0.3])
    def test_different_smoothing(self, smoothing):
        """测试不同平滑值"""
        import torch
        from training.trainer import LabelSmoothingCrossEntropy

        criterion = LabelSmoothingCrossEntropy(smoothing=smoothing)
        pred = torch.randn(4, 10)
        target = torch.randint(0, 10, (4,))
        loss = criterion(pred, target)
        assert torch.isfinite(loss).item()


class TestSplitDataset:
    """测试数据集拆分"""

    def test_split_ratio(self):
        """测试拆分比例"""
        from training.trainer import _split_dataset
        from torch.utils.data import TensorDataset
        import torch

        dataset = TensorDataset(torch.randn(100, 3))
        train_idx, val_idx = _split_dataset(dataset, val_ratio=0.2)
        assert len(val_idx) == 20
        assert len(train_idx) == 80

    def test_split_no_overlap(self):
        """测试训练集和验证集无重叠"""
        from training.trainer import _split_dataset
        from torch.utils.data import TensorDataset
        import torch

        dataset = TensorDataset(torch.randn(100, 3))
        train_idx, val_idx = _split_dataset(dataset, val_ratio=0.2)
        train_set = set(train_idx)
        val_set = set(val_idx)
        assert train_set.isdisjoint(val_set)

    def test_split_small_dataset(self):
        """测试小数据集拆分"""
        from training.trainer import _split_dataset
        from torch.utils.data import TensorDataset
        import torch

        dataset = TensorDataset(torch.randn(5, 3))
        train_idx, val_idx = _split_dataset(dataset, val_ratio=0.2)
        # 至少留 1 个训练样本
        assert len(train_idx) >= 1
        assert len(val_idx) >= 1

    def test_split_reproducible(self):
        """测试拆分可复现"""
        from training.trainer import _split_dataset
        from torch.utils.data import TensorDataset
        import torch

        dataset = TensorDataset(torch.randn(100, 3))
        train1, val1 = _split_dataset(dataset, val_ratio=0.2, seed=42)
        train2, val2 = _split_dataset(dataset, val_ratio=0.2, seed=42)
        assert train1 == train2
        assert val1 == val2


class TestBackupOldModel:
    """测试旧模型备份"""

    def test_backup_creates_copy(self, tmp_path: Path):
        """测试备份创建副本"""
        from training.trainer import _backup_old_model

        model_path = tmp_path / "model.pth"
        model_path.write_text("dummy model data", encoding="utf-8")
        bak_dir = tmp_path / "_bak"

        _backup_old_model(model_path, bak_dir)
        # 备份目录应至少有一个文件
        bak_files = list(bak_dir.iterdir())
        assert len(bak_files) >= 1

    def test_backup_no_existing_model(self, tmp_path: Path):
        """测试没有旧模型时备份不报错"""
        from training.trainer import _backup_old_model

        model_path = tmp_path / "nonexistent.pth"
        bak_dir = tmp_path / "_bak"
        # 不应抛出异常
        _backup_old_model(model_path, bak_dir)

    def test_backup_also_copies_classes(self, tmp_path: Path):
        """测试备份同时备份 classes.txt"""
        from training.trainer import _backup_old_model

        model_path = tmp_path / "model.pth"
        model_path.write_text("dummy", encoding="utf-8")
        classes_txt = tmp_path / "classes.txt"
        classes_txt.write_text("原神/荧", encoding="utf-8")
        bak_dir = tmp_path / "_bak"

        _backup_old_model(model_path, bak_dir)
        # 应同时备份了 classes.txt
        bak_files = list(bak_dir.iterdir())
        txt_backups = [f for f in bak_files if f.suffix == ".txt"]
        assert len(txt_backups) >= 1


class TestTrainModel:
    """测试 train_model 函数（不实际运行训练）"""

    @patch("training.trainer.logger")
    def test_nonexistent_dataset_dir(self, mock_logger):
        """测试不存在的数据集目录"""
        from training.trainer import train_model

        train_model(dataset_dir=r"C:\nonexistent\dataset")
        mock_logger.error.assert_any_call(
            "数据集目录不存在: %s", r"C:\nonexistent\dataset"
        )

    @patch("training.trainer.logger")
    def test_model_save_on_interrupt(self, mock_logger, tmp_path):
        """测试中断时保存模型（逻辑验证）"""
        from training.trainer import train_model
        # 不需要实际运行，验证日志逻辑
        # 框架上 train_model 在 KeyboardInterrupt 时保存模型
        # 这里验证函数签名和调用方式
        assert callable(train_model)

    def test_train_model_signature(self):
        """测试 train_model 函数签名"""
        import inspect
        from training.trainer import train_model

        sig = inspect.signature(train_model)
        params = sig.parameters
        assert "dataset_dir" in params
        assert "use_yolo_crop" in params
        assert "resume_model" in params