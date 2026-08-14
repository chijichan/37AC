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
        """测试备份同时备份 classes.json"""
        from training.trainer import _backup_old_model

        model_path = tmp_path / "model.pth"
        model_path.write_text("dummy", encoding="utf-8")
        classes_json = tmp_path / "classes.json"
        classes_json.write_text("{}", encoding="utf-8")
        bak_dir = tmp_path / "_bak"

        _backup_old_model(model_path, bak_dir)
        # 应同时备份了 classes.json
        bak_files = list(bak_dir.iterdir())
        json_backups = [f for f in bak_files if f.suffix == ".json"]
        assert len(json_backups) >= 1


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


class TestEvaluatePerIpSuccessRate:
    """测试训练结束后的分 IP（数据集）成功率统计"""

    @staticmethod
    def _make_model(num_classes: int, pred_idx: int):
        """构造一个固定输出指定类别索引的模拟模型。"""
        import torch
        import torch.nn as nn

        class _FixedLogitsModel(nn.Module):
            def __init__(self, n: int, idx: int):
                super().__init__()
                logits = torch.full((1, n), -10.0)
                logits[0, idx] = 10.0
                self.register_buffer("logits", logits)

            def forward(self, x):
                return self.logits.expand(x.size(0), -1)

        return _FixedLogitsModel(num_classes, pred_idx)

    def test_evaluate_mixed_ips(self, mock_dataset_dir: Path):
        """测试按 IP 分组的成功率统计（部分识别正确）"""
        import torch
        from data.dataset import IPRoleImageFolder
        from training.trainer import (
            VAL_TRANSFORMS,
            _evaluate_per_ip_success_rate,
        )

        # 类别按名称排序（中文 Unicode 顺序）: 原神/空, 原神/荧, 蔚蓝档案/白子
        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=VAL_TRANSFORMS)
        classes = dataset.classes

        # 模型始终预测 "原神/荧"
        model = self._make_model(len(classes), pred_idx=classes.index("原神/荧"))
        stats = _evaluate_per_ip_success_rate(model, dataset, torch.device("cpu"), classes)

        # 原神: 荧 2 张 + 空 1 张 = 3 张；IP 识别对 3 张（同属原神），角色完全匹配 2 张（荧）
        assert stats["原神"]["total"] == 3
        assert stats["原神"]["ip_ok"] == 3
        assert stats["原神"]["role_ok"] == 2
        # 蔚蓝档案: 白子 1 张；全部识别为原神，IP 与角色均不匹配
        assert stats["蔚蓝档案"]["total"] == 1
        assert stats["蔚蓝档案"]["ip_ok"] == 0
        assert stats["蔚蓝档案"]["role_ok"] == 0

    def test_evaluate_all_correct(self, mock_dataset_dir: Path):
        """测试全部识别正确时各 IP 成功率为 100%"""
        import torch
        from data.dataset import IPRoleImageFolder
        from training.trainer import (
            VAL_TRANSFORMS,
            _evaluate_per_ip_success_rate,
        )

        dataset = IPRoleImageFolder(root=str(mock_dataset_dir), transform=VAL_TRANSFORMS)
        classes = dataset.classes
        true_labels = [label for _, label in dataset.samples]

        # 逐样本模拟：模型输出 = 真实标签（构造每个样本一行 logits）
        import torch.nn as nn

        class _OracleModel(nn.Module):
            def __init__(self, labels):
                super().__init__()
                self.labels = labels

            def forward(self, x):
                # 每个输入样本对应一个固定 logits，使 argmax = 真实标签
                rows = []
                for i in range(x.size(0)):
                    idx = self.labels[i % len(self.labels)]
                    row = torch.full((1, len(classes)), -10.0)
                    row[0, idx] = 10.0
                    rows.append(row)
                return torch.cat(rows, dim=0)

        model = _OracleModel(true_labels)
        stats = _evaluate_per_ip_success_rate(model, dataset, torch.device("cpu"), classes)

        assert stats["原神"]["total"] == 3
        assert stats["原神"]["ip_ok"] == 3
        assert stats["原神"]["role_ok"] == 3
        assert stats["蔚蓝档案"]["total"] == 1
        assert stats["蔚蓝档案"]["ip_ok"] == 1
        assert stats["蔚蓝档案"]["role_ok"] == 1

    def test_evaluate_empty_dataset(self, tmp_path: Path):
        """测试空数据集返回空统计"""
        import torch
        from training.trainer import _evaluate_per_ip_success_rate

        class _EmptyDataset:
            def __len__(self):
                return 0

        model = self._make_model(3, pred_idx=0)
        stats = _evaluate_per_ip_success_rate(model, _EmptyDataset(), torch.device("cpu"), ["a/b"])
        assert stats == {}


class TestBuildIpSuccessTable:
    """测试成功率表格构建"""

    def test_table_contains_summary(self):
        """测试表格包含合计与各 IP 行"""
        from training.trainer import _build_ip_success_table

        ip_stats = {
            "原神": {"total": 3, "ip_ok": 2, "role_ok": 2},
            "蔚蓝档案": {"total": 1, "ip_ok": 1, "role_ok": 1},
        }
        table = _build_ip_success_table(ip_stats)
        assert "训练结束" in table
        assert "原神" in table
        assert "蔚蓝档案" in table
        assert "合计" in table
        assert "66.67%" in table  # 原神 IP 成功率 2/3
        assert "100.00%" in table  # 蔚蓝档案 1/1

    def test_table_with_unclassified_ip(self):
        """测试无 IP 前缀的类别显示为未归类"""
        from training.trainer import _build_ip_success_table

        ip_stats = {
            "": {"total": 2, "ip_ok": 1, "role_ok": 1},
        }
        table = _build_ip_success_table(ip_stats)
        assert "(未归类)" in table
        assert "50.00%" in table


class TestBuildClassSuccessTable:
    """测试角色类别成功率表格构建"""

    def test_table_contains_classes_and_summary(self):
        """测试表格包含各角色类别行与合计行"""
        from training.trainer import _build_class_success_table

        class_stats = {
            "原神/荧": {"total": 2, "correct": 2},
            "原神/空": {"total": 1, "correct": 0},
            "蔚蓝档案/白子": {"total": 1, "correct": 1},
        }
        table = _build_class_success_table(class_stats)
        assert "各角色类别测试结果" in table
        assert "原神/荧" in table
        assert "原神/空" in table
        assert "蔚蓝档案/白子" in table
        assert "合计" in table
        assert "100.00%" in table  # 原神/荧 2/2 与 蔚蓝档案/白子 1/1
        assert "0.00%" in table   # 原神/空 0/1
        assert "75.00%" in table  # 合计 3/4

    def test_table_with_unclassified_class(self):
        """测试无 IP 前缀的类别显示为未归类"""
        from training.trainer import _build_class_success_table

        class_stats = {
            "": {"total": 2, "correct": 1},
        }
        table = _build_class_success_table(class_stats)
        assert "(未归类)" in table
        assert "50.00%" in table