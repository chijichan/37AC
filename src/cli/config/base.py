# config/base.py
"""基础配置 - 训练、节点服务、路径等（从环境变量读取）"""

import sys
import json
import os
from pathlib import Path

# 将 src/ 加入 sys.path，使 common 公共包可被导入
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

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
CLASSES_JSON_PATH = MODEL_DIR / "classes.json"
# 模型配置/版本信息（训练时自动生成，供模型管理器同步比对）
MODEL_INFO_PATH = MODEL_DIR / "config.json"
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
# 服务端 HTTP 地址（保留备用；模型同步改走 TCP register_ack）
SERVER_HTTP_URL = os.getenv("SERVER_HTTP_URL", "http://127.0.0.1:13138").rstrip("/")
# 节点选择的识别模型（注册后按 register_ack.data.models 里的该模型同步）
MODEL_ID = os.getenv("MODEL_ID", "37ac")
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
# 训练结束后是否使用 LLM 为每个角色生成 features_used / tags 并写入 classes.json
# （需同时启用 LLM_RECOGNITION_ENABLED；会按角色逐个调用 API，注意成本）
LLM_ENRICH_FEATURES = os.getenv("LLM_ENRICH_FEATURES", "False").lower() == "true"
# 实验性：LLM 识别时把 classes.json 中已知角色的 features_used / tags 附加到提示词，
# 让大模型对照角色数据库匹配识别（需同时启用 LLM_RECOGNITION_ENABLED）
LLM_DB_RECOGNITION = os.getenv("LLM_DB_RECOGNITION", "False").lower() == "true"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
# API 类型：
#   - "chat-completions"  OpenAI 兼容格式（默认，兼容 openai/chat）
#   - "responses"         OpenAI Responses API 格式（gpt-5 等新模型）
#   - "anthropic"         Anthropic Messages API 格式（claude）
#   - "ollama"            Ollama 原生格式
# 注意：os.getenv 在变量存在但为空时返回空串而非默认值，因此用 or 兜底
_LLM_API_TYPE_RAW = (os.getenv("LLM_API_TYPE", "") or "chat-completions").strip().lower()
if _LLM_API_TYPE_RAW in ("openai", "chat", "chat-completions"):
    LLM_API_TYPE = "chat-completions"
elif _LLM_API_TYPE_RAW in ("anthropic", "claude", "anthropic-messages"):
    LLM_API_TYPE = "anthropic"
else:
    LLM_API_TYPE = _LLM_API_TYPE_RAW
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-v4.1")
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "30"))
# 单次 LLM 推理的最大输出 token 数（推理模型思考+结论所需，默认 2048）
LLM_MAX_TOKEN = int(os.getenv("LLM_MAX_TOKEN", "2048"))
# 是否开启模型思考（推理）模式：True=开启推理过程（适合 DeepSeek R1 / QwQ / o1 等），
# False=关闭思考（默认，让模型直接输出结果，更快更稳）。注意：部分模型不支持关闭思考。
LLM_THINKING = os.getenv("LLM_THINKING", "False").lower() == "true"
# 本地推理超时（秒）：首次加载模型 / YOLO 检测可能较慢，作为安全兜底（后台线程超时自动返回失败）
LOCAL_TASK_TIMEOUT_SEC = int(os.getenv("LOCAL_TASK_TIMEOUT_SEC", "120"))
# 识别提示词模板（默认提示词；.env 中留空时自动使用默认值）
_DEFAULT_LLM_PROMPT = (
    '你是一个专业的 ACG 角色图像识别专家，负责识别图片中的动漫、漫画、游戏、Vtuber、虚拟角色。'
    '\n'
    '你的任务是根据图片中的视觉证据，准确判断主要角色身份，并生成结构化 JSON 数据。'
    '\n'

    '【输入说明】\n'
    '输入：一张图片。\n'
    '图片类型可能包括：\n'
    '- 动画截图\n'
    '- 游戏截图\n'
    '- 官方角色立绘\n'
    '- 同人插画\n'
    '- cosplay 照片\n'
    '- 手办模型\n'
    '- 表情包或二创图片\n'
    '\n'

    '【核心目标】\n'
    '识别图片中最主要的 ACG 角色。\n'
    '如果无法可靠识别，不允许强行猜测。'
    '\n'

    '【内部分析流程（禁止输出分析过程）】\n'
    '请在内部完成以下步骤：\n'
    '\n'
    '1. 提取视觉特征：\n'
    '- 发色\n'
    '- 发型\n'
    '- 瞳色\n'
    '- 性别外观特征\n'
    '- 服装款式\n'
    '- 服装颜色\n'
    '- 制服、盔甲、礼服等设计\n'
    '- 武器、道具、装备\n'
    '- 特殊标志（角、尾巴、翅膀、徽章、纹身、饰品等）\n'
    '- 场景、UI、字幕、游戏界面元素\n'
    '- 作品画风和时代特征\n'
    '\n'

    '2. 根据视觉特征匹配已知 ACG 角色。\n'
    '\n'

    '3. 判断匹配可靠性：\n'
    '- 独特角色标志越多，可信度越高。\n'
    '- 普通外貌特征（例如黑发、白发、制服）不能作为主要依据。\n'
    '- 不允许仅凭相似脸型或发色确定角色。\n'
    '\n'

    '4. 选择最佳结果：\n'
    '- 优先选择拥有最多独特视觉证据支持的角色。\n'
    '- 如果多个角色相似，降低 confidence，并输出候选列表。\n'
    '- 如果证据不足，返回未知。'
    '\n'

    '【识别优先级】\n'
    '按照以下重要程度判断：\n'
    '角色专属标志 > 独特服装 > 武器道具 > 发型发色 > 普通外貌 > 场景背景。\n'
    '\n'

    '【输出格式】\n'
    '必须严格输出 JSON。\n'
    '禁止输出 markdown。\n'
    '禁止输出解释文字。\n'
    '禁止输出思考过程。\n'
    '\n'
    '【最终回答规则（最高优先级）】\n'
    '你的内部推理过程会被系统单独处理，绝不会作为答案返回。\n'
    '因此最终回答中：\n'
    '- 不要输出分析过程、推理过程、候选思考、猜测讨论。\n'
    '- 不要出现"应该是"、"可能是"、"选择最佳结果"、"我判断"等引导词。\n'
    '- 最终输出必须从 { 开始，到 } 结束，中间只能有 JSON，不能有任何其他字符。\n'
    '\n'
    '禁止在 JSON 前后添加：\n'
    '- 前置文字或说明\n'
    '- 后置文字或补充\n'
    '- Markdown 代码块（```json ... ```）\n'
    '- 任何解释或注释\n'
    '\n'

    '{\n'
    '  "label": "作品名/角色名",\n'
    '  "confidence": 95,\n'
    '  "features_used": ['
    '"银发",'
    '"黑色制服",'
    '"特殊武器"'
    '],\n'
    '  "tags": ['
    '"银发",'
    '"长发",'
    '"女性角色"'
    '],\n'
    '  "class_probs": [\n'
    '    {\n'
    '      "label": "作品名/角色名",\n'
    '      "confidence": 80\n'
    '    },\n'
    '    {\n'
    '      "label": "作品名/角色名",\n'
    '      "confidence": 15\n'
    '    }\n'
    '  ]\n'
    '}'
    '\n'

    '【label 字段规则（最高优先级）】\n'
    'label 必须严格使用以下格式：\n'
    '\n'
    '作品名/角色名\n'
    '\n'
    '斜杠 "/" 前必须是作品/IP名称。\n'
    '斜杠 "/" 后必须是具体角色名称。\n'
    '绝对禁止角色名在前、作品名在后的形式。'
    '\n'

    '正确示例：\n'
    '- 原神/雷电将军\n'
    '- 崩坏：星穹铁道/银狼\n'
    '- VOCALOID/初音未来\n'
    '- 艾尔登法环/梅琳娜\n'
    '\n'

    '错误示例：\n'
    '- 雷电将军/原神\n'
    '- 银狼/崩坏：星穹铁道\n'
    '- 初音未来/VOCALOID\n'
    '\n'

    '生成 label 时必须遵循：\n'
    '先确定角色名称 → 再确定所属作品 → 最后组合为作品名/角色名。'
    '\n'

    '【未知情况处理（禁止输出未知）】\n'
    '以下情况绝对禁止：\n'
    '- 禁止返回 "未知作品/角色名"、"作品名/未知角色"、"未知作品/未知角色"。\n'
    '- 禁止返回 {"label": null, "confidence": 0}。\n'
    '\n'
    '即使无法完全确定，也必须给出一个最可能的猜测：\n'
    '- 不确定作品名时，推测最接近的候选作品（可大胆猜测，不用 "未知"）。\n'
    '- 不确定角色名时，选择外观最相似的具体角色（禁止用 "未知角色"）。\n'
    '- 不确定性越高，confidence 越低（如 40-70），但必须给出具体角色名。\n'
    '- 哪怕只有微弱线索，也要猜一个最接近的角色，而不是放弃。\n'
    '\n'

    '【特殊图片处理规则】\n'
    '\n'
    '多角色图片：\n'
    '- 只识别主体角色。\n'
    '- 主体判断依据：面积最大、中心位置、最清晰角色。\n'
    '\n'

    'cosplay 图片：\n'
    '- 识别 cosplay 对应的 ACG 角色。\n'
    '- 不识别现实 coser 姓名。\n'
    '- 不输出摄影师或模特信息。\n'
    '\n'

    '手办图片：\n'
    '- 识别角色名称。\n'
    '- 不识别商品名称、厂商名称、价格信息。\n'
    '\n'

    '同人图：\n'
    '- 识别原始角色。\n'
    '- 不把画师原创改造设定当成新角色。\n'
    '\n'

    '现实人物：\n'
    '- 如果确认不是 ACG 角色：\n'
    '  label 使用 "现实人物/未知"\n'
    '  confidence 降低。\n'
    '\n'

    '【confidence 标准】\n'
    '90-100：多个独特特征完全匹配，基本确定。\n'
    '70-89：主要特征匹配，但存在少量不确定。\n'
    '40-69：部分特征匹配，有多个可能角色。\n'
    '1-39：低可信猜测。\n'
    '0：无法识别。\n'
    '\n'

    '【class_probs 规则】\n'
    '- 返回 1~3 个候选（至少 1 个，禁止空数组）。\n'
    '- 第一个候选即主 label；其余为其他可能角色。\n'
    '- 候选应尽量来自【不同作品/IP】，发散思考，不要都集中在同一作品内（例如不要全是《原神》的不同角色）。\n'
    '- 即使不确定，也必须给出至少 1 个最接近的具体角色猜测。\n'
    '- confidence 表示相对可能性，总和约等于 100。'
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
