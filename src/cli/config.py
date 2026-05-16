# config.py

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).resolve().parent / ".env")

ROOT_PATH = Path(__file__).resolve().parent

# 设备配置（从环境变量读取）
AUTO_DEVICE = os.getenv("AUTO_DEVICE", "True").lower() == "true"
DEVICE = None

# 训练相关配置（从环境变量读取）
DATASET_DIR = Path(os.getenv("DATASET_DIR", "W:/Img"))

MODEL_SAVE_PATH = ROOT_PATH / "saves" / "models" / "character_resnet18.pth"  # 模型
CLASSES_TXT_PATH = ROOT_PATH / "saves" / "models" / "classes.txt"  # 类别名

NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", "50"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "224"))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "1e-4"))

# 预测相关配置
MODEL_LOAD_PATH = ROOT_PATH / "saves" / "models" / "character_resnet18.pth"  # 模型文件

# 节点服务配置（从环境变量读取）
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

# 暂存
IMAGE_PATH = ROOT_PATH / "saves" / "uploads"
IMAGE_PATH.mkdir(exist_ok=True)

# 日志
LOGS_PATH = ROOT_PATH / "saves" / "logs"
LOGS_PATH.mkdir(exist_ok=True)

if AUTO_DEVICE == False:
    DEVICE = "cpu"
else:
    import torch

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

import logging

logging.info(f"使用设备: {DEVICE}")
