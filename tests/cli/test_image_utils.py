"""测试图片工具模块"""

from pathlib import Path

import pytest

from utils.image_utils import validate_image_file


class TestValidateImageFile:
    """测试图片验证"""

    def test_valid_png(self, valid_png: Path):
        """测试有效 PNG 图片"""
        assert validate_image_file(str(valid_png)) is True

    def test_valid_jpg(self, valid_jpg: Path):
        """测试有效 JPEG 图片"""
        assert validate_image_file(str(valid_jpg)) is True

    def test_invalid_file(self, invalid_file: Path):
        """测试非图片文件"""
        assert validate_image_file(str(invalid_file)) is False

    def test_corrupted_image(self, corrupted_image: Path):
        """测试损坏的图片文件"""
        assert validate_image_file(str(corrupted_image)) is False

    def test_nonexistent_file(self):
        """测试不存在的文件"""
        assert validate_image_file(r"C:\nonexistent\image.png") is False

    def test_empty_file(self, tmp_path: Path):
        """测试空文件"""
        empty = tmp_path / "empty.jpg"
        empty.write_text("", encoding="utf-8")
        assert validate_image_file(str(empty)) is False

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png"])
    def test_valid_formats(self, ext, tmp_path: Path):
        """测试不同图片格式"""
        from PIL import Image
        path = tmp_path / f"test{ext}"
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        img.save(str(path))
        assert validate_image_file(str(path)) is True

    def test_zero_size_image(self, tmp_path: Path):
        """测试空文件/损坏图片"""
        path = tmp_path / "zero.jpg"
        # 0 字节文件（伪造的损坏图片）
        path.write_bytes(b"")
        result = validate_image_file(str(path))
        # 空文件应被判定为无效
        assert result is False

    def test_non_rgb_image(self, tmp_path: Path):
        """测试灰度图（应可转换为 RGB）"""
        from PIL import Image
        path = tmp_path / "grayscale.png"
        img = Image.new("L", (100, 100), 128)
        img.save(str(path))
        # 灰度图应能成功转为 RGB → 验证通过
        assert validate_image_file(str(path)) is True


def test_project_image_compression_uses_managed_temp_root(tmp_path: Path, monkeypatch):
    from PIL import Image
    from config import base as config
    import utils.image_utils as image_utils

    project_root = tmp_path / "37AC"
    cli_root = project_root / "src" / "cli"
    cli_root.mkdir(parents=True)
    source = project_root / "large.png"
    Image.new("RGB", (1200, 800), (128, 64, 32)).save(source)

    monkeypatch.setattr(config, "ROOT_PATH", cli_root)
    staged_paths = []
    original_temp_path = image_utils._compression_temp_path

    def capture_temp_path(file_path):
        path = original_temp_path(file_path)
        staged_paths.append(Path(path))
        return path

    monkeypatch.setattr(image_utils, "_compression_temp_path", capture_temp_path)

    assert image_utils.compress_image_file(str(source), max_size=512)
    assert staged_paths[0].parent == cli_root / "saves" / "tmp"
    assert not staged_paths[0].exists()
    assert not Path(f"{source}.37ac_tmp").exists()
    assert not list(project_root.glob("*.37ac_tmp"))
    with Image.open(source) as compressed:
        assert max(compressed.size) <= 512