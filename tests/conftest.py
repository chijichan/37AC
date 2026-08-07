"""pytest 全局配置与共享 fixtures

注意：CLI 与 Server 各自拥有独立的 `config` 包，不能在同一个
Python 进程中同时解析。因此 sys.path 注入按测试目录拆分：
- tests/cli/conftest.py    → 仅注入 src/cli + src（公共模块）
- tests/server/conftest.py → 仅注入 src/server + src（公共模块）

请分别运行 `pytest tests/cli` 与 `pytest tests/server`。
"""

import tempfile
from pathlib import Path

import pytest


# ── 测试用临时目录 fixture ──

@pytest.fixture
def tmp_model_dir(tmp_path: Path) -> Path:
    """返回一个临时模型目录，模拟 saves/models/"""
    d = tmp_path / "saves" / "models"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """返回一个临时日志目录，模拟 saves/logs/"""
    d = tmp_path / "saves" / "logs"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def tmp_upload_dir(tmp_path: Path) -> Path:
    """返回一个临时上传目录，模拟 saves/uploads/"""
    d = tmp_path / "saves" / "uploads"
    d.mkdir(parents=True)
    return d


# ── 临时图片文件 fixture ──

@pytest.fixture
def valid_png(tmp_path: Path) -> Path:
    """生成一张 1x1 有效 PNG 图片"""
    from PIL import Image
    path = tmp_path / "valid.png"
    img = Image.new("RGB", (224, 224), (255, 0, 0))
    img.save(path, "PNG")
    return path


@pytest.fixture
def valid_jpg(tmp_path: Path) -> Path:
    """生成一张 1x1 有效 JPEG 图片"""
    from PIL import Image
    path = tmp_path / "valid.jpg"
    img = Image.new("RGB", (224, 224), (0, 255, 0))
    img.save(path, "JPEG")
    return path


@pytest.fixture
def invalid_file(tmp_path: Path) -> Path:
    """生成一个非图片文件"""
    path = tmp_path / "not_image.txt"
    path.write_text("这不是一张图片", encoding="utf-8")
    return path


@pytest.fixture
def corrupted_image(tmp_path: Path) -> Path:
    """生成一个损坏的图片文件（头信息正确但内容错误）"""
    path = tmp_path / "corrupted.png"
    # PNG 魔数
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return path


# ── 临时类别文件 fixture ──

@pytest.fixture
def classes_file(tmp_path: Path) -> Path:
    """生成一个类别列表文件"""
    path = tmp_path / "classes.txt"
    path.write_text("原神/荧\n原神/空\n蔚蓝档案/白子\n", encoding="utf-8")
    return path


# ── 空类别文件 fixture ──

@pytest.fixture
def empty_classes_file(tmp_path: Path) -> Path:
    """生成一个空类别文件"""
    path = tmp_path / "empty_classes.txt"
    path.write_text("", encoding="utf-8")
    return path


# ── 模拟数据集目录（IP/角色 两级结构） fixture ──

@pytest.fixture
def mock_dataset_dir(tmp_path: Path) -> Path:
    """创建模拟数据集目录：
    dataset/
    ├── 原神/
    │   ├── 荧/       (2 张有效图片)
    │   └── 空/       (1 张有效图片)
    └── 蔚蓝档案/
        └── 白子/     (1 张有效图片)
    """
    from PIL import Image
    ds = tmp_path / "dataset"
    ip_roles = {
        "原神": ["荧", "空"],
        "蔚蓝档案": ["白子"],
    }
    for ip, roles in ip_roles.items():
        for role in roles:
            role_dir = ds / ip / role
            role_dir.mkdir(parents=True)
            # 每个角色生成 1-2 张有效图片
            n = 2 if role == "荧" else 1
            for i in range(n):
                img = Image.new("RGB", (224, 224), (255, 0, 0))
                img.save(str(role_dir / f"{role}_{i}.jpg"), "JPEG")
    return ds