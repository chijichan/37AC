"""测试预测器模块"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestPredictImage:
    """测试 predict_image 函数"""

    def test_image_not_found(self):
        """测试图片不存在"""
        from prediction.predictor import predict_image

        result = predict_image(r"C:\nonexistent\image.jpg")
        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_unsupported_format(self, tmp_path: Path):
        """测试不支持的格式"""
        from prediction.predictor import predict_image

        file = tmp_path / "test.bmp"
        file.write_text("dummy", encoding="utf-8")
        result = predict_image(str(file))
        assert result["success"] is False

    def test_corrupted_image(self, corrupted_image: Path):
        """测试损坏图片"""
        from prediction.predictor import predict_image

        result = predict_image(str(corrupted_image))
        assert result["success"] is False

    @patch("prediction.predictor.load_classes_from_file")
    @patch("prediction.predictor.check_model_file")
    def test_model_not_found(self, mock_check, mock_load, valid_png: Path):
        """测试模型文件不存在"""
        mock_load.return_value = ["原神/荧", "原神/空"]
        mock_check.return_value = False

        from prediction.predictor import predict_image

        result = predict_image(str(valid_png))
        assert result["success"] is False
        assert "不存在" in result["error"] or "不可读" in result["error"]

    @patch("prediction.predictor.load_classes_from_file")
    @patch("prediction.predictor.check_model_file")
    def test_classes_not_found(self, mock_check, mock_load, valid_png: Path):
        """测试类别文件不存在"""
        mock_load.return_value = []
        mock_check.return_value = True

        # 清空全局类别缓存，避免被前序测试污染（缓存命中会跳过 load 分支）
        import prediction.predictor as predictor_module
        predictor_module._classes_cache = None

        from prediction.predictor import predict_image

        result = predict_image(str(valid_png))
        assert result["success"] is False
        assert "类别" in result["error"]

    def test_predict_character_signature(self):
        """测试 predict_character 函数存在"""
        from prediction.predictor import predict_character
        assert callable(predict_character)


class TestPredictTransforms:
    """测试预测预处理变换"""

    def test_transform_application(self, valid_png: Path):
        """测试变换应用到图片"""
        from prediction.predictor import PREDICT_TRANSFORMS
        from PIL import Image
        import torch

        with Image.open(str(valid_png)) as img:
            img_rgb = img.convert("RGB")
            tensor = PREDICT_TRANSFORMS(img_rgb)

        assert isinstance(tensor, torch.Tensor)
        assert tensor.shape == (3, 224, 224)

    def test_normalization_values(self, valid_png: Path):
        """测试归一化值范围"""
        from prediction.predictor import PREDICT_TRANSFORMS
        from PIL import Image
        import torch

        with Image.open(str(valid_png)) as img:
            img_rgb = img.convert("RGB")
            tensor = PREDICT_TRANSFORMS(img_rgb)

        # 归一化后的值应在合理范围内
        assert tensor.min().item() >= -3.0
        assert tensor.max().item() <= 3.0


class TestDisplayPredictionResult:
    """测试显示预测结果"""

    def test_success_result(self, capsys):
        """测试成功结果的显示"""
        from prediction.predictor import _display_prediction_result

        result = {
            "success": True,
            "label": "原神/荧",
            "confidence": 95.5,
            "class_probs": [
                {"name": "原神/荧", "prob": 95.5},
                {"name": "原神/空", "prob": 3.2},
            ],
            "image_path": r"C:\test.jpg",
        }
        _display_prediction_result(result, r"C:\test.jpg")
        captured = capsys.readouterr()
        assert "原神/荧" in captured.out
        assert "95.50%" in captured.out

    def test_failure_result(self, capsys):
        """测试失败结果的显示"""
        from prediction.predictor import _display_prediction_result

        result = {
            "success": False,
            "error": "模型加载失败",
            "label": "",
            "confidence": 0.0,
            "class_probs": [],
            "image_path": r"C:\test.jpg",
        }
        _display_prediction_result(result, r"C:\test.jpg")
        captured = capsys.readouterr()
        assert "模型加载失败" in captured.out