"""测试数据集验证工具"""

from pathlib import Path

import pytest

from utils.validation_utils import validate_dataset_images


class TestValidateDatasetImages:
    """测试数据集图片验证"""

    def test_valid_dataset(self, mock_dataset_dir: Path):
        """测试有效数据集"""
        valid, total, classes, invalid = validate_dataset_images(str(mock_dataset_dir))
        assert valid == 4  # 荧 2 + 空 1 + 白子 1
        assert total == 4
        assert len(classes) == 3
        assert "原神/荧" in classes
        assert "原神/空" in classes
        assert "蔚蓝档案/白子" in classes
        assert invalid == []

    def test_nonexistent_dir(self):
        """测试不存在的目录"""
        valid, total, classes, invalid = validate_dataset_images(r"C:\nonexistent\dataset")
        assert valid == 0
        assert total == 0
        assert classes == []
        assert invalid == []

    def test_empty_dataset(self, tmp_path: Path):
        """测试空数据集目录"""
        empty_dir = tmp_path / "empty_dataset"
        empty_dir.mkdir()
        valid, total, classes, invalid = validate_dataset_images(str(empty_dir))
        assert valid == 0
        assert total == 0
        assert classes == []
        assert invalid == []

    def test_dataset_with_no_ip_dirs(self, tmp_path: Path):
        """测试没有 IP 目录的数据集"""
        ds = tmp_path / "no_ip"
        ds.mkdir()
        # 直接放图片在根目录（不符合 IP/角色 两级结构）
        from PIL import Image
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(str(ds / "direct.jpg"))
        valid, total, classes, invalid = validate_dataset_images(str(ds))
        assert valid == 0  # 不识别根目录图片
        assert total == 0
        assert classes == []

    def test_dataset_with_invalid_images(self, tmp_path: Path, corrupted_image: Path):
        """测试包含无效图片的数据集"""
        ds = tmp_path / "mixed_dataset"
        role_dir = ds / "原神" / "荧"
        role_dir.mkdir(parents=True)

        # 有效图片
        from PIL import Image
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(str(role_dir / "valid.jpg"))

        # 复制损坏图片
        import shutil
        shutil.copy(str(corrupted_image), str(role_dir / "bad.png"))

        valid, total, classes, invalid = validate_dataset_images(str(ds))
        assert valid == 1
        assert total == 2
        assert len(invalid) == 1

    def test_dataset_skips_non_image_files(self, mock_dataset_dir: Path):
        """测试跳过非图片文件"""
        # 在角色目录下放一个非图片文件
        role_dir = mock_dataset_dir / "原神" / "荧"
        txt_file = role_dir / "notes.txt"
        txt_file.write_text("这不是图片", encoding="utf-8")

        valid, total, classes, invalid = validate_dataset_images(str(mock_dataset_dir))
        # 总数应不变（非图片文件被跳过）
        assert valid == 4
        assert total == 4

    def test_dataset_with_hidden_dirs(self, tmp_path: Path):
        """测试跳过隐藏目录（以 . 开头）"""
        ds = tmp_path / "hidden"
        # 正常 IP 目录
        normal_dir = ds / "原神" / "荧"
        normal_dir.mkdir(parents=True)
        from PIL import Image
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(str(normal_dir / "test.jpg"))

        # 隐藏 IP 目录
        hidden_dir = ds / ".hidden_ip" / "角色"
        hidden_dir.mkdir(parents=True)
        img2 = Image.new("RGB", (100, 100), (0, 255, 0))
        img2.save(str(hidden_dir / "hidden.jpg"))

        valid, total, classes, invalid = validate_dataset_images(str(ds))
        # 隐藏目录应被跳过
        assert valid == 1
        assert total == 1
        assert classes == ["原神/荧"]