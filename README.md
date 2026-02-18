
# 37AC 二次元美少女识别

**37AC**（**A**nime **C**haracter recognition）是一个基于深度学习的二次元角色识别系统，支持**模型训练、在线预测**。

系统采用**C/S架构**，包含服务端和多个边缘推理节点。

---

## 🚀 功能特性

### ✅ 模型训练与预测
- 基于 **ResNet18**，支持从文件夹自动读取角色类别
- 支持数据校验，自动排查损坏/异常图片，提升训练稳定性
- 实时显示训练进度、指标与准确率
- 保存模型权重（`character_resnet18.pth`）与类别文件（`classes.txt`）

### ✅ Web 在线角色识别
- 提供直观的 **Flask Web 界面**
- 支持 **拖放 / 点击上传图片**
- 自动调用 **Cropper.js** 进行图片裁剪，限制格式为 **JPG / JPEG / PNG**，最大 **10MB**
- 支持 **异步推理**：上传后自动分发任务至边缘节点，轮询获取推理结果
- 展示识别结果：**角色名称、置信度、各类别概率分布（含可视化进度条）**

### 分布式边缘推理（开发中）
- 用户上传的图片由 **Flask 后端通过 TCP 转发至边缘节点**
- 边缘节点负责实际模型推理，减轻中心服务器压力
- 支持 **节点注册、心跳检测、任务派发、结果回传**
- 推理结果保存至 **MySQL**，供 Web 前端查询展示

### ✅ 图片安全与健壮性
- 前端限制上传类型与大小，防止非法文件上传
- 后端与 TCP 服务严格区分 **文本消息（如 JSON 控制指令）** 与 **二进制数据（如图片）**，避免 `'utf-8' decode` 错误
- 支持图片格式校验、大小限制、错误提示、任务状态追踪

---

## 📂 数据集格式要求

训练数据应按照以下结构组织，每个子文件夹代表一个角色，文件夹名即为角色类别名：
/dataset/
├── IP-1/
│ ├── 角色A/
│ ├── 001.jpg
│ ├── 002.png
│ └── ...
├── IP-2/
│ ├── 角色B
│ ├── 001.jpg
│ └── ...
└── ...
- 支持图片格式：`.jpg`、`.jpeg`、`.png`
- 图片应尽量清晰、正面、无遮挡，以提升识别准确率
- 每个角色建议提供 **至少 100 张图片** 以获得更好效果

---

## 🔌 37AC 接口规范（v1.0）

37AC 系统采用 **TCP协议** 实现推理节点与中心服务之间的通信。支持多种消息类型，包括控制指令和任务数据。

### 📡 接口概述

- **传输协议**：TCP
- **连接方式**：长连接（节点主动连接）
- **编码方案**：
  - **文本协议**：JSON 格式，UTF-8 编码
  - **二进制协议**：原始字节流
- **消息边界**：长度前缀模式

### 📊 协议分类

#### 🟢 文本协议（JSON格式）
- 节点注册（register）
- 节点心跳（heartbeat）  
- 推理结果回传（RESULT_UPLOAD）

#### 🔵 二进制协议（原始字节）
- 任务下发（TASK_DISPATCH）

---

### 📨 协议消息规范

#### 1. 🟢 节点注册

**请求格式（节点 → 服务器）：**
```json
{
    "type": "register",
    "timestamp": "2024-01-01T12:00:00Z",
    "data": {
        "node_id": "1",
        "token": "your_secret_token",
        "tasks": [],
        "max_tasks": 5,
        "status": "ready"
    }
}
```

**响应格式（服务器 → 节点）：**
```json
{
    "type": "register_ack",
    "timestamp": "2024-01-01T12:00:01Z", 
    "data": {
        "status": "success",
        "message": "节点注册成功",
        "assigned_id": "node_001_v2",
        "heartbeat_interval": 30
    }
}
```

#### 2. 🟢 节点心跳

**请求格式（节点 → 服务器）：**
```json
{
    "type": "heartbeat",
    "timestamp": "2024-01-01T12:00:30Z",
    "data": {
        "node_id": "node_001_v2",
        "token": "your_secret_token", 
        "status": "active",
        "load": 0.65,
        "memory_usage": "45%"
    }
}
```

**响应格式（服务器 → 节点）：**
```json
{
    "type": "heartbeat_ack",
    "timestamp": "2024-01-01T12:00:31Z",
    "data": {
        "status": "success", 
        "message": "心跳确认"
    }
}
```

#### 3. 🔵 任务下发

**请求格式（服务器 → 节点）：**
```json
{
    "type": "task",
    "timestamp": "2024-01-01T12:01:00Z",
    "data": {
        "task_id": "uuid_string",
        "model_type": "resnet18", 
        "priority": "normal"
    }
}
```

#### 4. 🟢 推理结果回传

**响应格式（节点 → 服务器）：**
```json
{
    "type": "task_result",
    "timestamp": "2024-01-01T12:01:00Z",
    "data": {
        "task_id": "6093950a-4dab-4289-96ad-ed6eb901700c",
        "node_id": "node_001_v2",
        "status": "success",
        "result": {
        "label": "春日野穹",
        "confidence": 96.5,
        "inference_time": 125,
        "class_probs": [
            {"name": "春日野穹", "prob": 96.5},
            {"name": "雪之下雪乃", "prob": 2.1},
            {"name": "霞之丘诗羽", "prob": 1.4}
        ]
        },
        "metadata": {
        "model_version": "v1.2.0",
        "hardware": "GPU-NVIDIA-RTX3080"
        }
    }
}
```

### ⚠️ 协议安全与错误处理

#### 安全规则
- 所有文本协议必须包含 `timestamp` 字段
- 敏感数据传输需使用加密通道
- 节点身份验证通过 `token` 字段

#### 错误码规范
```json
{
    "error_codes": {
        "1000": "认证失败",
        "1001": "协议版本不兼容", 
        "2000": "任务处理失败",
        "2001": "图片格式错误",
        "3000": "系统内部错误"
    }
}
```

#### 超时与重试
- 心跳超时：60秒
- 任务处理超时：300秒  
- 最大重试次数：3次

---

### 🛡️ 数据安全规范

#### 文本 vs 二进制数据
| 数据类型 | 解码方式 | 说明 |
|----------|----------|------|
| ✅ JSON 协议 | 需 `decode('utf-8')` | 注册、心跳、结果回传 |
| ❌ 二进制数据 | **禁止** `decode('utf-8')` | 图片、任务数据 |

**核心原则：**
> 接收数据时，检查是否包含无法UTF-8解码的字节（如 `0xff`），如有则按二进制协议处理

---

## 🛠 技术栈

- **Python 3.9**
- **PyTorch** – 深度学习框架
- **ResNet18** – 主干网络（可替换）
- **Flask** – Web 框架，提供 API 与前端交互
- **PIL / Pillow** – 图像处理
- **torchvision** – 数据加载与增强
- **tqdm** – 进度条
- **MySQL** – 任务 / 节点状态存储
- **TCP Socket** – 边缘节点通信
- **其他依赖**：numpy, os, json, logging, hashlib, io 等

---

## 📥 安装与运行

### 1. 克隆项目
bash
git clone https://github.com/chijichan/37AC.git
cd 37AC
### 2. 创建并激活虚拟环境（推荐）
bash
python -m venv venv
Windows:
venv\Scripts\activate
macOS / Linux:
source venv/bin/activate
### 3. 安装依赖
bash
pip install -r requirements.txt
> 📌 若无 `requirements.txt`，请根据项目 import 手动安装，如：
> ```bash
> pip install torch torchvision flask pillow tqdm pymysql
> ```

---

## ▶️ 使用方法

### 一、训练模型
运行主程序，选择菜单选项 **1** 开始训练：
bash
python 37AC/anime_character_app.py
- 按提示选择功能：训练 / 预测 / 图片校验 / 退出
- 训练完成后，模型保存在 `37AC/models/character_resnet18.pth`
- 类别文件保存在 `37AC/models/classes.txt`

### 二、启动 Web 界面
确保模型文件存在后，启动 Flask 服务：
bash
python AC_web/runserver.py
- 默认访问地址：`http://localhost:13138`
- 上传图片，系统自动分发任务至边缘节点，返回推理结果

---

## 🧪 可选功能

- **图片校验**：运行主程序，选择菜单 **3**，检测数据集中损坏图片
- **单张预测**：命令行交互式预测（菜单选项 2）

---

## 📌 注意事项

- 训练图片建议清晰、正面、无遮挡
- 每个角色建议提供 100+ 图片以获得更高精度
- 确保 `views.py` 中的模型路径（`MODEL_PATH`、`CLASSES_FILE`）配置正确
- 推理依赖边缘节点在线，确保 TCP 服务正常运行
- 推荐使用 GPU 加速模型训练与推理

---

## 🛡️ License

本项目仅限内部研究使用，禁止商用及二次分发。如需商用或二次分发，请联系作者。

---

## 🙋 联系我们

- 📧 邮箱：qijijiang@126.com
- 🌐 项目地址：[https://github.com/chijichan/37AC](https://github.com/chijichan/37AC)
- 👥 团队：37AC 二次元技术研究组

---

**Enjoy 二次元美少女识别！(≧▽≦) /**