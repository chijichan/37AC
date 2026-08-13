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
from common.constants import IMAGE_EXTENSIONS_BASIC
from utils.image_utils import validate_image_file
from utils.file_utils import load_classes_from_file, check_model_file
from models.character_model import CharacterRecognitionModel
from config.base import (
    IMAGE_SIZE,
    CLASSES_TXT_PATH,
    CLASSES_JSON_PATH,
    MODEL_LOAD_PATH,
    YOLO_ENABLED,
    LLM_RECOGNITION_ENABLED,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_API_TYPE,
    LLM_MODEL_NAME,
    LLM_PROMPT_TEMPLATE,
    LLM_TIMEOUT_SEC,
    LLM_MAX_TOKEN,
    LLM_THINKING,
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


def _default_classes_file() -> str:
    """返回默认类别文件路径：优先 classes.json，否则回退 classes.txt。"""
    try:
        if CLASSES_JSON_PATH.exists():
            return str(CLASSES_JSON_PATH)
    except Exception:
        pass
    return str(CLASSES_TXT_PATH)


def predict_character():
    """交互式预测函数（保持原有功能）"""
    # --- 1. 加载类别 ---
    CLASS_NAMES = load_classes_from_file(_default_classes_file())
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
        if not user_input.lower().endswith(IMAGE_EXTENSIONS_BASIC):
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
        error_msg = result.get("error", "未知错误")
        logger.error("预测失败: %s", error_msg)
        print(f"\n预测失败: {error_msg}")
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
    classes_file = classes_file or _default_classes_file()

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
        # - "chat-completions" → OpenAI 兼容格式 (image_url / max_tokens)【默认】
        # - "responses"        → OpenAI Responses API 格式 (input_image / max_output_tokens)
        # - "anthropic"        → Anthropic Messages API 格式 (image/source / max_tokens)
        # - "ollama"           → Ollama 原生格式 (images / options)
        # LLM_THINKING 控制是否开启模型思考（推理）过程：默认关闭，让模型直接输出结果。
        def _build_payload(prompt: str) -> dict:
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
    """从 LLM API 响应中提取 (label, confidence, features_used, class_probs)。

    兼容四种请求格式对应的响应结构：
    - Ollama /api/chat:      {"message": {"content": "...", "reasoning_content": "..."}}
    - OpenAI 兼容 chat:      {"choices": [{"message": {"content": "...", "reasoning_content": "..."}}]}
    - OpenAI Responses API:  {"output": [{"content": [{"type":"output_text","text":"..."}]}]}
    - Anthropic Messages:    {"content": [{"type":"text","text":"..."}, {"type":"thinking","thinking":"..."}]}
    - 推理模型:              content 可能为 None/空，结论在 reasoning_content / thinking 中

    与 _DEFAULT_LLM_PROMPT 约定的输出结构一致：
    {"label": "作品/角色名", "confidence": 95, "features_used": ["发色", "服装"],
     "class_probs": [{"label": "其他可能作品名/角色名", "confidence": 3}, ...]}
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
                logger.info("[LLM] 从 reasoning_content 提取到 JSON 结论")
            else:
                logger.warning(
                    "[LLM] content 为空且 reasoning 中无有效 JSON 结论，放弃识别"
                )

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

            # 备选角色 → class_probs（与本地模型统一 [{"name", "prob"}] 格式）
            # 提示词约定字段为 "class_probs"（{"label","confidence"}），
            # 兼容旧字段 "alternative_guesses"。
            raw_alts = parsed.get("class_probs")
            if not isinstance(raw_alts, list):
                raw_alts = parsed.get("alternative_guesses")
            if isinstance(raw_alts, list):
                probs = []
                for g in raw_alts:
                    if not isinstance(g, dict):
                        continue
                    # 兼容两种字段命名：提示词用 label/confidence，本地统一用 name/prob
                    name = str(g.get("label") or g.get("name") or "").strip()
                    if not name:
                        continue
                    # 与主 label 一致，确保「作品/角色」顺序
                    name = _normalize_label_order(name)
                    # 跳过提示词占位符条目（如 "作品名/角色名"）
                    if _is_placeholder_label(name):
                        continue
                    prob = float(g.get("confidence", g.get("prob", 0)) or 0)
                    probs.append({"name": name, "prob": prob})
                class_probs = probs

            if not label:
                reason = parsed.get("reason")
                logger.info("[LLM] 模型判定特征不足: %s", reason or "无原因说明")
        else:
            # 降级：纯文本作为标签
            label = content
            confidence = 95.0

        # 确保「作品/角色」顺序（模型偶尔会写成「角色/作品」）
        label = _normalize_label_order(label)

        # 过滤非角色标签（安全审查、拒绝回答等）
        if _is_invalid_label(label):
            logger.warning("[LLM] 过滤无效标签: %s", label)
            return ("", 0.0, [], [])

        return label, confidence, features_used, class_probs

    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.error("[LLM] 无法解析 API 响应: %s, 错误: %s", resp_data, e)
        return ("", 0.0, [], [])


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


