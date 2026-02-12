# prediction/predictor.py
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import os
from utils.image_utils import validate_image_file
from utils.file_utils import load_classes_from_file, check_model_file
from models.character_model import CharacterRecognitionModel
from config import *
import logging

logger = logging.getLogger(__name__)

# 数据预处理
PREDICT_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)

# 全局模型缓存，避免重复加载
_model_cache = None
_classes_cache = None


def predict_character():
    """交互式预测函数（保持原有功能）"""
    # --- 1. 加载类别 ---
    CLASS_NAMES = load_classes_from_file(CLASSES_TXT_PATH)
    if not CLASS_NAMES:
        return

    # --- 2. 加载模型 ---
    if not check_model_file(MODEL_LOAD_PATH):
        return

    try:
        model_handler = CharacterRecognitionModel(len(CLASS_NAMES))
        model = model_handler.load_model(MODEL_LOAD_PATH, len(CLASS_NAMES))
        model.eval()
        logger.info("模型加载成功")

    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}", exc_info=True)
        return

    # --- 3. 用户输入图片路径 ---
    while True:
        user_input = input("请输入你要预测的图片路径（或输入 0 返回主菜单）: ").strip()
        if user_input == "0":
            logger.info("好的，返回主菜单~")
            return
        if not user_input:
            logger.info("路径不能为空哦，再试一次吧~")
            continue
        if not os.path.exists(user_input):
            logger.info(f"找不到图片: {user_input}，请检查路径是否正确~")
            continue
        if not user_input.lower().endswith((".jpg", ".jpeg", ".png")):
            logger.info("请上传图片文件（如 .jpg / .png），当前格式可能不支持~")
            continue

        TEST_IMAGE_PATH = user_input

        # 验证图像文件
        if not validate_image_file(TEST_IMAGE_PATH):
            logger.info(f"图像文件可能已损坏或格式不正确: {TEST_IMAGE_PATH}")
            continue

        # 使用新的predict_image函数进行预测
        result = predict_image(TEST_IMAGE_PATH)
        _display_prediction_result(result, TEST_IMAGE_PATH)


def _display_prediction_result(result, image_path):
    """显示预测结果（内部辅助函数）"""
    if "success" == False:
        logger.error(f"预测失败: {result['error']}")
        return

    print(f"\n预测结果是: {result['label']}")
    print(f"置信度: {result['confidence']:.2f}%")
    print(f"图片路径: {image_path}")
    for item in result["class_probs"]:
        print(f"   → {item['name']}: {item['prob']:.1f}%")
    print()


# ======================
# 完善的 predict_image 函数
# ======================
def predict_image(image_path, model_path=None, classes_file=None, use_cache=True):
    """
    预测单张图片的角色（供其他代码调用）

    Args:
        image_path (str): 图片路径
        model_path (str, optional): 模型文件路径，默认使用配置中的路径
        classes_file (str, optional): 类别文件路径，默认使用配置中的路径
        use_cache (bool): 是否使用缓存的模型和类别，避免重复加载

    Returns:
        dict: 包含预测结果的字典，格式如下：
            {
                "success": bool,           # 是否成功
                "label": str,              # 预测标签
                "confidence": float,       # 置信度(0-100)
                "class_probs": list,       # 各类别概率列表 [{"name": str, "prob": float}]
                "image_path": str,         # 图片路径
                "error": str               # 错误信息（失败时）
            }
    """
    # 使用默认路径或传入的路径
    model_path = model_path or MODEL_LOAD_PATH
    classes_file = classes_file or CLASSES_TXT_PATH

    # 初始化结果字典
    result = {
        "success": False,
        "label": "",
        "confidence": 0.0,
        "class_probs": [],
        "image_path": image_path,
        "error": None,
    }

    try:
        # ======================
        # === 参数验证 ===
        # ======================
        if not os.path.exists(image_path):
            result["error"] = f"图片文件不存在: {image_path}"
            return result

        if not image_path.lower().endswith((".jpg", ".jpeg", ".png")):
            result["error"] = f"不支持的图片格式: {image_path}"
            return result

        if not validate_image_file(image_path):
            result["error"] = f"图像文件可能已损坏或格式不正确: {image_path}"
            return result

        # ======================
        # === 加载类别（带缓存） ===
        # ======================
        global _classes_cache
        if use_cache and _classes_cache is not None:
            CLASS_NAMES = _classes_cache
        else:
            CLASS_NAMES = load_classes_from_file(classes_file)
            if not CLASS_NAMES:
                result["error"] = "无法加载类别文件或类别文件为空"
                return result
            if use_cache:
                _classes_cache = CLASS_NAMES

        NUM_CLASSES = len(CLASS_NAMES)

        # ======================
        # === 加载模型（带缓存） ===
        # ======================
        global _model_cache
        if use_cache and _model_cache is not None:
            model = _model_cache
        else:
            if not check_model_file(model_path):
                result["error"] = f"模型文件不存在或不可读: {model_path}"
                return result

            try:
                model_handler = CharacterRecognitionModel(NUM_CLASSES)
                model = model_handler.load_model(model_path, NUM_CLASSES)
                model.eval()
                if use_cache:
                    _model_cache = model
            except Exception as e:
                result["error"] = f"模型加载失败: {str(e)}"
                logger.error(f"模型加载失败: {str(e)}", exc_info=True)
                return result

        # ======================
        # === 图像预处理和预测 ===
        # ======================
        transform = PREDICT_TRANSFORMS

        try:
            image = Image.open(image_path).convert("RGB")
            image_tensor = transform(image).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                outputs = model(image_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probs, 1)

                label = CLASS_NAMES[predicted_idx.item()]
                confidence_value = confidence.item() * 100

                # 构建各类别概率列表
                class_probs = [
                    {"name": CLASS_NAMES[i], "prob": round(prob.item() * 100, 2)}
                    for i, prob in enumerate(probs[0])
                ]

                # 成功返回结果
                result.update(
                    {
                        "success": True,
                        "label": label,
                        "confidence": round(confidence_value, 2),
                        "class_probs": class_probs,
                    }
                )

                logger.info(
                    f"预测成功: {image_path} -> {label} ({confidence_value:.2f}%)"
                )
                return result

        except Exception as e:
            result["error"] = f"图像处理或预测失败: {str(e)}"
            logger.error(f"预测过程中出现错误: {str(e)}", exc_info=True)
            return result

    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"
        logger.error(f"预测过程中出现未知错误: {str(e)}", exc_info=True)
        return result


# ======================
# 批量预测函数（额外功能）
# ======================
def predict_batch(image_paths, **kwargs):
    """
    批量预测多张图片

    Args:
        image_paths (list): 图片路径列表
        **kwargs: 传递给predict_image的参数

    Returns:
        list: 每张图片的预测结果列表
    """
    results = []
    for image_path in image_paths:
        result = predict_image(image_path, **kwargs)
        results.append(result)
    return results


# ======================
# 便捷函数（额外功能）
# ======================
def quick_predict(image_path):
    """
    快速预测，只返回标签和置信度

    Args:
        image_path (str): 图片路径

    Returns:
        tuple: (label, confidence) 或 (None, None) 如果失败
    """
    result = predict_image(image_path)
    if result["success"]:
        return result["label"], result["confidence"]
    else:
        return None, None
