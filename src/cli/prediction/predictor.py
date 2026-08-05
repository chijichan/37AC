# prediction/predictor.py
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import os
import json
import re
import time
import threading
from utils.image_utils import validate_image_file
from utils.file_utils import load_classes_from_file, check_model_file
from models.character_model import CharacterRecognitionModel
from config.base import (
    IMAGE_SIZE,
    CLASSES_TXT_PATH,
    MODEL_LOAD_PATH,
    YOLO_ENABLED,
    LLM_RECOGNITION_ENABLED,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_API_TYPE,
    LLM_MODEL_NAME,
    LLM_PROMPT_TEMPLATE,
    LLM_TIMEOUT_SEC,
    get_device,
)
from config.log_config import get_logger

logger = get_logger(__name__)

# YOLO 人物检测（可选）
try:
    from detection.yolo_detector import crop_best_character
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.debug("YOLO 检测模块不可用，使用全图分类")

# 数据预处理
PREDICT_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)

# 全局模型缓存，避免重复加载
# 缓存结构：{ "model": nn.Module, "num_classes": int, "classes": list }
_model_cache = None
_classes_cache = None
_cache_lock = threading.Lock()


def predict_character():
    """交互式预测函数（保持原有功能）"""
    # --- 1. 加载类别 ---
    CLASS_NAMES = load_classes_from_file(CLASSES_TXT_PATH)
    if not CLASS_NAMES:
        return

    # --- 2. 验证模型文件存在 ---
    if not check_model_file(MODEL_LOAD_PATH):
        return

    # --- 3. 用户输入图片路径 ---
    while True:
        try:
            user_input = input("请输入你要预测的图片路径（或输入 0 返回主菜单）: ").strip().strip("\"'").strip("\x1a")
        except (KeyboardInterrupt, EOFError):
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
            logger.info(f"找不到图片: {user_input}，请检查路径是否正确~")
            continue
        if not user_input.lower().endswith((".jpg", ".jpeg", ".png", ".jfif")):
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
    if not result.get("success"):
        logger.error(f"预测失败: {result.get('error', '未知错误')}")
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

        if not image_path.lower().endswith((".jpg", ".jpeg", ".png", ".jfif")):
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
                    effective_image = crop_path
                    yolo_info = det_info
                    logger.info(
                        "YOLO 定位到角色区域: %s, 类别=%s, 置信度=%.2f",
                        det_info["bbox"] if det_info else "N/A",
                        det_info["class_name"] if det_info else "N/A",
                        det_info["confidence"] if det_info else 0,
                    )
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
                if use_cache:
                    with _cache_lock:
                        _model_cache = (model, NUM_CLASSES)
            except Exception as e:
                result["error"] = f"模型加载失败: {str(e)}"
                logger.error(f"模型加载失败: {str(e)}", exc_info=True)
                return result

        # ======================
        # === 图像预处理和预测 ===
        # ======================
        transform = PREDICT_TRANSFORMS

        try:
            # 使用 YOLO 裁剪后的图片（如有）进行分类
            with Image.open(effective_image) as img:
                image = img.convert("RGB")
            image_tensor = transform(image).unsqueeze(0).to(get_device())

            with torch.no_grad():
                outputs = model(image_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probs, 1)

                label = CLASS_NAMES[predicted_idx.item()]
                confidence_value = confidence.item() * 100

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

                # 成功返回结果
                result.update(
                    {
                        "success": True,
                        "label": label,
                        "confidence": round(confidence_value, 2),
                        "class_probs": class_probs,
                        "features_used": [],  # 本地模型无可解释文本特征，留空
                        "yolo_detected": yolo_info is not None,
                    }
                )

                logger.info(
                    f"预测成功: {image_path} -> {label} ({confidence_value:.2f}%)"
                    + (f" [YOLO定位]" if yolo_info else "")
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


# ======================
# 第三方大模型（LLM）识别
# ======================

def predict_image_llm(image_path: str) -> dict:
    """通过第三方多模态 API（如 DeepSeek、GPT-4V）识别图片角色。

    Args:
        image_path (str): 图片本地路径

    Returns:
        dict: 与 predict_image() 格式一致的识别结果
    """
    result = {
        "success": False,
        "label": "",
        "confidence": 0.0,
        "class_probs": [],
        "image_path": image_path,
        "error": None,
        "recognition_type": "llm",
    }

    if not LLM_RECOGNITION_ENABLED:
        result["error"] = "LLM 识别未启用（LLM_RECOGNITION_ENABLED=False）"
        logger.warning("[LLM] %s", result["error"])
        return result

    try:
        import base64
        import io
        import requests

        # 读取图片，缩放压缩后转 Base64（减小 payload，避免网关断开连接）
        # 视觉模型通常不需要大图，限制最长边 1024px、JPEG 质量 85
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            max_side = 1024
            w, h = img.size
            if max(w, h) > max_side:
                ratio = max_side / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            image_bytes = buf.getvalue()
        image_mime = "image/jpeg"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        logger.info(
            "[LLM] 请求 API: %s, 模型: %s, 图片: %s (压缩后 %d 字节)",
            LLM_API_URL, LLM_MODEL_NAME, image_path, len(image_bytes)
        )

        # LLM_API_KEY 允许为空：为空时不携带 Authorization 头
        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"

        # 根据 LLM_API_TYPE 选择请求格式：
        # - "ollama"           → Ollama 原生格式 (images / options)
        # - "chat-completions" → OpenAI 兼容格式 (image_url / max_tokens)
        def _build_payload(prompt: str) -> dict:
            if LLM_API_TYPE == "ollama":
                return {
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
                        "num_predict": 1024,   # 推理模型思考+结论，需要更多 token
                        "temperature": 0.1,
                    },
                }
            # OpenAI 兼容格式（chat-completions，兜底默认）
            return {
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
                "max_tokens": 1024,          # 推理模型思考+结论，需要更多 token
                "temperature": 0.1,
            }

        def _request(prompt: str, _retries: int = 2):
            """向 LLM API 发送一次识别请求，返回解析后的
            (label, confidence, features_used, class_probs)。

            ConnectionError（网关断开）时自动重试，最多 _retries 次。
            """
            for attempt in range(1, _retries + 1):
                try:
                    resp = requests.post(
                        LLM_API_URL,
                        headers=headers,
                        json=_build_payload(prompt),
                        timeout=LLM_TIMEOUT_SEC,
                    )
                except requests.ConnectionError as e:
                    logger.warning(
                        "[LLM] 连接被断开 (第 %d/%d 次): %s", attempt, _retries, e
                    )
                    if attempt < _retries:
                        time.sleep(2 * attempt)  # 2s, 4s 递增等待
                        continue
                    result["error"] = f"LLM 连接失败: {e}"
                    logger.error("[LLM] %s", result["error"])
                    return None, None, [], []
                except requests.Timeout:
                    result["error"] = f"API 请求超时 ({LLM_TIMEOUT_SEC}秒)"
                    logger.error("[LLM] %s", result["error"])
                    return None, None, [], []
                break
            if resp.status_code != 200:
                result["error"] = f"API 返回错误 ({resp.status_code}): {resp.text[:200]}"
                logger.error("[LLM] %s", result["error"])
                return None, None, [], []
            resp_data = resp.json()
            return _parse_llm_response(resp_data)

        label, confidence, features_used, class_probs = _request(LLM_PROMPT_TEMPLATE)

        if not label or label.lower() == "unknown":
            result["error"] = f"LLM 无法识别该角色: {label}"
            logger.warning("[LLM] %s", result["error"])
            return result

        result.update(
            {
                "success": True,
                "label": label,
                "confidence": confidence,
                "class_probs": class_probs,
                "features_used": features_used,
            }
        )
        logger.info("[LLM] 识别成功: %s -> %s", image_path, label)
        return result

    except ImportError:
        result["error"] = "缺少 requests 库，请执行: pip install requests"
        logger.error("[LLM] %s", result["error"])
        return result
    except requests.Timeout:
        result["error"] = f"API 请求超时 ({LLM_TIMEOUT_SEC}秒)"
        logger.error("[LLM] %s", result["error"])
        return result
    except Exception as e:
        result["error"] = f"LLM 识别异常: {str(e)}"
        logger.error("[LLM] %s", result["error"], exc_info=True)
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
    # 遍历每个 '{' 位置，尝试从该处解析完整 JSON
    for m in re.finditer(r'\{', text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _parse_llm_response(resp_data: dict) -> tuple:
    """从 LLM API 响应中提取 (label, confidence, features_used, class_probs)。

    兼容两种格式：
    - Ollama /api/chat: {"message": {"content": "..."}}
    - OpenAI 兼容:      {"choices": [{"message": {"content": "..."}}]}
    - 推理模型:          {"choices": [{"message": {"reasoning_content": "...", "content": null}}]}

    LLM 输出结构：
    {"label": "作品/角色名", "confidence": 95, "features_used": ["发色", "服装"],
     "alternative_guesses": [{"label": "...", "confidence": 55}]}
    其中 alternative_guesses 统一转换为 class_probs（与本地模型一致的 [{"name", "prob"}] 格式）。
    """
    try:
        content = None
        reasoning = None

        # 先尝试 Ollama 格式 /api/chat
        message = resp_data.get("message")
        if message:
            content = message.get("content")
            reasoning = message.get("reasoning_content")
        else:
            # 再尝试 OpenAI 兼容格式 /v1/chat/completions
            choices = resp_data.get("choices") or [{}]
            message = choices[0].get("message", {}) if len(choices) > 0 else {}
            content = message.get("content")
            reasoning = message.get("reasoning_content")

        # 推理模型：content 可能为 None/空，结论在 reasoning_content 中
        if not content and reasoning:
            text = str(reasoning).strip()
            # 1) 优先从全文搜索 JSON 结构化结果（推理过程末尾通常输出结论）
            parsed = _extract_json(text)
            if parsed and parsed.get("label"):
                content = json.dumps(parsed, ensure_ascii=False)
                logger.info("[LLM] 从 reasoning_content 提取到 JSON 结论")
            else:
                # 2) 无 JSON 时，取尾部内容（结论通常在末尾）
                content = text[-300:] if len(text) > 300 else text
                logger.info("[LLM] 使用 reasoning_content 作为识别内容")

        if not content:
            logger.error("[LLM] API 返回空内容: %s", resp_data)
            return ("", 0.0, [], [])

        content = str(content).strip()

        # 默认值
        features_used = []
        class_probs = []

        # 优先从 JSON 中提取结构化结果（支持嵌套结构）
        parsed = _extract_json(content)
        if parsed:
            raw_label = parsed.get("label")
            label = str(raw_label).strip() if raw_label else ""
            confidence = float(parsed.get("confidence", 95.0))

            # 关键特征（如 ["蓝发", "和服"]）
            raw_features = parsed.get("features_used")
            if isinstance(raw_features, list):
                features_used = [str(f).strip() for f in raw_features if str(f).strip()]

            # alternative_guesses -> class_probs（与本地模型统一格式）
            raw_alt = parsed.get("alternative_guesses") or []
            if isinstance(raw_alt, list):
                class_probs = [
                    {"name": str(g.get("label", "")).strip(), "prob": float(g.get("confidence", 0))}
                    for g in raw_alt
                    if isinstance(g, dict) and g.get("label")
                ]

            if not label:
                reason = parsed.get("reason")
                logger.info("[LLM] 模型判定特征不足: %s", reason or "无原因说明")
        else:
            # 降级：纯文本作为标签
            label = content
            confidence = 95.0

        # 过滤非角色标签（安全审查、拒绝回答等）
        if _is_invalid_label(label):
            logger.warning("[LLM] 过滤无效标签: %s", label)
            return ("", 0.0, [], [])

        return label, confidence, features_used, class_probs

    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.error("[LLM] 无法解析 API 响应: %s, 错误: %s", resp_data, e)
        return ("", 0.0, [], [])


def _is_invalid_label(label: str) -> bool:
    """判断 LLM 输出的标签是否为有效的角色名称。"""
    if not label:
        return True
    
    # 角色名合理长度：最长的一般不超过 30 个字符（如 "崩坏：星穹铁道/银狼"）
    if len(label) > 50:
        return True

    lower = label.lower()

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

    # 中文句子特征：句号、感叹号、问号、冒号、破折号等表明这是一段描述而非角色名
    sentence_markers = ['。', '！', '？', '：', '——', '～', '~', '…', '●']
    for m in sentence_markers:
        if m in label:
            return True

    # 长度异常：不超过 50 字符的角色名中出现这些标志
    url_patterns = ['http', 'www.', '.com', '.org', '.cn', '萌娘百科', '维基']
    for u in url_patterns:
        if u in lower:
            return True

    return False


