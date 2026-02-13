# config.py

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent

# import os
# ROOT_PATH = Path(os.path.abspath(__file__)).parent.parent  # 先转成Path对象

AUTO_DEVICE = True
DEVICE = None

# 训练相关配置
DATASET_DIR = Path("E:/pj/TAC_dataset/processed")
# DATASET_DIR = Path("W:/Img")

MODEL_SAVE_PATH = ROOT_PATH / "saves" / "models" / "character_resnet18.pth"  # 模型
CLASSES_TXT_PATH = ROOT_PATH / "saves" / "models" / "classes.txt"  # 类别名

NUM_EPOCHS = 50
BATCH_SIZE = 16  # 16
IMAGE_SIZE = 224  # 224
LEARNING_RATE = 1e-4

# 预测相关配置
MODEL_LOAD_PATH = ROOT_PATH / "saves" / "models" / "character_resnet18.pth"  # 模型文件

# 节点服务配置
TCP_HOST = "154.9.253.170"  # 请根据实际情况设置或从环境变量获取
TCP_PORT = 13137  # 请根据实际情况设置或从环境变量获取
NODE_ID = 1  # 请根据实际情况设置
TOKEN = "a1ce075a-1ddb-430f-912c-747cc90d28fb"  # 请根据实际情况设置
HEARTBEAT_INTERVAL_SEC = 10  # 心跳发送间隔（与线程一致）
HEARTBEAT_RESPONSE_TIMEOUT_SEC = 30  # 超过该时间未收到 heartbeat_ack 则认为超时
HEARTBEAT_MISS_LIMIT = 3  # 允许连续丢失 heartbeat_ack 的最大次数
RECONNECT_DELAY_SEC = 10  # 重连前等待时间（秒）

# 暂存
IMAGE_PATH = ROOT_PATH / "saves" / "uploads"

# 日志
LOGS_PATH = ROOT_PATH / "logs"

# 如果需要确保目录存在，可以添加：
LOGS_PATH.mkdir(exist_ok=True)

if AUTO_DEVICE == False:
    DEVICE = "cpu"
else:
    import torch

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

import logging

logging.info(f"使用设备: {DEVICE}")
