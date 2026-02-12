# config.py

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent

# import os
# ROOT_PATH = Path(os.path.abspath(__file__)).parent.parent  # 先转成Path对象

# 训练相关配置
DATASET_DIR = Path("E:/pj/TAC_dataset/processed")  # 建议也改为Path对象，或者保持字符串

MODEL_SAVE_PATH = ROOT_PATH / "models" / "character_resnet18.pth"  # 模型
CLASSES_TXT_PATH = ROOT_PATH / "models" / "classes.txt"  # 类别名

NUM_EPOCHS = 10
BATCH_SIZE = 16
IMAGE_SIZE = 224
LEARNING_RATE = 1e-4

# 预测相关配置
MODEL_LOAD_PATH = ROOT_PATH / "models" / "character_resnet18.pth"  # 模型文件

# 节点服务配置
TCP_HOST = "154.9.253.170"  # 请根据实际情况设置或从环境变量获取
TCP_PORT = 13137  # 请根据实际情况设置或从环境变量获取
NODE_ID = 1  # 请根据实际情况设置
TOKEN = "a1ce075a-1ddb-430f-912c-747cc90d28fb"  # 请根据实际情况设置
HEARTBEAT_INTERVAL_SEC = 10  # 心跳发送间隔（与线程一致）
HEARTBEAT_RESPONSE_TIMEOUT_SEC = 30  # 超过该时间未收到 heartbeat_ack 则认为超时
HEARTBEAT_MISS_LIMIT = 3  # 允许连续丢失 heartbeat_ack 的最大次数
RECONNECT_DELAY_SEC = 10  # 重连前等待时间（秒）

# 修正日志和数据路径
LOGS_PATH = ROOT_PATH / "logs"
DATA_PATH = ROOT_PATH / "data"

# 如果需要确保目录存在，可以添加：
LOGS_PATH.mkdir(exist_ok=True)
DATA_PATH.mkdir(exist_ok=True)
