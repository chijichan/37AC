# TAC - 二次元角色识别系统

**TAC**（**T**wo-Dimensional **A**nime **C**haracter recognition）是一个基于深度学习的二次元角色识别系统，支持**模型训练、在线预测**，并配套有简洁友好的 **Flask Web 界面**，方便用户上传图片进行角色识别。

系统采用**分布式边缘推理节点架构（开发中）**，将推理任务分发至边缘设备执行，有效降低公网服务器压力，提升推理效率与实时性。

---

## 📦 项目结构
TAC/
│
├── TAC/ # 后端核心代码（训练、预测、任务调度、TCP通信）
│ ├── dataset/ # 训练用的二次元角色图片数据集，每个角色一个子文件夹
│ ├── models/ # 保存训练好的模型及类别文件（如 character_resnet18.pth, classes.txt）
│ ├── uploads/ # 用户上传的临时图片（上传后转交给边缘节点处理）
│ ├── anime_character_app.py # 主程序：模型训练、预测、Web API、TCP 任务调度逻辑
│ ├── node_server.py # 边缘节点通信服务：注册、心跳、任务下发、结果接收
│ ├── TAC.pyproj # Visual Studio 项目文件（Windows）
│ ├── anime_character_app.spec # PyInstaller 打包配置（可选）
│ │
├── AC_web/ # Flask 前端 Web 界面
│ ├── AC_web/ # Flask 应用主包
│ │ ├── __init__.py
│ │ ├── views.py # 路由与视图逻辑（上传、任务查询等）
│ │ ├── static/ # 静态资源：CSS / JS / 图片
│ │ └── templates/ # HTML 模板：首页、上传页、结果页
│ ├── uploads/ # 前端用户上传的临时图片（与后端共用或软链）
│ ├── models/ # 模型文件目录（建议与 TAC/models 共用）
│ ├── runserver.py # 启动 Flask 开发服务器
│ ├── tcp_server.py # TCP 服务：管理节点连接、注册、心跳、任务分发、结果接收
│ ├── config.py # 项目配置（数据库、服务端口、TCP 等）
│ ├── AC_web.pyproj # Visual Studio 项目文件
│ │
├── requirements.txt # Python 依赖包列表
├── README.md # 本项目说明文档（即本文件）
│
├── TAC.sln # Visual Studio 解决方案文件
├── TAC.slnLaunch.user # VS 用户启动配置
> 🔧 **注意：**
> - `AC_web/models/` 与 `TAC/models/` **建议共用同一目录**，避免模型路径混乱。当前 `views.py` 已配置为从 `../models/` 加载模型。
> - 上传的图片首先保存在 `uploads/`，随后通过 TCP 转发至边缘节点处理。
> - 所有节点信息、任务状态与推理结果均存储于 MySQL，由 `tcp_server.py` 管理。

---

## 🚀 功能特性

### ✅ 模型训练与预测
- 基于 **ResNet18**（可替换），支持从文件夹自动读取角色类别
- 支持数据校验，自动排查损坏/异常图片，提升训练稳定性
- 实时显示训练进度、指标与准确率
- 保存模型权重（`character_resnet18.pth`）与类别文件（`classes.txt`）

### ✅ Web 在线角色识别
- 提供直观的 **Flask Web 界面**
- 支持 **拖放 / 点击上传图片**
- 自动调用 **Cropper.js** 进行图片裁剪，限制格式为 **JPG / JPEG / PNG**，最大 **10MB**
- 支持 **异步推理**：上传后自动分发任务至边缘节点，轮询获取推理结果
- 展示识别结果：**角色名称、置信度、各类别概率分布（含可视化进度条）**

### ✅ 分布式边缘推理（架构开发中）
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
TAC/dataset/
├── 角色A/
│ ├── 001.jpg
│ ├── 002.png
│ └── ...
├── 角色B/
│ ├── 001.jpg
│ └── ...
└── ...
- 支持图片格式：`.jpg`、`.jpeg`、`.png`
- 图片应尽量清晰、正面、无遮挡，以提升识别准确率
- 每个角色建议提供 **至少 100 张图片** 以获得更好效果

---

## 🧠 TCP 通信协议（节点接口）

TAC 系统采用 **TCP 长连接** 实现边缘推理节点（运行 `node_server.py` 的机器）与中心 Flask 服务（运行 `runserver.py` 的机器）之间的通信。协议支持 **多种消息类型**，包括 **控制指令（JSON 文本）** 与 **任务数据（二进制数据）**，节点与服务器通过 **Socket 长连接** 进行交互。

---

### 📡 一、通信方式

- **协议**：TCP
- **连接方式**：长连接（节点主动连接并保持）
- **编码格式**：
  - **控制消息（如注册、心跳）**：使用 **UTF-8 编码的 JSON 文本**
  - **任务数据（如图片、推理结果）**：使用 **二进制格式（bytes）**，**严禁使用 `decode('utf-8')` 解码！**
- **消息边界**：由具体实现控制（如固定头部、长度前缀或协议解析）

---

### 📨 二、支持的通信消息类型

---

#### 1. 🟢 节点注册（Register）

- **方向**：节点 → 服务器
- **用途**：边缘节点启动后向中心注册，加入任务调度池
- **消息类型**：JSON（文本）
- **请求格式：**
```
json
{
"type": "register",
"token": "你的节点密钥",
"name": "节点名称"
}
- **成功返回：**
json
{
"status": "success",
"message": "节点注册成功"
}
```
---

#### 2. 🟢 节点心跳（Heartbeat）

- **方向**：节点 → 服务器
- **用途**：节点定期发送心跳，维持在线状态
- **消息类型**：JSON（文本）
- **请求格式：**
```
json
{
"type": "heartbeat",
"token": "你的节点密钥"
}
- **成功返回：**
json
{
"status": "success",
"message": "心跳收到"
}
```
---

#### 3. 🟣 任务下发（Task Dispatch）[核心功能]

- **方向**：服务器 → 节点
- **用途**：将用户上传的图片（二进制）及任务 ID 下发给边缘节点进行推理
- **消息类型**：**二进制数据（bytes），不是文本！**
- **数据组成（由实际代码决定，可能包括）：**
  - 任务 ID（字符串）
  - 图片二进制数据（如 JPG / PNG 文件内容）
- **重要提醒：**
  - 图片为原始二进制，**严禁调用 `data.decode('utf-8')`**
  - 节点应直接将接收到的二进制数据保存为图片或输入模型推理
- **说明：** 任务下发协议详见 `tcp_server.py` 与 `node_server.py` 实现

---

#### 4. 🟣 推理结果回传（Result Upload）[核心功能]

- **方向**：节点 → 服务器
- **用途**：节点完成推理后，将结果以 **JSON 文本** 通过 TCP 回传给 Flask 后端
- **消息类型**：JSON（文本）
- **返回格式示例：**
```
json
{
"status": "success",
"task_id": "6093950a-4dab-4289-96ad-ed6eb901700c",
"result": {
"label": "角色A",
"confidence": 96.5,
"class_probs": [
{"name": "角色A", "prob": 96.5},
{"name": "角色B", "prob": 2.1}
]
}
}
```
- **字段说明：**
  - `task_id`: 与任务对应的唯一标识，用于存储结果及前端查询
  - `label`: 推理得到的角色名称
  - `confidence`: 置信度（0~100）
  - `class_probs`: 各类别概率，用于前端展示

---

### ⚠️ 三、重要提醒：文本 vs 二进制

| 数据类型 | 是否能 `decode('utf-8')` | 说明 |
|----------|--------------------------|------|
| ✅ 控制消息（注册、心跳） | ✅ 可以 | 是 JSON 格式文本，编码为 UTF-8 |
| ❌ 图片 / 推理输入 / 二进制任务数据 | ❌ 不能 | 是原始二进制（如 `.jpg` / `.png`），强行解码会导致 `'utf-8' codec can't decode byte 0xff` |
| ✅ 推理结果（回传 JSON） | ✅ 可以 | 是 JSON 文本，需先 `decode('utf-8')` 再 `json.loads()` |

🔒 **核心原则：**
> 收到数据后，若含有 `0xff` 等字节，说明是 **图片或二进制数据，不要解码为文本！**

---

## 🛠 技术栈

- **Python 3.x**
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
git clone https://github.com/chijichan/TAC.git
cd TAC
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
python TAC/anime_character_app.py
- 按提示选择功能：训练 / 预测 / 图片校验 / 退出
- 训练完成后，模型保存在 `TAC/models/character_resnet18.pth`
- 类别文件保存在 `TAC/models/classes.txt`

### 二、启动 Web 界面
确保模型文件存在后，启动 Flask 服务：
bash
python AC_web/runserver.py
- 默认访问地址：`http://localhost:13137`
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
- 🌐 项目地址：[https://github.com/chijichan/TAC](https://github.com/chijichan/TAC)
- 👥 团队：37AC 二次元技术研究组

---

**Enjoy 二次元角色识别！(≧▽≦) /**