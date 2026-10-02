"""YOLO 权重路径解析与裁剪预热（防止在 cwd 里下载、防止多线程并发下载卡死）。"""

import importlib
import os

from config import base as cfg
from detection import yolo_detector as YD


def _reload_with(value):
    if value is None:
        os.environ.pop("YOLO_MODEL_PATH", None)
    else:
        os.environ["YOLO_MODEL_PATH"] = value
    return importlib.reload(cfg)


def _restore():
    os.environ.pop("YOLO_MODEL_PATH", None)
    importlib.reload(cfg)


def test_empty_env_falls_back_to_model_dir():
    try:
        reloaded = _reload_with("")            # 关键：空值不能用裸文件名
        assert reloaded.YOLO_MODEL_PATH == reloaded.MODEL_DIR / "yolov8n.pt"
        assert reloaded.YOLO_MODEL_PATH.is_absolute()
    finally:
        _restore()


def test_relative_env_resolves_under_model_dir():
    try:
        reloaded = _reload_with("custom.pt")
        assert reloaded.YOLO_MODEL_PATH == reloaded.MODEL_DIR / "custom.pt"
    finally:
        _restore()


def test_absolute_env_kept(tmp_path):
    target = tmp_path / "abs.pt"
    try:
        reloaded = _reload_with(str(target))
        assert reloaded.YOLO_MODEL_PATH == target
    finally:
        _restore()


def test_default_env_points_at_existing_weights():
    assert cfg.YOLO_MODEL_PATH.is_absolute()
    assert os.path.exists(str(cfg.YOLO_MODEL_PATH)), "默认权重路径应指向已有文件"


def test_crop_dataset_aborts_when_weights_unavailable(monkeypatch, tmp_path):
    """权重不可用时：预热阶段就失败退出，不开线程池、不逐个角色重复报错。"""
    class Broken:
        load_error = "权重缺失"

        def _load_model(self):
            return False

    monkeypatch.setattr(YD, "check_yolo_available", lambda force=False: (True, ""))
    monkeypatch.setattr(YD, "_new_detector", lambda: Broken())

    stats = YD.crop_dataset(str(tmp_path), str(tmp_path / "out"), max_images_per_role=1)

    assert stats["processed"] == 0 and stats["failed"] == 0
    assert stats["interrupted"] is False
