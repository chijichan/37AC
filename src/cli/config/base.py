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
DEVICE = None

# ==================== 训练相关配置 ====================
DATASET_DIR = Path(os.getenv("DATASET_DIR", "W:/Img"))

MODEL_DIR = ROOT_PATH / "saves" / "models"
MODEL_PATH = MODEL_DIR / os.getenv("MODEL_FILENAME", "37ac-v0.0.1.pth")
CLASSES_TXT_PATH = MODEL_DIR / "classes.txt"

NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", "50") or "50")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16") or "16")
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "224") or "224")
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "1e-4") or "1e-4")
# 单个角色最大训练样本数（YOLO 裁剪保存时生效）
MAX_IMAGES_PER_ROLE = int(os.getenv("MAX_IMAGES_PER_ROLE", "100") or "100")

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
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-vl2")
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "30"))
# 识别提示词模板
LLM_PROMPT_TEMPLATE = os.getenv(
    "LLM_PROMPT_TEMPLATE",
    '你只能输出一行 JSON，禁止输出任何其他文字。\n'
    '任务：识别图片中的 ACG 角色。\n'
    '输出格式（严格遵循）：{"label": "作品/角色名", "confidence": 95}\n'
    '规则：\n'
    '- label 写作品和角色名，中日文均可\n'
    '- 完全无法识别时填 "unknown"\n'
    '- confidence 填 0-100 的整数\n'
    '警告：禁止输出描述、分析、评论或任何非 JSON 内容。\n'
    '示例：{"label": "原神/神里绫华", "confidence": 98}'
)

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
IMAGE_PATH.mkdir(exist_ok=True)

# 日志
LOGS_PATH = ROOT_PATH / "saves" / "logs"
LOGS_PATH.mkdir(exist_ok=True)

# ==================== 设备自动选择 ====================
if AUTO_DEVICE is False:
    DEVICE = "cpu"
else:
    import torch

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
