# prediction/predictor.py
from PIL import Image
import os
import json
import random
import re
import shutil
import time
import threading
from common.constants import IMAGE_EXTENSIONS_BASIC
from common.recognition import parse_candidate_entry
from utils.image_utils import validate_image_file
from utils.file_utils import load_classes_from_file, load_classes_json_data, check_model_file
from config.base import (
    IMAGE_SIZE,
    CLASSES_JSON_PATH,
    MODEL_LOAD_PATH,
    YOLO_ENABLED,
    MULTI_CHARACTER_ENABLED,
    MAX_CHARACTERS,
    LLM_MULTI_CHARACTER,
    LLM_MAX_CHARACTERS,
    LLM_CROP_METHOD,
    LLM_CROP_MAX_SIDE,
    LLM_IMAGE_MAX_SIDE,
    LOCAL_RECOGNITION_ENABLED,
    LLM_RECOGNITION_ENABLED,
    LLM_DB_RECOGNITION,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_API_TYPE,
    LLM_MODEL_NAME,
    LLM_PROMPT_TEMPLATE,
    LLM_TIMEOUT_SEC,
    LLM_MAX_TOKEN,
    LLM_THINKING,
    LLM_MAX_FEATURES,
    LLM_MAX_TAGS,
    LLM_MAX_ATTEMPTS,
    LLM_RETRY_BASE_SEC,
    LLM_RETRY_MAX_SEC,
    LLM_MAX_TOTAL_SEC,
    get_device,
)
from config.log_config import get_logger
from detection.bbox import clamp_bbox, normalize_bbox, percent_bbox

logger = get_logger("predictor")

# YOLO 人物检测（可选）
try:
    from detection.yolo_detector import crop_best_character
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.debug("YOLO 检测模块不可用，使用全图分类")

# 多人物裁剪入口（yolo / mediapipe / auto，见 detection/cropper.py）
try:
    from detection.cropper import crop_characters_by_method, crop_quality_ok
    CROP_AVAILABLE = True
except ImportError:
    CROP_AVAILABLE = False
    crop_characters_by_method = None

    def crop_quality_ok(*args, **kwargs):
        """裁剪模块缺失时的兜底：不拦任何裁剪。"""
        return True

    logger.debug("裁剪模块不可用，使用整图分类")

# 数据预处理（惰性构建：torchvision 只在真正要推理时才 import）
# 说明：torch/torchvision 曾在本模块顶层 import，导致"只做 LLM 识别"的节点也常驻
# 175MB(torch) + 80MB(torchvision)。改成惰性后，空闲节点不再为本地模型买单。
_TRANSFORMS = None


def get_predict_transforms():
    """返回推理预处理 pipeline（首次调用时构建）。"""
    global _TRANSFORMS
    if _TRANSFORMS is None:
        from torchvision import transforms
        from config.base import apply_torch_thread_limit

        apply_torch_thread_limit()
        _TRANSFORMS = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
    return _TRANSFORMS


def __getattr__(name):
    """PEP 562：保留 PREDICT_TRANSFORMS 这个历史名字（按需构建）。"""
    if name == "PREDICT_TRANSFORMS":
        return get_predict_transforms()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# 全局模型缓存，避免重复加载
# 缓存结构：{ "model": nn.Module, "num_classes": int, "classes": list }
_model_cache = None
_classes_cache = None
_registry_cache = None
_cache_lock = threading.Lock()


def invalidate_model_cache():
    """清空模型/类别/注册表缓存（节点下载新模型后调用）。"""
    global _model_cache, _classes_cache, _registry_cache
    with _cache_lock:
        _model_cache = None
        _classes_cache = None
        _registry_cache = None


def _load_class_registry() -> dict:
    """加载 classes.json 角色注册表（{类别键: 类别对象}），带进程内缓存。

    类别名 = 整个对象："IP/角色" 仅作为唯一标识（路径参考/模型索引），
    完整类别定义（id/ip/name_zh/features_used/tags）来自 classes.json。
    """
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = load_classes_json_data(str(CLASSES_JSON_PATH))
    return _registry_cache


def _enrich_probs_with_metadata(class_probs):
    """从 classes.json 注册表为 class_probs 各项附加完整类别对象元数据。

    使识别结果中的每个类别项携带整个对象：
    {name, prob, name_zh, ip, features_used, tags}。
    注册表缺失 / 无该类别时保持原样。
    """
    if not class_probs:
        return class_probs
    try:
        registry = _load_class_registry()
    except Exception:
        return class_probs
    if not registry:
        return class_probs
    for item in class_probs:
        name = item.get("name")
        meta = registry.get(name)
        if not meta or not isinstance(meta, dict):
            continue
        item.setdefault("name_zh", meta.get("name_zh") or meta.get("id") or name)
        item.setdefault("ip", meta.get("ip") or "")
        item.setdefault("features_used", list(meta.get("features_used") or []))
        item.setdefault("tags", list(meta.get("tags") or []))
    return class_probs


def _default_classes_file() -> str:
    """返回默认类别文件路径（classes.json）。"""
    return str(CLASSES_JSON_PATH)


def predict_character(recognition_method: str = "local", image_path: str = None):
    """交互式预测函数

    Args:
        recognition_method: 识别方式
            - "local"：使用本地 37ac ResNet 模型（默认）
            - "llm"：使用第三方多模态大模型 API（需 LLM_RECOGNITION_ENABLED=true）
        image_path: 非空时直接识别该单张图片后返回（命令行 --image 模式），
            否则进入交互循环由用户输入图片路径
    """
    # --- 1. 按识别方式加载前置依赖 ---
    if recognition_method == "llm":
        if not LLM_RECOGNITION_ENABLED:
            logger.warning("LLM 识别未启用（LLM_RECOGNITION_ENABLED=False），请先在 .env 中开启")
            print("\nLLM 识别未启用，请在 .env 中设置 LLM_RECOGNITION_ENABLED=true")
            return
        logger.info("识别方式: LLM 大模型")
    else:
        # 本地模型：加载类别 + 验证模型文件存在
        CLASS_NAMES = load_classes_from_file(_default_classes_file())
        if not CLASS_NAMES:
            return

        if not check_model_file(MODEL_LOAD_PATH):
            return
        logger.info("识别方式: 本地模型")

    # --- 2. 用户输入图片路径 ---
    single_shot = image_path is not None
    while True:
        if single_shot:
            user_input = image_path
        else:
            from utils.cli_input import GoBack, read_line

            try:
                user_input = read_line(
                    "请输入你要预测的图片路径（ESC/Ctrl+Z 返回上级，0 返回主菜单）: "
                ).strip("\"'")
            except GoBack:
                print()
                logger.info("好的，返回主菜单~")
                return
        if user_input == "0" or user_input == "":
            logger.info("好的，返回主菜单~")
            return
        if not user_input:
            logger.info("路径不能为空哦，再试一次吧~")
            continue
        if not os.path.exists(user_input):
            logger.info("找不到图片: %s，请检查路径是否正确~", user_input)
            continue
        if not user_input.lower().endswith(IMAGE_EXTENSIONS_BASIC):
            logger.info("请上传图片文件（如 .jpg / .png），当前格式可能不支持~")
            continue

        TEST_IMAGE_PATH = user_input

        # 验证图像文件
        if not validate_image_file(TEST_IMAGE_PATH):
            logger.info("图像文件可能已损坏或格式不正确: %s", TEST_IMAGE_PATH)
            continue

        # 按识别方式调用对应引擎
        if recognition_method == "llm":
            result = predict_image_llm(TEST_IMAGE_PATH)
        else:
            result = predict_image(TEST_IMAGE_PATH)
        _display_prediction_result(result, TEST_IMAGE_PATH)

        # 命令行 --image 单张模式：识别完即返回
        if single_shot:
            return


def _display_prediction_result(result, image_path):
    """显示预测结果（内部辅助函数）

    统一结构：只依赖 result["class_probs"]（按概率降序，第一项即最佳结果），
    不再使用顶层 label / confidence 字段。
    """
    if not result.get("success"):
        error_msg = result.get("error", "未知错误")
        logger.error("预测失败: %s", error_msg)
        print(f"\n预测失败: {error_msg}")
        return

    probs = result.get("class_probs") or []
    if not probs:
        print("\n未识别到角色")
        return

    top = probs[0]
    print(f"\n预测结果是: {top['name']}")
    print(f"置信度: {top['prob']:.2f}%")
    # 类别名 = 整个对象：最佳类别携带完整对象（name_zh/ip/features_used/tags）
    name_zh = top.get("name_zh")
    if name_zh and name_zh != top["name"]:
        print(f"中文名: {name_zh}")
    feats = top.get("features_used") or []
    if feats:
        print(f"特征: {'、'.join(feats)}")
    tags = top.get("tags") or []
    if tags:
        print(f"标签: {'、'.join(tags)}")
    print(f"图片路径: {image_path}")
    for item in probs[1:]:
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
                "class_probs": list,       # 各类别概率列表（按概率降序，[{"name", "prob"}]，第一项即最佳结果）
                "features_used": list,     # 可解释文本特征（本地模型为空）
                "image_path": str,         # 图片路径
                "error": str               # 错误信息（失败时）
            }
        不再返回顶层 label / confidence 字段，最佳结果统一取 class_probs[0]。
    """
    # 使用默认路径或传入的路径
    model_path = model_path or MODEL_LOAD_PATH
    classes_file = classes_file or _default_classes_file()

    # 初始化结果字典
    result = {
        "success": False,
        "class_probs": [],
        "image_path": image_path,
        "error": None,
        # 多人物结果（需求1）：无人物时为空数组，crop_method 说明用了哪条裁剪路径
        "characters": [],
        "crop_method": "full",
    }

    try:
        # ======================
        # === 参数验证 ===
        # ======================
        if not os.path.exists(image_path):
            result["error"] = f"图片文件不存在: {image_path}"
            return result

        if not image_path.lower().endswith(IMAGE_EXTENSIONS_BASIC):
            result["error"] = f"不支持的图片格式: {image_path}"
            return result

        if not validate_image_file(image_path):
            result["error"] = f"图像文件可能已损坏或格式不正确: {image_path}"
            return result

        # ======================
        # === YOLO 快速定位（可选）===
        # ======================
        # 优先使用 YOLO 检测并裁剪人物区域，提高识别精度
        effective_image = image_path
        yolo_info = None
        if YOLO_ENABLED and YOLO_AVAILABLE:
            try:
                crop_path, det_info = crop_best_character(image_path)
                if crop_path and os.path.exists(crop_path):
                    # 质量门控：COCO 检测器在二次元图上常误检/多检，裁错的框会拉低准确率
                    # （实测：不裁剪 79.0% vs 直接裁剪 71.3%）——不达标就回退整图
                    if crop_quality_ok(crop_path, image_path, (det_info or {}).get("confidence")):
                        effective_image = crop_path
                        yolo_info = det_info
                        logger.info(
                            "YOLO 定位到角色区域: %s, 类别=%s, 置信度=%.2f",
                            det_info["bbox"] if det_info else "N/A",
                            det_info["class_name"] if det_info else "N/A",
                            det_info["confidence"] if det_info else 0,
                        )
                    else:
                        logger.info("裁剪质量不达标（置信度/面积占比），改用整图分类")
                else:
                    logger.info("YOLO 未检测到角色区域，使用全图分类")
            except Exception as e:
                logger.warning("YOLO 检测异常（降级到全图分类）: %s", e)
        elif not YOLO_AVAILABLE:
            logger.debug("YOLO 模块未安装，使用全图分类")

        # ======================
        # === 加载类别（带缓存） ===
        # ======================
        global _classes_cache
        with _cache_lock:
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
        # torch / torchvision / 模型定义都改为按需加载：
        # 只做 LLM 识别的节点永远不会走到这里，也就不会为本地模型付出 255MB 常驻内存
        import torch
        from models.character_model import CharacterRecognitionModel

        global _model_cache
        model = None

        with _cache_lock:
            # 尝试从缓存获取
            if use_cache and _model_cache is not None:
                cached_model, cached_num_classes = _model_cache
                if cached_num_classes == NUM_CLASSES:
                    model = cached_model
                else:
                    logger.info("模型类别数变化 (%d → %d)，重新加载模型", cached_num_classes, NUM_CLASSES)
                    _model_cache = None

        # 缓存未命中时加载模型
        if model is None:
            if not check_model_file(model_path):
                result["error"] = f"模型文件不存在或不可读: {model_path}"
                return result

            try:
                model_handler = CharacterRecognitionModel(NUM_CLASSES)
                model = model_handler.load_model(model_path, NUM_CLASSES)
                model.eval()
            except Exception as e:
                result["error"] = f"模型加载失败: {str(e)}"
                logger.error("模型加载失败: %s", e, exc_info=True)
                return result

        if use_cache:
            with _cache_lock:
                _model_cache = (model, NUM_CLASSES)

        # ======================
        # === 图像预处理和预测 ===
        # ======================
        transform = get_predict_transforms()

        def _classify(path):
            """对单张图（裁剪图或原图）做一次分类，返回 class_probs（已附加元数据）。"""
            with Image.open(path) as img:
                image = img.convert("RGB")
            image_tensor = transform(image).unsqueeze(0).to(get_device())
            with torch.no_grad():
                outputs = model(image_tensor)
                probs = torch.softmax(outputs, dim=1)
                # 构建各类别概率列表，按概率降序排列，只保留前10个
                sorted_probs = sorted(
                    [
                        {"name": CLASS_NAMES[i], "prob": round(prob.item() * 100, 2)}
                        for i, prob in enumerate(probs[0])
                    ],
                    key=lambda x: x["prob"],
                    reverse=True,
                )
            class_probs = [p for p in sorted_probs if p["prob"] > 0][:10]
            _enrich_probs_with_metadata(class_probs)
            return class_probs

        try:
            # ======================
            # === 多人物识别（需求1）===
            # ======================
            # 一张图里可能有多个角色：逐个人物裁剪 + 逐个识别，
            # 返回 characters[]（含原图百分比坐标）；顶层 class_probs 取置信度最高的人物
            if MULTI_CHARACTER_ENABLED and CROP_AVAILABLE:
                found = None
                try:
                    # auto: YOLO 优先，未命中回落 mediapipe，再没有则是整图
                    found = crop_characters_by_method(image_path)
                    crops = found.get("characters") or []
                    characters = []
                    for item in crops:
                        try:
                            probs = _classify(item["crop_path"])
                        except Exception as e:
                            logger.warning("第 %s 个人物识别失败: %s", item.get("index"), e)
                            continue
                        if not probs:
                            continue
                        characters.append({
                            "index": item["index"],
                            "bbox": item.get("bbox_norm"),
                            "bbox_percent": item.get("bbox_percent"),
                            "detector_confidence": item.get("detector_confidence"),
                            "confidence": probs[0]["prob"],
                            "class_probs": probs,
                        })

                    if characters:
                        best = max(characters, key=lambda c: c["confidence"] or 0)
                        _attach_yolo_note(result)
                        result.update({
                            "success": True,
                            "class_probs": best["class_probs"],   # 兼容旧客户端：顶层=最佳人物
                            "features_used": [],
                            "characters": characters,
                            "character_count": len(characters),
                            "crop_method": found.get("crop_method") or "yolo",
                            "image": {
                                "width": found["image_size"][0],
                                "height": found["image_size"][1],
                            },
                            "yolo_detected": True,
                        })
                        logger.info(
                            "多人物识别: %s -> %d 个人物，最佳 %s (%.2f%%)",
                            image_path, len(characters),
                            best["class_probs"][0]["name"], best["confidence"],
                        )
                        return result
                    logger.info("多人物检测未命中，回退单品/整图分类")
                except Exception as e:
                    logger.warning("多人物识别异常（回退单品/整图分类）: %s", e)
                finally:
                    if isinstance(found, dict) and found.get("tmp_dir"):
                        shutil.rmtree(found["tmp_dir"], ignore_errors=True)

            # ======================
            # === 单品分类（原有路径） ===
            # ======================
            class_probs = _classify(effective_image)
            if not class_probs:
                result["error"] = "图像处理或预测失败: 分类结果为空"
                return result
            with Image.open(image_path) as raw_img:
                original_size = raw_img.size
            _attach_yolo_note(result)
            result.update(
                {
                    "success": True,
                    "class_probs": class_probs,
                    "features_used": [],  # 本地模型无可解释文本特征，留空
                    "characters": [],
                    "crop_method": "yolo" if yolo_info else "full",
                    "image": {"width": original_size[0], "height": original_size[1]},
                    "yolo_detected": yolo_info is not None,
                }
            )

            logger.info(
                "预测成功: %s -> %s (%.2f%%)%s",
                image_path, class_probs[0]["name"], class_probs[0]["prob"],
                " [YOLO定位]" if yolo_info else "",
            )
            return result

        except Exception as e:
            result["error"] = f"图像处理或预测失败: {str(e)}"
            logger.error("预测过程中出现错误: %s", e, exc_info=True)
            return result

    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"
        logger.error("预测过程中出现未知错误: %s", e, exc_info=True)
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
    快速预测，只返回标签和置信度（取自 class_probs 第一项）

    Args:
        image_path (str): 图片路径

    Returns:
        tuple: (label, confidence) 或 (None, None) 如果失败
    """
    result = predict_image(image_path)
    if result["success"] and result.get("class_probs"):
        top = result["class_probs"][0]
        return top["name"], top["prob"]
    return None, None


# ======================
# 第三方大模型（LLM）识别
# ======================

def _build_db_prompt(base_prompt: str) -> str:
    """实验性（LLM_DB_RECOGNITION=True）：把 classes.json 中已知角色的
    features_used / tags 附加到提示词，让 LLM 对照角色数据库匹配识别。

    Args:
        base_prompt: 原始识别提示词

    Returns:
        str: 附加了角色数据库的提示词；加载失败或数据库为空时返回原提示词
    """
    try:
        from utils.file_utils import load_classes_json_data

        data = load_classes_json_data(str(CLASSES_JSON_PATH))
    except Exception as e:
        logger.warning("LLM 加载角色数据库失败，使用默认提示词: %s", e)
        return base_prompt
    if not data:
        return base_prompt

    lines = [
        "",
        "【已知角色数据库（供你对照匹配，label 应优先从下列角色中选择）】",
    ]
    for name, meta in data.items():
        if not isinstance(meta, dict):
            continue
        feats = meta.get("features_used") or []
        tags = meta.get("tags") or []
        parts = []
        if feats:
            parts.append("特征: " + "、".join(str(f) for f in feats))
        if tags:
            parts.append("标签: " + "、".join(str(t) for t in tags))
        if parts:
            lines.append(f"- {name}（{'；'.join(parts)}）")
    if len(lines) <= 1:
        return base_prompt
    return base_prompt + "\n".join(lines)


def _cross_compute_confidence(label, confidence, features_used, tags, profiles):
    """用角色数据库（classes.json 中的 features_used / tags）与 LLM 输出的
    特征/标签交叉计算置信度。

    原理：LLM 给出的 label + confidence 不再作为最终结论，而是把 LLM 提取的
    features_used / tags 与数据库中该角色的档案做匹配度计算，再与 LLM 置信度
    交叉加权：
      - 匹配度高 → 置信度基本保留（甚至小幅提升）
      - 匹配度低 → 置信度被明显压低（特征/标签完全对不上时封顶 45%）

    Args:
        label: LLM 判定的角色（"IP/角色"）
        confidence: LLM 给出的置信度（0-100）
        features_used: LLM 提取的视觉特征列表
        tags: LLM 提取的标签列表
        profiles: classes.json 的角色档案 dict {类别名: {features_used, tags}}

    Returns:
        (float, bool): (交叉计算后的置信度, 是否命中数据库档案)
    """
    if not profiles:
        return confidence, False
    profile = profiles.get(label)
    if not profile or not isinstance(profile, dict):
        return confidence, False

    prof_feats = set(str(f) for f in (profile.get("features_used") or []))
    prof_tags = set(str(t) for t in (profile.get("tags") or []))
    llm_feats = set(str(f) for f in (features_used or []))
    llm_tags = set(str(t) for t in (tags or []))
    if not prof_feats and not prof_tags:
        # 档案为空，无法交叉验证，保持原置信度
        return confidence, True

    def _overlap(a, b):
        """重合度：交集大小 / 较长的集合（0~1）"""
        if not a or not b:
            return 0.0
        return len(a & b) / max(len(a), len(b))

    # 标签语义更宽泛、更适合交叉验证，权重更高
    tag_score = _overlap(llm_tags, prof_tags)
    feat_score = _overlap(llm_feats, prof_feats)
    match_score = 0.6 * tag_score + 0.4 * feat_score  # 0~1

    # 交叉置信度 = 70% LLM 置信度 + 30% 特征/标签匹配度
    crossed = 0.7 * float(confidence) + 0.3 * match_score * 100.0
    if match_score < 0.25:
        # 特征/标签与数据库档案基本对不上，即使 LLM 高置信也压到 45% 以下
        crossed = min(crossed, 45.0)
    return round(crossed, 2), True


def _merge_llm_class_probs(label, confidence, class_probs):
    """把 LLM 的主结论（label + confidence）与备选列表合并为统一的 class_probs。

    统一结构：按概率降序的 [{"name": "IP/角色", "prob": 0-100}]，第一项即最佳结果。
    旧的备选格式 {"label", "confidence"} 在 _parse_llm_response 中已转换为
    {"name", "prob"}。

    Args:
        label: LLM 判定的角色（"IP/角色"）
        confidence: 主结论置信度（0-100，可能已经过交叉计算）
        class_probs: 备选角色列表 [{"name", "prob"}]

    Returns:
        list: 合并、去重、降序排列后的 class_probs（最多 10 项）
    """
    merged = [{"name": label, "prob": round(float(confidence), 2)}]
    seen = {label}
    for item in class_probs or []:
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            prob = round(float(item.get("prob", 0) or 0), 2)
        except (TypeError, ValueError):
            prob = 0.0
        merged.append({"name": name, "prob": prob})
    merged.sort(key=lambda x: x["prob"], reverse=True)
    return merged[:10]


def _cap_items(items, limit):
    """按上限截断列表（limit<=0 表示不限制）。"""
    items = list(items or [])
    if limit is None or limit <= 0:
        return items
    return items[:limit]


# 可重试的 HTTP 状态码：限流 + 服务端/网关临时错误
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def _parse_retry_after(resp):
    """解析响应头 Retry-After（秒数或 HTTP 日期），拿不到返回 None。"""
    try:
        raw = (getattr(resp, "headers", None) or {}).get("Retry-After")
    except Exception:
        raw = None
    if not raw:
        return None
    text = str(raw).strip()
    if text.isdigit():
        return float(text)
    try:
        import email.utils
        from datetime import datetime, timezone

        when = email.utils.parsedate_to_datetime(text)
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return (when - datetime.now(timezone.utc)).total_seconds()
    except Exception:
        return None


def _retry_delay(resp, attempt, base=None, cap=None):
    """第 attempt 次失败后的等待秒数：优先 Retry-After，否则指数退避 + 抖动。"""
    base = float(LLM_RETRY_BASE_SEC if base is None else base)
    cap = float(LLM_RETRY_MAX_SEC if cap is None else cap)
    delay = _parse_retry_after(resp)
    if delay is None or delay <= 0:
        delay = base * (2 ** max(0, attempt - 1))
    delay = max(0.0, min(float(delay), cap))
    # 抖动：最多 +25%（避免多节点同时重试再次撞限流）
    return delay + random.uniform(0, delay * 0.25)


def _encode_image_for_llm(image_path, max_side=None, quality=85):
    """把图片缩放压缩后转 base64（视觉模型不需要大图，顺便省 token / 避免网关断开）。

    Returns:
        (image_b64, mime)；失败返回 (None, "")
    """
    import base64 as _base64
    import io as _io

    try:
        with Image.open(image_path) as img:
            rgb = img.convert("RGB")
            limit = int(max_side or LLM_IMAGE_MAX_SIDE)
            width, height = rgb.size
            if limit and max(width, height) > limit:
                ratio = limit / float(max(width, height))
                rgb = rgb.resize((max(1, int(width * ratio)), max(1, int(height * ratio))),
                                 Image.LANCZOS)
            buf = _io.BytesIO()
            rgb.save(buf, format="JPEG", quality=quality)
            return _base64.b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"
    except Exception as e:
        logger.error("LLM 图片编码失败 %s: %s", image_path, e)
        return None, ""


def _attach_yolo_note(result):
    """YOLO（人物检测框）不可用时，把真实原因塞进识别结果。

    服务器上常见"ultralytics 装了但 opencv 缺 libGL" —— 以前只在节点日志里报一句
    "ultralytics 未安装"，接口/前端完全看不出为什么没有检测框。
    """
    try:
        from detection.yolo_detector import yolo_available
        ok, reason = yolo_available()
    except Exception as exc:
        ok, reason = False, "检测器初始化失败：%s" % exc
    if not ok and reason:
        result["yolo_error"] = reason
    return result


def resolve_llm_crop_method() -> str:
    """决定"切图给 LLM"用哪个检测器。

    auto：本地模型开启 → yolo（更准）；只做 LLM 的节点 → mediapipe（不需要 torch）。
    """
    method = (LLM_CROP_METHOD or "auto").strip().lower()
    if method == "auto":
        return "yolo" if LOCAL_RECOGNITION_ENABLED else "mediapipe"
    return method


def crop_for_llm(image_path, method: str = None):
    """把图里的人物切成子图（坐标直接取检测框，不让 LLM 猜位置）。

    Returns:
        (characters, tmp_dir, used_method)：characters 为检测器给的子图列表
        （每项含 crop_path / bbox_norm / bbox_percent / detector_confidence）。
    """
    method = method or resolve_llm_crop_method()
    if method == "none":
        return [], None, "none"
    try:
        from detection.cropper import crop_characters_by_method
    except ImportError:
        return [], None, "none"

    try:
        found = crop_characters_by_method(
            image_path, method=method, max_characters=LLM_MAX_CHARACTERS,
        )
    except Exception as e:
        logger.warning("LLM 切图失败（回退整图识别）: %s", e)
        return [], None, "none"

    crops = found.get("characters") or []
    used = found.get("crop_method") or method
    if crops:
        logger.info("LLM 切图: %d 个人物（方式=%s）", len(crops), used)
    return crops, found.get("tmp_dir"), used


def predict_image_llm(image_path: str) -> dict:
    """通过第三方多模态 API（如 DeepSeek、GPT-4V）识别图片角色。

    识别结果统一结构：最佳结果在 class_probs[0]（{name, prob}），
    不再返回顶层 label / confidence 字段。

    Args:
        image_path (str): 图片本地路径

    Returns:
        dict: 与 predict_image() 格式一致的识别结果
    """
    result = {
        "success": False,
        "class_probs": [],
        "image_path": image_path,
        "error": None,
        "recognition_type": "llm",
    }

    if not LLM_RECOGNITION_ENABLED:
        result["error"] = "LLM 识别未启用（LLM_RECOGNITION_ENABLED=False）"
        logger.warning("LLM %s", result["error"])
        return result

    try:
        import base64
        import io
        import requests

        # 整图编码（仅回退路径用；切图路径下每个子图单独编码）
        image_b64, image_mime = _encode_image_for_llm(image_path)
        if not image_b64:
            result["error"] = f"图片编码失败: {image_path}"
            logger.error("LLM %s", result["error"])
            return result

        logger.info("LLM 请求 API: %s, 模型: %s, 图片: %s", LLM_API_URL, LLM_MODEL_NAME, image_path)

        # LLM_API_KEY 允许为空：为空时不携带 Authorization 头
        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"

        # 根据 LLM_API_TYPE 选择请求格式：
        # - "chat-completions" → OpenAI 兼容格式 (image_url / max_tokens)【默认】
        # - "responses"        → OpenAI Responses API 格式 (input_image / max_output_tokens)
        # - "anthropic"        → Anthropic Messages API 格式 (image/source / max_tokens)
        # - "ollama"           → Ollama 原生格式 (images / options)
        # LLM_THINKING 控制是否开启模型思考（推理）过程：默认关闭，让模型直接输出结果。
        def _build_payload(prompt: str, image_b64: str, image_mime: str) -> dict:
            if LLM_API_TYPE == "responses":
                # OpenAI Responses API（如 gpt-5）：图片放在 input 中，token 上限用 max_output_tokens
                payload = {
                    "model": LLM_MODEL_NAME,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": (
                                        f"data:{image_mime};base64,{image_b64}"
                                    ),
                                },
                            ],
                        }
                    ],
                    "max_output_tokens": LLM_MAX_TOKEN,  # 推理模型思考+结论，需要更多 token
                    "temperature": 0.1,
                }
                if LLM_THINKING:
                    payload["reasoning"] = {"effort": "high"}
                return payload
            if LLM_API_TYPE == "anthropic":
                # Anthropic Messages API（如 claude）：图片用 image/source (base64)
                payload = {
                    "model": LLM_MODEL_NAME,
                    "max_tokens": LLM_MAX_TOKEN,  # 推理模型思考+结论，需要更多 token
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": image_mime,
                                        "data": image_b64,
                                    },
                                },
                            ],
                        }
                    ],
                }
                # Anthropic 思考显式开关：开启启用思考并分配预算，关闭则禁用
                if LLM_THINKING:
                    payload["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": LLM_MAX_TOKEN,
                    }
                else:
                    payload["thinking"] = {"type": "disabled"}
                return payload
            if LLM_API_TYPE == "ollama":
                payload = {
                    "model": LLM_MODEL_NAME,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": LLM_MAX_TOKEN,  # 推理模型思考+结论，需要更多 token
                        "temperature": 0.1,
                    },
                }
                # Ollama 思考开关（对支持思考的模型，如 Qwen）
                payload["options"]["think"] = LLM_THINKING
                return payload
            # OpenAI 兼容格式（chat-completions，兜底默认，mimo 等走此分支）
            payload = {
                "model": LLM_MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                # mimo 等 OpenAI 兼容模型用 max_completion_tokens 限制"思考+回答"总长度
                "max_completion_tokens": LLM_MAX_TOKEN,
            }
            # 深度思考开关（mimo / DeepSeek 等用 thinking.type，而非 OpenAI 的 reasoning_effort）：
            # - 开启思考：显式 enabled；mimo 思考模式不支持 temperature/top_p（强制 1.0/0.95），故不传
            # - 关闭思考：显式 disabled；此时可传 temperature 保证确定性输出
            if LLM_THINKING:
                payload["thinking"] = {"type": "enabled"}
            else:
                payload["thinking"] = {"type": "disabled"}
                payload["temperature"] = 0.1
            return payload

        # 本轮请求的软错误（限流/超时/断开等可重试失败）：
        # 只有整图路径才算整体失败；一图多角时只表示"这个人没识别出来"
        soft = {"last": None, "counts": {}}
        started_at = time.time()

        def _deadline_left():
            """距离整张图的总预算还剩多少秒（0=不限）。"""
            if LLM_MAX_TOTAL_SEC <= 0:
                return None
            return LLM_MAX_TOTAL_SEC - (time.time() - started_at)

        def _post_with_retry(prompt, image_b64, image_mime):
            """POST 一次（含限流/服务端错误的退避重试）。

            Returns:
                (resp, soft_error)：soft_error 非空表示"重试耗尽仍失败"，
                此时 resp 为 None；拿到响应时 soft_error 为 None（状态码由调用方判断）。
            """
            attempts = max(1, int(LLM_MAX_ATTEMPTS))
            last = None
            last_resp = None          # 保留上一次响应，用于读取 Retry-After
            for attempt in range(1, attempts + 1):
                resp = None
                if attempt > 1:
                    delay = _retry_delay(last_resp, attempt - 1)
                    left = _deadline_left()
                    if left is not None and left <= delay:
                        logger.warning(
                            "LLM 重试预算不足（剩余 %.1fs < 需等待 %.1fs），放弃本次请求", left, delay
                        )
                        break
                    logger.warning(
                        "LLM 请求失败，%.1fs 后重试（第 %d/%d 次）", delay, attempt, attempts
                    )
                    time.sleep(delay)
                try:
                    resp = requests.post(
                        LLM_API_URL,
                        headers=headers,
                        json=_build_payload(prompt, image_b64, image_mime),
                        timeout=LLM_TIMEOUT_SEC,
                    )
                except requests.ConnectionError as e:
                    last = ("connection", f"连接被断开: {e}")
                except requests.Timeout:
                    last = ("timeout", f"请求超时 ({LLM_TIMEOUT_SEC}秒)")
                else:
                    last_resp = resp
                    if resp.status_code == 200 or resp.status_code not in _RETRYABLE_STATUS:
                        return resp, None
                    last = ("http_%d" % resp.status_code,
                            "API 返回错误 (%d): %s" % (resp.status_code, resp.text[:150]))
                    # 用响应里的 Retry-After 覆盖下一次等待
                    retry_after = _parse_retry_after(resp)
                    if retry_after and retry_after > 0:
                        logger.warning("服务端要求 %.0fs 后重试（Retry-After）", retry_after)
                if _deadline_left() is not None and _deadline_left() <= 0:
                    logger.warning("LLM 总时间预算（%.0fs）已用尽，停止重试", LLM_MAX_TOTAL_SEC)
                    break
            return None, last

        def _request(prompt: str, image_b64: str, image_mime: str):
            """识别一张图，返回 (label, confidence, features_used, tags, class_probs)。

            限流/服务端错误会退避重试；重试仍失败时返回空结果，
            并把原因放进 soft（一图多角时只跳过这一个子图，不影响其它人物）。
            """
            resp, err = _post_with_retry(prompt, image_b64, image_mime)
            if err is not None:
                soft["last"] = err
                soft["counts"][err[0]] = soft["counts"].get(err[0], 0) + 1
                logger.error("LLM 请求失败（已重试 %d 次）: %s", LLM_MAX_ATTEMPTS, err[1])
                return None, None, [], [], []
            if resp.status_code != 200:
                result["error"] = f"API 返回错误 ({resp.status_code}): {resp.text[:200]}"
                logger.error("LLM %s", result["error"])
                return None, None, [], [], []
            return _parse_llm_response(resp.json())

        # 实验性模式（LLM_DB_RECOGNITION=True）：把 classes.json 中已知角色的
        # features_used / tags 附加到提示词，让 LLM 对照角色数据库匹配识别
        prompt = LLM_PROMPT_TEMPLATE
        if LLM_DB_RECOGNITION:
            prompt = _build_db_prompt(prompt)

        def _finalize(label_in, confidence_in, features_in, tags_in, probs_in):
            """交叉计算置信度（可选）+ 合并候选 + 附加类别元数据，返回 (confidence, class_probs)。"""
            conf = confidence_in
            if LLM_DB_RECOGNITION:
                try:
                    profiles = load_classes_json_data(str(CLASSES_JSON_PATH))
                    conf, _ = _cross_compute_confidence(
                        label_in, conf, features_in, tags_in, profiles
                    )
                    logger.info("LLM 交叉计算置信度: %s -> %.2f%%", label_in, conf)
                except Exception as cross_err:
                    logger.warning("LLM 交叉计算置信度失败，使用原始置信度: %s", cross_err)
            merged = _merge_llm_class_probs(label_in, conf, probs_in)
            _enrich_probs_with_metadata(merged)
            return conf, merged

        # ======================
        # === 一图多角：先切图，再逐张问 LLM ===
        # ======================
        # 坐标直接取 YOLO / MediaPipe 的检测框（不让 LLM 猜位置），
        # 而且模型每次只看一个人，识别更准；
        # 代价：N 个人物 = N 次 API 调用（上限见 LLM_MAX_CHARACTERS）
        characters = []
        failed_characters = []          # 限流/超时等导致"这个人没识别出来"的记录
        crops, crop_tmp_dir, used_crop_method = ([], None, "none")
        if LLM_MULTI_CHARACTER:
            crops, crop_tmp_dir, used_crop_method = crop_for_llm(image_path)

        try:
            for item in crops:
                crop_b64, crop_mime = _encode_image_for_llm(
                    item.get("crop_path"), max_side=LLM_CROP_MAX_SIDE
                )
                if not crop_b64:
                    continue
                c_label, c_conf, c_feats, c_tags, c_probs = _request(prompt, crop_b64, crop_mime)
                if not c_label:
                    reason = soft["last"][1] if soft["last"] else "LLM 未识别出角色"
                    kind = soft["last"][0] if soft["last"] else "unrecognized"
                    soft["last"] = None
                    failed_characters.append({
                        "index": item.get("index"),
                        "bbox_percent": item.get("bbox_percent"),
                        "reason": kind,
                        "message": reason,
                    })
                    logger.info("第 %s 个人物未识别（%s），跳过，其余人物不受影响",
                                item.get("index"), kind)
                    continue
                c_conf, merged = _finalize(c_label, c_conf, c_feats, c_tags, c_probs)
                characters.append({
                    "index": item.get("index", len(characters)),
                    "label": c_label,
                    "confidence": round(float(c_conf or 0), 2),
                    "bbox": item.get("bbox_norm"),
                    "bbox_percent": item.get("bbox_percent"),
                    "detector_confidence": item.get("detector_confidence"),
                    "class_probs": merged,
                    "features_used": c_feats,
                    "tags": c_tags,
                    "source": "llm",
                })
        finally:
            if crop_tmp_dir:
                shutil.rmtree(crop_tmp_dir, ignore_errors=True)

        if characters:
            best = max(characters, key=lambda c: c.get("confidence") or 0)
            result.update({
                "success": True,
                "error": None,                          # 有任意人物成功就不算整张失败
                "class_probs": best["class_probs"],     # 兼容旧客户端：顶层=最确定的人物
                "features_used": best.get("features_used") or [],
                "tags": best.get("tags") or [],
                "characters": characters,
                "character_count": len(characters),
                "crop_method": f"llm_{used_crop_method}",
                "image": None,
            })
            if failed_characters:
                # 限流/超时导致没识别出来的人物：单独列出，前端可选择展示"该人物未识别"
                result["failed_characters"] = failed_characters
                result["character_failed_count"] = len(failed_characters)
                result["warnings"] = [
                    "有 %d 个人物未识别：%s" % (
                        len(failed_characters),
                        ", ".join(sorted(soft["counts"])) or "unrecognized",
                    )
                ]
            logger.info(
                "LLM 多角色识别: %s -> %d 个人物（切图=%s，最佳 %s%s）",
                image_path, len(characters), used_crop_method, best["label"],
                "，%d 个未识别" % len(failed_characters) if failed_characters else "",
            )
            return result

        # 没切出人物（或切图关闭）→ 整图单次识别（旧行为，只识别主体）
        label, confidence, features_used, tags, class_probs = _request(prompt, image_b64, image_mime)

        if not label or label.lower() == "unknown":
            if soft["last"]:
                # 限流/超时/断开等，重试已耗尽：如实报出原因而不是"无法识别"
                result["error"] = f"LLM 请求失败（{soft['last'][0]}）: {soft['last'][1]}"
                logger.error("LLM %s", result["error"])
            elif not result.get("error"):
                # 已经由 _request 记录过具体错误（如 401/403）就不要覆盖成"无法识别"
                result["error"] = f"LLM 无法识别该角色: {label}"
                logger.warning("LLM %s", result["error"])
            return result

        # 统一结果结构：最佳结果在 class_probs[0]（不再返回顶层 label/confidence）
        confidence, merged_probs = _finalize(label, confidence, features_used, tags, class_probs)
        characters = [{
            "index": 0,
            "label": label,
            "confidence": round(float(confidence or 0), 2),
            "bbox": None,            # 整图识别没有人物框
            "bbox_percent": None,
            "class_probs": merged_probs,
            "features_used": features_used,
            "tags": tags,
            "source": "llm",
        }]
        result.update(
            {
                "success": True,
                "class_probs": merged_probs,
                "features_used": features_used,
                "tags": tags,
                # 与 37ac 通道对齐的契约（整图路径只有 1 条、无框）
                "characters": characters,
                "character_count": 1,
                "crop_method": "llm",
                "image": None,
            }
        )
        logger.info("LLM 识别成功（整图）: %s -> %s", image_path, label)
        return result

    except ImportError:
        result["error"] = "缺少 requests 库，请执行: pip install requests"
        logger.error("LLM %s", result["error"])
        return result
    except requests.Timeout:
        result["error"] = f"API 请求超时 ({LLM_TIMEOUT_SEC}秒)"
        logger.error("LLM %s", result["error"])
        return result
    except Exception as e:
        result["error"] = f"LLM 识别异常: {str(e)}"
        logger.error("LLM %s", result["error"], exc_info=True)
        return result


def _extract_json(text: str):
    """从文本中提取第一个完整的 JSON 对象（支持嵌套结构）。

    Args:
        text: 可能包含 JSON 的文本

    Returns:
        dict | None: 解析成功的字典；未找到返回 None
    """
    if not text:
        return None
    decoder = json.JSONDecoder()
    # 遍历每个 '{' 位置，尝试用 raw_decode 解析完整 JSON（支持嵌套、容忍尾部杂质）
    for m in re.finditer(r'\{', text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            continue
    # 兜底：截取第一个 '{' 到最后一个 '}' 之间尝试 json.loads
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    return None


# 作品/IP 名称的强特征词（用于检测 label 顺序是否写反）
_WORK_NAME_HINTS = (
    "project", "series", "vocaloid", "utau", "东方", "舰队collection", "舰队收藏",
    "偶像大师", "lovelive", "live", "歌姬计划", "崩坏", "原神", "明日方舟",
    "碧蓝航线", "少女前线", "赛马娘", "公主连结", "蔚蓝档案", "fate", "fgo",
    "宝可梦", "数码宝贝", "奥特曼", "假面骑士", "高达", "舰队", "偶像",
    "hololive", "nijisanji", "彩虹社",
)


def _normalize_label_order(label: str) -> str:
    """确保 label 为「作品名/角色名」顺序。

    提示词要求「作品/角色」，但模型偶尔会写反成「角色/作品」。
    当第二段包含强烈的作品/IP 特征词、而第一段没有时，自动交换顺序。
    无法可靠判断时保持原样，避免误改正确结果。
    """
    if not label or "/" not in label:
        return label
    parts = label.split("/")
    if len(parts) != 2:
        return label
    first, second = parts[0].strip(), parts[1].strip()
    if not first or not second:
        return label
    first_lower, second_lower = first.lower(), second.lower()
    # 第二段像作品名而第一段不像 → 顺序写反，交换
    if (any(h in second_lower for h in _WORK_NAME_HINTS)
            and not any(h in first_lower for h in _WORK_NAME_HINTS)):
        return f"{second}/{first}"
    return label


def _parse_llm_response(resp_data: dict) -> tuple:
    """从 LLM API 响应中提取 (label, confidence, features_used, tags, class_probs)。

    兼容四种请求格式对应的响应结构：
    - Ollama /api/chat:      {"message": {"content": "...", "reasoning_content": "..."}}
    - OpenAI 兼容 chat:      {"choices": [{"message": {"content": "...", "reasoning_content": "..."}}]}
    - OpenAI Responses API:  {"output": [{"content": [{"type":"output_text","text":"..."}]}]}
    - Anthropic Messages:    {"content": [{"type":"text","text":"..."}, {"type":"thinking","thinking":"..."}]}
    - 推理模型:              content 可能为 None/空，结论在 reasoning_content / thinking 中

    与 _DEFAULT_LLM_PROMPT 约定的输出结构一致：
    {"label": "作品/角色名", "confidence": 95, "features_used": ["发色", "服装"],
     "tags": ["银发", "女性角色"], "class_probs": [{"label": "...", "confidence": 3}, ...]}
    - 优先读取 "class_probs"（提示词约定的字段）
    - 兼容旧字段 "alternative_guesses"
    两者统一转换为与本地模型一致的 [{"name": "作品/角色名", "prob": 3}] 格式。
    """
    try:
        content = None
        reasoning = None

        # 1) Anthropic Messages 格式：content 是块列表
        content_blocks = resp_data.get("content")
        if isinstance(content_blocks, list):
            text_parts, thinking_parts = [], []
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text"):
                    text_parts.append(block["text"])
                elif block.get("type") == "thinking" and block.get("thinking"):
                    thinking_parts.append(block["thinking"])
            content = "\n".join(text_parts) or None
            reasoning = "\n".join(thinking_parts) or None

        # 2) OpenAI Responses API 格式：output 数组，块类型 output_text
        if content is None and isinstance(resp_data.get("output"), list):
            text_parts, reasoning_parts = [], []
            for item in resp_data["output"]:
                if not isinstance(item, dict):
                    continue
                inner = item.get("content") or []
                if isinstance(inner, list):
                    for block in inner:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "output_text" and block.get("text"):
                            text_parts.append(block["text"])
                        elif block.get("type") == "reasoning" and block.get("summary"):
                            reasoning_parts.append(str(block["summary"]))
            content = "\n".join(text_parts) or None
            reasoning = "\n".join(reasoning_parts) or None

        # 3) Ollama /api/chat 格式
        if content is None:
            message = resp_data.get("message")
            if message:
                content = message.get("content")
                reasoning = message.get("reasoning_content")

        # 4) OpenAI 兼容格式 /v1/chat/completions
        if content is None:
            choices = resp_data.get("choices") or [{}]
            message = choices[0].get("message", {}) if len(choices) > 0 else {}
            content = message.get("content")
            reasoning = message.get("reasoning_content")

        # 推理模型：content 可能为 None/空。
        # 重要：绝不能把纯推理过程（reasoning_content）当作最终答案。
        # 仅当 reasoning 中能提取出完整 JSON（含 label）时才采用，否则视为无有效内容。
        if not content and reasoning:
            parsed = _extract_json(str(reasoning))
            if parsed and parsed.get("label"):
                content = json.dumps(parsed, ensure_ascii=False)
                logger.info("LLM 从 reasoning_content 提取到 JSON 结论")
            else:
                logger.warning(
                    "LLM content 为空且 reasoning 中无有效 JSON 结论，放弃识别"
                )

        if not content:
            logger.error("LLM API 返回空内容: %s", resp_data)
            return ("", 0.0, [], [], [])

        content = str(content).strip()

        # 默认值
        features_used = []
        tags = []
        class_probs = []

        # 优先从 JSON 中提取结构化结果（支持嵌套结构）
        parsed = _extract_json(content)
        if parsed:
            raw_label = parsed.get("label")
            label = str(raw_label).strip() if raw_label else ""
            confidence = float(parsed.get("confidence", 95.0))

            # 关键特征（如 ["蓝发", "和服"]）：最多 LLM_MAX_FEATURES 条（默认 3）
            raw_features = parsed.get("features_used")
            if isinstance(raw_features, list):
                features_used = _cap_items(
                    [str(f).strip() for f in raw_features if str(f).strip()], LLM_MAX_FEATURES
                )

            # 标签（如 ["银发", "长发", "女性角色"]）：最多 LLM_MAX_TAGS 条（默认 3）
            raw_tags = parsed.get("tags")
            if isinstance(raw_tags, list):
                tags = _cap_items(
                    [str(t).strip() for t in raw_tags if str(t).strip()], LLM_MAX_TAGS
                )

            # 备选角色 → class_probs（统一 Candidate 结构，见 common/recognition.py）
            # 提示词约定字段为 "class_probs"（{"label","confidence"}），
            # 兼容旧字段 "alternative_guesses"。
            raw_alts = parsed.get("class_probs")
            if not isinstance(raw_alts, list):
                raw_alts = parsed.get("alternative_guesses")
            if isinstance(raw_alts, list):
                probs = []
                for g in raw_alts:
                    candidate = parse_candidate_entry(g)
                    if not candidate:
                        continue
                    # 与主 label 一致，确保「作品/角色」顺序
                    candidate["name"] = _normalize_label_order(candidate["name"])
                    # 跳过提示词占位符条目（如 "作品名/角色名"）
                    if _is_placeholder_label(candidate["name"]):
                        continue
                    probs.append(candidate)
                class_probs = probs

            if not label:
                reason = parsed.get("reason")
                logger.info("LLM 模型判定特征不足: %s", reason or "无原因说明")
        else:
            # 降级：纯文本作为标签——但要拒绝空串 / JSON 片段 / 超长文本，
            # 否则模型返回 "{}" 之类会被当成角色名传给下游
            text_label = str(content).strip()
            if not text_label or text_label[0] in "{[<" or len(text_label) > 100:
                logger.warning("LLM 返回内容既不是 JSON 也不像角色标签，放弃: %s", text_label[:80])
                return ("", 0.0, [], [], [])
            label = text_label
            confidence = 95.0

        # 裁剪方案下每次只问一个子图，这里就是单角色结果；
        # 若用的是自定义的"整图多角"提示词（返回 characters 数组），取第一条作为主结论
        if not label and parsed and isinstance(parsed.get("characters"), list) and parsed["characters"]:
            first = parsed["characters"][0] if isinstance(parsed["characters"][0], dict) else {}
            label = str(first.get("label") or "").strip()
            try:
                confidence = float(first.get("confidence", confidence))
            except (TypeError, ValueError):
                pass

        # 确保「作品/角色」顺序（模型偶尔会写成「角色/作品」）
        label = _normalize_label_order(label)

        # 过滤非角色标签（安全审查、拒绝回答等）
        if _is_invalid_label(label):
            logger.warning("LLM 过滤无效标签: %s", label)
            return ("", 0.0, [], [], [])

        return label, confidence, features_used, tags, class_probs

    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.error("LLM 无法解析 API 响应: %s, 错误: %s", resp_data, e)
        return ("", 0.0, [], [], [])


def _is_placeholder_label(label: str) -> bool:
    """判断标签是否为提示词模板占位符（模型未真正识别，回显了示例占位文本）。

    如 "作品名/角色名"、"未知作品/角色名" 等。这类文本永远不会是真实角色名。
    """
    if not label:
        return False
    lower = label.lower()
    placeholder_markers = ["作品名", "角色名", "未知作品", "未知角色",
                           "example", "示例", "character name", "work name"]
    return any(pm in lower for pm in placeholder_markers)


def _is_invalid_label(label: str) -> bool:
    """判断 LLM 输出的标签是否为有效的角色名称。"""
    if not label:
        return True
    
    # 角色名合理长度：最长的一般不超过 30 个字符（如 "崩坏：星穹铁道/银狼"）
    if len(label) > 50:
        return True

    lower = label.lower()

    # 提示词模板占位符（如 "作品名/角色名"、"未知作品/角色名"）
    if _is_placeholder_label(label):
        return True

    # 安全审查关键词
    safety_keywords = ["user safety", "safe", "unsafe", "content safety", "nsfw"]
    for kw in safety_keywords:
        if kw in lower:
            return True

    # 拒绝回答模式
    refuse_keywords = ["sorry", "apologize", "cannot", "can't", "unable", "not able",
                       "i'm sorry", "i am sorry", "拒绝", "无法"]
    for kw in refuse_keywords:
        if kw in lower:
            return True

    # 中文描述性开头（非角色名句式）
    desc_patterns = [r'^图中', r'^图片中', r'^这张', r'^该角色', r'^这是', r'^这位',
                     r'^画面', r'^这幅', r'^从画', r'^角色是', r'^根据']
    for p in desc_patterns:
        if re.search(p, label):
            return True

    # 中文句子特征：句号、感叹号、问号、破折号等表明这是一段描述而非角色名
    # 注意：不包含全角冒号"："，它常见于作品标题（如"崩坏：星穹铁道/银狼"），
    # 若加入会导致这类合法标签被误杀。
    sentence_markers = ['。', '！', '？', '——', '～', '~', '…', '●']
    for m in sentence_markers:
        if m in label:
            return True

    # 长度异常：不超过 50 字符的角色名中出现这些标志
    url_patterns = ['http', 'www.', '.com', '.org', '.cn', '萌娘百科', '维基']
    for u in url_patterns:
        if u in lower:
            return True

    return False
