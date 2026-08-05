# config/base.py
"""基础配置 - 训练、节点服务、路径等（从环境变量读取）"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROOT_PATH = Path(__file__).resolve().parent.parent

# ==================== 调试模式 ====================
TSAC_DEBUG = os.getenv("TSAC_DEBUG", "False").lower() == "true"

# ==================== 设备配置 ====================
AUTO_DEVICE = os.getenv("AUTO_DEVICE", "True").lower() == "true"
USE_DIRECTML = os.getenv("USE_DIRECTML", "False").lower() == "true"
DEVICE = None

# ==================== 训练相关配置 ====================
DATASET_DIR = Path(os.getenv("DATASET_DIR", "W:/Img"))

MODEL_DIR = ROOT_PATH / "saves" / "models"
MODEL_PATH = MODEL_DIR / os.getenv("MODEL_FILENAME", "37ac-v0.0.1.pth")
CLASSES_TXT_PATH = MODEL_DIR / "classes.txt"
# 已有模型权重备份目录
MODEL_BAK_DIR = MODEL_DIR / "_bak"

# 是否从已有模型权重继续训练（而非从头 ImageNet 预训练）
RESUME_MODEL_PATH = os.getenv("RESUME_MODEL_PATH", "")
if RESUME_MODEL_PATH:
    RESUME_MODEL_PATH = Path(RESUME_MODEL_PATH)
else:
    RESUME_MODEL_PATH = None  # 默认使用 ImageNet 预训练

NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", "50") or "50")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16") or "16")
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "224") or "224")
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "1e-4") or "1e-4")
# === 分阶段微调（基于 ImageNet 预训练权重） ===
# 阶段1: 冻结 backbone，仅训练 FC + CBAM，高学习率快速拟合头部
PHASE1_EPOCHS = int(os.getenv("PHASE1_EPOCHS", "10") or "10")
PHASE1_LR = float(os.getenv("PHASE1_LR", "1e-3") or "1e-3")
# 阶段2: 解冻全部，低学习率全局精调
PHASE2_LR = float(os.getenv("PHASE2_LR", "1e-4") or "1e-4")
PHASE2_MIN_LR = float(os.getenv("PHASE2_MIN_LR", "1e-6") or "1e-6")
# 单个角色最大训练样本数（YOLO 裁剪保存时生效）
MAX_IMAGES_PER_ROLE = int(os.getenv("MAX_IMAGES_PER_ROLE", "100") or "100")
# 验证集比例（0 表示不使用验证集）
VAL_SPLIT_RATIO = float(os.getenv("VAL_SPLIT_RATIO", "0.2") or "0.2")
# 权重衰减（L2 正则化）
WEIGHT_DECAY = float(os.getenv("WEIGHT_DECAY", "1e-4") or "1e-4")
# 标签平滑
LABEL_SMOOTHING = float(os.getenv("LABEL_SMOOTHING", "0.1") or "0.1")
# 梯度裁剪最大范数
GRAD_CLIP_NORM = float(os.getenv("GRAD_CLIP_NORM", "1.0") or "1.0")
# 早停耐心轮数（0 表示不使用早停）
EARLY_STOP_PATIENCE = int(os.getenv("EARLY_STOP_PATIENCE", "10") or "10")
# DataLoader 工作进程数
NUM_WORKERS = int(os.getenv("NUM_WORKERS", "2") or "2")

# ==================== 预测相关配置 ====================
MODEL_LOAD_PATH = MODEL_PATH

# ==================== 数据集路径配置 ====================
# 原始数据集目录（由 DATASET_DIR 指定，如 W:/Img）
# YOLO 裁剪后的数据集目录（自动生成，不覆盖原图）
CROPPED_DATASET_DIR = ROOT_PATH / "saves" / "dataset"

# ==================== 节点服务配置 ====================
TCP_HOST = os.getenv("TCP_HOST", "127.0.0.1")
TCP_PORT = int(os.getenv("TCP_PORT", "13137"))
LOCAL_PORT = os.getenv("LOCAL_PORT")
if LOCAL_PORT:
    LOCAL_PORT = int(LOCAL_PORT)
else:
    LOCAL_PORT = None  # 默认随机
NODE_ID = int(os.getenv("NODE_ID", "1"))
TOKEN = os.getenv("TOKEN")  # 节点认证Token
HEARTBEAT_INTERVAL_SEC = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "15"))
HEARTBEAT_RESPONSE_TIMEOUT_SEC = int(os.getenv("HEARTBEAT_RESPONSE_TIMEOUT_SEC", "30"))
HEARTBEAT_MISS_LIMIT = int(os.getenv("HEARTBEAT_MISS_LIMIT", "3"))
RECONNECT_DELAY_SEC = int(os.getenv("RECONNECT_DELAY_SEC", "10"))
MAX_TASKS = int(os.getenv("MAX_TASKS", "5"))

# ==================== 第三方大模型（LLM）识别配置 ====================
# 使用多模态大模型（如 DeepSeek、GPT-4V 等）进行图片识别
LLM_RECOGNITION_ENABLED = os.getenv("LLM_RECOGNITION_ENABLED", "False").lower() == "true"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
# API 类型："chat-completions"（OpenAI 兼容格式，默认）/ "ollama"（Ollama 原生格式）
# 注意：os.getenv 在变量存在但为空时返回空串而非默认值，因此用 or 兜底
_LLM_API_TYPE_RAW = (os.getenv("LLM_API_TYPE", "") or "chat-completions").strip().lower()
if _LLM_API_TYPE_RAW in ("openai", "chat", "chat-completions"):
    LLM_API_TYPE = "chat-completions"
else:
    LLM_API_TYPE = _LLM_API_TYPE_RAW
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-v4.1")
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "30"))
# 本地推理超时（秒）：首次加载模型 / YOLO 检测可能较慢，作为安全兜底（后台线程超时自动返回失败）
LOCAL_TASK_TIMEOUT_SEC = int(os.getenv("LOCAL_TASK_TIMEOUT_SEC", "120"))
# 识别提示词模板（默认提示词；.env 中留空时自动使用默认值）
_DEFAULT_LLM_PROMPT = (
    '你是一个 ACG 角色识别专家。\n'
    '输入：一张图片（可能包含 cosplay、手办、插画、截图等）。\n'
    '目标：尽可能准确地识别其中最主要的 ACG 角色。\n'
    '\n'
    '请按以下步骤思考（不要输出思考过程）：\n'
    '1. 提取视觉线索：发色、发型、服装、配饰、武器、特有标志、姿势、场景。\n'
    '2. 与已知角色库进行匹配（覆盖日漫、国漫、游戏、Vtuber等）。\n'
    '3. 给出最佳匹配，并评估可信度（0-100，依据：特征匹配数、特征独特性、遮挡情况）。\n'
    '\n'
    '输出格式（严格 JSON，无 markdown，无注释）：\n'
    '{"label": "作品名/角色名", "confidence": 95, "features_used": ["发色", "服装"], "class_probs": [{"label": "其他可能作品名/角色名", "confidence": 3},{"label": "其他可能作品名/角色名", "confidence": 2}...]}\n'
    '\n'
    '规则：\n'
    '- 若图片包含多个角色，只识别最突出（占画面面积最大或居中的）的那一个。\n'
    '- 若图片模糊、遮挡严重或缺乏足够特征，允许返回 {"label": null, "confidence": 0, "reason": "特征不足"}。\n'
    '- 绝对不要编造特征，置信度必须基于可见证据。\n'
    '- 对于 cosplay 照片，优先识别原作角色，而非现实人物。\n'
    '- 若识别结果为现实人物（非 ACG），需特别标注。\n'
)
# 注意：os.getenv 在变量存在但值为空字符串时返回空串而非默认值，因此用 or 兜底
LLM_PROMPT_TEMPLATE = os.getenv("LLM_PROMPT_TEMPLATE", "") or _DEFAULT_LLM_PROMPT

# ==================== 节点能力配置 ====================
# 节点支持的识别能力列表，自动根据配置推导
# "local" 表示支持本地 YOLO+ResNet 模型推理（始终可用）
# "llm" 表示支持第三方多模态大模型推理
_CAPABILITIES = ["local"]
if LLM_RECOGNITION_ENABLED:
    _CAPABILITIES.append("llm")
CAPABILITIES = json.dumps(_CAPABILITIES, ensure_ascii=False)

# ==================== YOLO 检测配置 ====================
# YOLO（快速定位）+ ResNet（角色分类）技术架构
YOLO_ENABLED = os.getenv("YOLO_ENABLED", "True").lower() == "true"
# 模型名称：yolov8n.pt（nano，最快）/ yolov8s.pt / yolov8m.pt
# 默认放在 saves/models/ 目录下
_DEFAULT_YOLO_MODEL = str((MODEL_DIR / "yolov8n.pt").resolve())
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", _DEFAULT_YOLO_MODEL)
# 检测置信度阈值（低于此值的目标被忽略）
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.25"))

# ==================== 路径配置 ====================
# 暂存
IMAGE_PATH = ROOT_PATH / "saves" / "uploads"
IMAGE_PATH.mkdir(parents=True, exist_ok=True)

# 日志
LOGS_PATH = ROOT_PATH / "saves" / "logs"
LOGS_PATH.mkdir(parents=True, exist_ok=True)

# ==================== 设备自动选择（惰性初始化） ====================
# 首次调用时获取，避免模块导入时加载 torch/torch-directml
_DEVICE_INITIALIZED = False


def get_device():
    """获取计算设备（惰性初始化，首次调用时加载 torch）"""
    global _DEVICE_INITIALIZED, DEVICE
    if _DEVICE_INITIALIZED:
        return DEVICE

    _logger = __import__('logging').getLogger(__name__)

    if AUTO_DEVICE is False:
        DEVICE = "cpu"
    elif USE_DIRECTML:
        try:
            import torch_directml
            DEVICE = torch_directml.device()
            _logger.info("使用 DirectML 设备 (AMD GPU): %s", DEVICE)
        except ImportError:
            _logger.warning("torch-directml 未安装，回退到 CPU")
            DEVICE = "cpu"
        except KeyboardInterrupt:
            raise
        except Exception as e:
            _logger.warning("DirectML 初始化失败: %s，回退到 CPU", e)
            DEVICE = "cpu"
    else:
        import torch
        if torch.cuda.is_available():
            DEVICE = torch.device("cuda")
        else:
            DEVICE = "cpu"

    _DEVICE_INITIALIZED = True
    return DEVICE
