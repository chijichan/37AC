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

    def test_predict_character_llm_disabled_returns(self, capsys):
        """测试 LLM 未启用时 predict_character(llm) 直接返回并提示"""
        from unittest.mock import patch

        from prediction.predictor import predict_character

        with patch("prediction.predictor.LLM_RECOGNITION_ENABLED", False):
            predict_character(recognition_method="llm")
        captured = capsys.readouterr()
        assert "未启用" in captured.out


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
        """测试成功结果的显示（统一结构：最佳结果取自 class_probs[0]）"""
        from prediction.predictor import _display_prediction_result

        result = {
            "success": True,
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
        assert "原神/空" in captured.out

    def test_success_empty_class_probs(self, capsys):
        """测试成功但 class_probs 为空"""
        from prediction.predictor import _display_prediction_result

        result = {
            "success": True,
            "class_probs": [],
            "image_path": r"C:\test.jpg",
        }
        _display_prediction_result(result, r"C:\test.jpg")
        captured = capsys.readouterr()
        assert "未识别到角色" in captured.out

    def test_failure_result(self, capsys):
        """测试失败结果的显示"""
        from prediction.predictor import _display_prediction_result

        result = {
            "success": False,
            "error": "模型加载失败",
            "class_probs": [],
            "image_path": r"C:\test.jpg",
        }
        _display_prediction_result(result, r"C:\test.jpg")
        captured = capsys.readouterr()
        assert "模型加载失败" in captured.out


class TestLlmRecognition:
    """测试 LLM 识别相关函数"""

    def test_parse_llm_response_with_tags(self):
        """测试解析 features_used 与 tags"""
        from prediction.predictor import _parse_llm_response

        resp = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"label": "原神/荧", "confidence": 90, '
                            '"features_used": ["金发", "双辫"], '
                            '"tags": ["长发", "女性角色"]}'
                        )
                    }
                }
            ]
        }
        label, confidence, features_used, tags, class_probs = _parse_llm_response(resp)
        assert label == "原神/荧"
        assert confidence == 90.0
        assert features_used == ["金发", "双辫"]
        assert tags == ["长发", "女性角色"]
        assert class_probs == []

    def test_build_db_prompt_appends_character_db(self):
        """测试把角色数据库（特征/标签）附加到提示词"""
        from unittest.mock import patch

        from prediction.predictor import _build_db_prompt

        fake_data = {
            "原神/荧": {
                "id": "荧", "ip": "原神", "name_zh": "荧",
                "features_used": ["金发", "双辫"],
                "tags": ["长发", "女性角色"],
            },
        }
        with patch("utils.file_utils.load_classes_json_data", return_value=fake_data):
            prompt = _build_db_prompt("基础识别提示词")
        assert "基础识别提示词" in prompt
        assert "已知角色数据库" in prompt
        assert "原神/荧" in prompt
        assert "金发" in prompt
        assert "双辫" in prompt
        assert "女性角色" in prompt

    def test_build_db_prompt_empty_db_returns_base(self):
        """测试角色数据库为空时返回原提示词"""
        from unittest.mock import patch

        from prediction.predictor import _build_db_prompt

        with patch("utils.file_utils.load_classes_json_data", return_value={}):
            prompt = _build_db_prompt("基础识别提示词")
        assert prompt == "基础识别提示词"


class TestCrossComputeConfidence:
    """测试 LLM 交叉计算置信度"""

    def test_matching_profile_keeps_confidence(self):
        """测试特征/标签匹配时置信度基本保留"""
        from prediction.predictor import _cross_compute_confidence

        profiles = {
            "原神/荧": {
                "features_used": ["金发", "双辫"],
                "tags": ["长发", "女性角色"],
            },
        }
        conf, hit = _cross_compute_confidence(
            "原神/荧", 90.0,
            ["金发", "双辫"], ["长发", "女性角色"],
            profiles,
        )
        assert hit is True
        # 完全匹配 → 交叉后应接近原置信度（0.7*90 + 0.3*100 = 93）
        assert conf == 93.0

    def test_mismatching_profile_penalizes(self):
        """测试特征/标签不匹配时置信度被压低"""
        from prediction.predictor import _cross_compute_confidence

        profiles = {
            "原神/荧": {
                "features_used": ["金发", "双辫"],
                "tags": ["长发", "女性角色"],
            },
        }
        conf, hit = _cross_compute_confidence(
            "原神/荧", 95.0,
            ["红发", "短发"], ["短发", "男性角色"],
            profiles,
        )
        assert hit is True
        # 完全不匹配 → 封顶 45
        assert conf == 45.0

    def test_no_profile_keeps_confidence(self):
        """测试数据库无该角色档案时保持原置信度"""
        from prediction.predictor import _cross_compute_confidence

        conf, hit = _cross_compute_confidence(
            "原神/未知角色", 88.0, ["金发"], ["女性角色"], {}
        )
        assert hit is False
        assert conf == 88.0


class TestMergeLlmClassProbs:
    """测试 LLM 主结论与备选合并为 class_probs"""

    def test_merge_and_sort(self):
        """测试合并去重并按概率降序"""
        from prediction.predictor import _merge_llm_class_probs

        merged = _merge_llm_class_probs(
            "原神/荧", 90.0,
            [{"name": "原神/空", "prob": 70.0}, {"name": "蔚蓝档案/白子", "prob": 80.0}],
        )
        assert merged[0] == {"name": "原神/荧", "prob": 90.0}
        assert merged[1] == {"name": "蔚蓝档案/白子", "prob": 80.0}
        assert merged[2] == {"name": "原神/空", "prob": 70.0}
        # 去重：与主结论相同的备选被忽略
        merged2 = _merge_llm_class_probs("原神/荧", 90.0, [{"name": "原神/荧", "prob": 99.0}])
        assert len(merged2) == 1

    def test_merge_crossed_confidence(self):
        """测试交叉计算后的置信度参与排序"""
        from prediction.predictor import _merge_llm_class_probs

        # 主结论被交叉计算压低到 40 后，应排在备选之后
        merged = _merge_llm_class_probs(
            "原神/荧", 40.0,
            [{"name": "原神/空", "prob": 60.0}],
        )
        assert merged[0]["name"] == "原神/空"