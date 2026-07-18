# 37AC 二次元美少女识别系统

<div align="center">

**37AC**（**A**nime **C**haracter recognition）—— 基于深度学习与分布式推理的二次元角色识别平台。

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.13-orange)
![YOLO](https://img.shields.io/badge/YOLOv8-00CCFF)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![PHP](https://img.shields.io/badge/PHP-7+-purple)
![MySQL](https://img.shields.io/badge/MySQL-5.7-blue)
![License](https://img.shields.io/badge/License-Internal%20Research-red)

</div>

---

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [数据集格式要求](#数据集格式要求)
- [技术栈](#技术栈)
- [安装与运行](#安装与运行)
- [使用方法](#使用方法)
- [通信协议规范](#通信协议规范)
- [访问方式](#访问方式)
- [可选功能](#可选功能)
- [注意事项](#注意事项)
- [License](#license)
- [联系我们](#联系我们)

---

## 项目概述

37AC 是一个基于 **分布式 C/S 架构** 的二次元角色识别系统，支持：

- **模型训练**
- **在线图片识别**
- **多节点并行推理**
- **管理仪表盘与权限控制**

系统主要组成：

- `src/cli/`：训练、预测与边缘节点客户端
- `src/server/`：Flask 服务端、API、节点管理、限流中间件
- `www/`：PHP 仪表盘与前端页面

---

## 系统架构

```mermaid
flowchart TB
    User["用户 / 浏览器"]

    subgraph Server["服务端"]
        direction TB
        Flask["Flask 服务端<br/>端口 13138<br/>API + SSE"]
        PHP["PHP Web 仪表盘<br/>端口 8000<br/>MVC 架构"]
        TCP["TCP 服务<br/>端口 13137<br/>节点管理 · 任务分发"]
    end

    subgraph Nodes["边缘推理节点"]
        N1["节点 1<br/>推理服务"]
        N2["节点 2<br/>推理服务"]
        N3["节点 N<br/>推理服务"]
    end

    User -- HTTP/API --> Flask
    User -- HTTP --> PHP
    Flask -- TCP --> TCP
    TCP --> N1 & N2 & N3
```

---

## 功能特性

### 模型训练与预测
- **YOLO + ResNet** 双阶段架构：YOLOv8 快速定位角色区域，ResNet18 精确分类
- 自动从文件夹读取类别标签
- 支持图片数据校验，排查损坏文件
- 实时展示训练损失与准确率
- 自动保存最佳模型权重与类别映射

### 在线角色识别
- 提供 **Flask 流式API** + **PHP 仪表盘** 双渠道访问
- 支持图片上传、异步推理、结果展示
- 图片格式支持 `.jpg/.jpeg/.png`
- 可视化显示角色置信度与概率分布
- **流式上传**：POST `/upload` 携带 `X-Stream-Response: true` 直接返回 SSE 流，无需二次连接

### 分布式边缘推理
- 中心服务器通过 **TCP** 下发推理任务
- 边缘节点负责模型推理，降低服务器负载
- 包含节点注册、心跳检测、任务派发、结果回传
- 支持并发任务与动态节点调度
- **能力感知分发**：节点注册时声明支持的能力（local/LLM），服务端按识别类型自动匹配
- 结果写入 **MySQL** 数据库，支持历史查询

### 管理仪表盘
- 基于 **Pico CSS 2** 响应式界面
- 支持用户注册、登录、密码找回
- API Key 管理与节点状态监控
- 推理历史与系统设置查看

### 运行安全与稳定性
- 前端限制上传类型与大小
- 后端严格区分 JSON 控制消息与图片数据
- 支持错误提示与任务自动重试
- 推荐生产环境替换默认密钥与密码

---

## 项目结构

```text
37AC/
├─ src/
│  ├─ cli/
│  │  ├─ main.py
│  │  ├─ .env.example
│  │  ├─ config/
│  │  │  ├─ base.py
│  │  │  └─ log_config.py
│  │  ├─ data/dataset.py
│  │  ├─ models/character_model.py
│  │  ├─ training/trainer.py
│  │  ├─ prediction/predictor.py          # 含 LLM API + _parse_llm_response
│  │  ├─ services/
│  │  │  ├─ node_service.py               # TCP 客户端 + 异步 LLM
│  │  │  └─ menu_service.py
│  │  ├─ utils/
│  │  │  ├─ file_utils.py
│  │  │  ├─ image_utils.py
│  │  │  └─ validation_utils.py
│  │  ├─ requirements.txt
│  │  └─ saves/
│  │     ├─ logs/
│  │     └─ models/
│  │        ├─ 37ac-v0.0.1.pth           # 模型权重
│  │        └─ classes.txt                # 类别映射
│  └─ server/
│     ├─ runserver.py
│     ├─ .env.example
│     ├─ requirements.txt
│     ├─ config/
│     │  ├─ base.py
│     │  ├─ email_config.py
│     │  └─ log_config.py
│     ├─ middleware/
│     │  ├─ auth_middleware.py
│     │  └─ rate_limiter.py
│     ├─ routes/                          # 7 个蓝图
│     ├─ services/
│     │  ├─ listen_service.py             # TCP 监听
│     │  ├─ node_manager.py               # 节点管理
│     │  ├─ task_manager.py               # 任务重试（LLM感知）
│     │  ├─ task_dispatcher.py            # 任务分发
│     │  ├─ message_handlers.py           # 消息处理 + SSE 推送
│     │  ├─ sse_bus.py                    # SSE 事件总线
│     │  ├─ async_processor.py            # 异步线程池
│     │  ├─ protocol/json_protocol.py     # JSON 协议
│     │  ├─ auth/                         # 认证工具
│     │  └─ dashboard/                    # 仪表盘服务
│     ├─ AC_web/__init__.py               # Flask 应用初始化
│     └─ saves/
├─ www/
│  ├─ public/index.php
│  ├─ router.php
│  ├─ .env.example
│  ├─ start-server.bat
│  ├─ controllers/
│  ├─ views/
│  │  ├─ home/upload.php                 # 快速/高级模式 + SSE
│  │  ├─ home/about.php
│  │  ├─ home/contact.php
│  │  ├─ dashboard/
│  │  └─ auth/
│  ├─ DASHBOARD.md
│  └─ SECURITY.md
├─ docs/项目结构总结.md
├─ docs/前端规范.md
├─ scripts/alter_tables.sql
└─ verify_env.py
```

> `src/cli/`：训练、预测与节点客户端。  
> `src/server/`：Flask 服务端与节点管理。  
> `www/`：PHP 仪表盘与前端页面。

---

## 数据集格式要求

训练数据目录应按角色分类组织：

```text
dataset/
├─ 作品A/
│  ├─ 角色A/
│  │  ├─ 001.jpg
│  │  └─ 002.png
│  └─ 角色B/
└─ 作品B/
   └─ 角色C/
```

- 支持 `.jpg`、`.jpeg`、`.png`
- 图片应清晰、无遮挡、正面
- 建议每个角色至少 100 张图片

---

## 技术栈

### 深度学习与后端

| 技术 | 用途 |
|------|------|
| Python 3.12 | 开发语言（原生 `str \| None` 联合类型） |
| PyTorch 2.13 | 模型训练与推理 |
| YOLOv8 (Ultralytics 8.4) | 人物快速定位（person 类别检测+裁剪，可选） |
| ResNet18 | 角色分类网络（37AC v0.0.1） |
| torch-directml | AMD GPU 加速 |
| Flask 3.1 | Web/API 框架 |
| Pillow 12.3 | 图像处理 |
| torchvision 0.28 | 数据加载与增强 |
| opencv-python 5.0 | YOLO 依赖与图像处理 |
| tqdm | 训练进度显示 |
| requests | LLM API 调用 |

### 数据库与通信

| 技术 | 用途 |
|------|------|
| MySQL 5.7 | 数据存储 |
| TCP Socket | 中心与节点通信 |
| 自定义协议 | 长度前缀 + JSON/二进制 |

### Web 前端

| 技术 | 用途 |
|------|------|
| PHP 7+ | 仪表盘后端 |
| Pico CSS 2 | 响应式样式 |
| Cropper.js | 图片裁剪 |
| @imgly/background-removal | AI 去背景 |
| Auth.js | JWT 认证模块 |
| EventSource (SSE) | 实时结果推送 |

### 安全与认证

| 技术 | 用途 |
|------|------|
| JWT | API 身份验证 |
| bcrypt | 密码哈希 |
| CORS | 跨域支持 |

---

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/chijichan/37AC.git
cd 37AC
```

### 2. 创建并激活虚拟环境（推荐 Python 3.12）

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r src/cli/requirements.txt
pip install -r src/server/requirements.txt
```

> **AMD GPU (RX 580) 用户**：额外安装 DirectML 加速：
> ```bash
> pip install torch-directml
> # 然后在 .env 中设置 USE_DIRECTML=True
> ```

### 4. 配置数据库

```bash
mysql -u root -p < scripts/alter_tables.sql
```

编辑 `src/server/config/base.py`，配置数据库连接、JWT 密钥等。

也可通过 `src/server/.env` 文件配置（推荐）：

```env
# 服务端配置
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
JWT_SECRET=your-jwt-secret-key-change-this-in-production

# 节点配置（src/cli/.env）
NODE_ID=1
TOKEN=your_node_token
LLM_RECOGNITION_ENABLED=false
LLM_API_KEY=your_api_key
```

### 5. 启动 Flask 服务端

```bash
python src/server/runserver.py
```

## 使用方法

### 1. 训练模型

#### 命令行模式

```bash
# 从头训练（ImageNet 预训练）
python src/cli/main.py --mode 1

# 继续训练（自动使用当前模型权重）
python src/cli/main.py --mode 1 --resume

# 继续训练（指定历史权重文件）
python src/cli/main.py --mode 1 --resume saves/models/37ac_p_2026071315.tar
```

命令行模式下 `--resume` 参数直接决定训练方式，不会弹出交互子菜单。

#### 交互菜单模式

```bash
python src/cli/main.py
```

选择 **1. 训练模型** 后，首先选择训练方式：

```
  选择训练方式
  [1] 从头训练（ImageNet 预训练）
  [2] 继续训练（基于已有权重: 37ac-v0.0.1.pth）
  [0] 返回主菜单
----------------------------------------
请选择 (1/2/0):
```

- **[1] 从头训练** — 从 ImageNet 预训练权重开始，分两阶段微调
- **[2] 继续训练** — 基于已有模型权重继续训练，跳过阶段1，直接全局精调

然后选择数据集：

```
  选择训练数据集
  [1] 原始数据集: W:\Img
  [2] 已裁剪数据集: .../saves/dataset（使用已存在的 YOLO 裁剪结果）
  [3] 使用 YOLO 裁剪原始数据集后训练（从头裁剪，保存到 saves/dataset/）
  [0] 返回主菜单
----------------------------------------
请选择 (1/2/3/0):
```

#### 类别数变化支持

继续训练时自动检测类别数变化：

| 场景 | 处理方式 |
|------|---------|
| 类别数 **不变**（如 88→88） | 全量加载所有权重，包括 fc 分类头 |
| 类别数 **变化**（如 88→100） | 跳过 fc 层，只加载 backbone + CBAM，fc 层随机初始化新分类头 |

新增角色到数据集后直接继续训练即可，无需从头开始。

#### 训练参数

可在 `src/cli/.env` 中配置：
- `MAX_IMAGES_PER_ROLE` — 单个角色最大保留张数（YOLO 裁剪时生效），默认 `100`
- 图片按文件大小降序处理，优先保留高质量大图

#### 自动备份机制

每次训练开始前，系统会自动将当前模型权重和 `classes.txt` 备份到 `saves/models/_bak/` 目录，防止覆盖后无法回退：

```text
saves/models/_bak/
├─ 37ac-v0.0.1_bak_20260716_183000.pth
├─ classes_bak_20260716_183000.txt
├─ 37ac-v0.0.1_bak_20260717_091500.pth
└─ classes_bak_20260717_091500.txt
```

备份文件名包含时间戳，支持多次训练的历史回溯。

#### 训练结果

- `src/cli/saves/models/37ac-v0.0.1.pth`
- `src/cli/saves/models/classes.txt`

### 2. 启动 Flask 服务端

```bash
python src/server/runserver.py
```

默认地址：
- Flask Web：`http://127.0.0.1:13138`
- TCP 节点服务：`0.0.0.0:13137`

### 3. 启动 PHP 仪表盘

```bash
cd www
php -S 127.0.0.1:8000 -t public/
```

或在 Windows 下运行：

```bash
www\start-server.bat
```

访问：`http://127.0.0.1:8000`

### 4. 启动边缘节点

```bash
python src/cli/main.py --mode 4
```

> 推荐启动顺序：Flask 服务端 -> PHP 仪表盘 -> 边缘节点

---

## 通信协议规范

### 协议概览

- 协议：`TCP`
- 连接方式：节点主动长连接
- 文本：`JSON` UTF-8
- 图片：Base64 或原始二进制
- 边界：长度前缀模式

### 核心消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| register | 节点 -> 服务器 | 节点注册（含 capabilities / max_tasks 等元数据） |
| register_ack | 服务器 -> 节点 | 注册确认 |
| heartbeat | 节点 -> 服务器 | 心跳 |
| heartbeat_ack | 服务器 -> 节点 | 心跳确认 |
| task | 服务器 -> 节点 | 推理任务（含 recognition_type） |
| task_result | 节点 -> 服务器 | 结果回传 |

### 注册消息示例

```json
{
  "type": "register",
  "timestamp": 1700000000,
  "data": {
    "node_id": 1,
    "token": "your-node-token",
    "max_tasks": 5,
    "capabilities": "[\"local\",\"llm\"]"
  }
}
```

- `capabilities`：JSON 数组字符串，声明节点支持的推理能力
  - `["local"]` — 仅支持本地 ResNet 模型（默认）
  - `["local","llm"]` — 同时支持本地模型和第三方多模态大模型
- 服务端 `NodeManager.get_idle_node_by_capability()` 根据 `recognition_type` 匹配具备相应能力的空闲节点，实现智能分发

### 任务下发消息示例

```json
{
  "type": "task",
  "timestamp": 1700000000,
  "data": {
    "task_id": "uuid",
    "image_filename": "test.jpg",
    "image_data": "base64_encoded...",
    "recognition_type": "local"
  }
}
```

- `recognition_type`：由服务端根据节点能力自动选择后下发
  - `local` — 使用本地 ResNet 模型
  - `llm` — 使用第三方多模态大模型 API
  - `auto` — 由节点根据自身配置决定

### 错误码

任务结果中的 `result` 字段在出错时包含 `error` 描述。

---

## 访问方式

| 服务 | 地址 |
|------|------|
| Flask Web / API | `http://localhost:13138` |
| PHP 仪表盘 | `http://localhost:8000` |
| 上传流式接口 | `POST http://localhost:13138/upload` (Accept: `text/event-stream`) |
| SSE 结果流 | `GET http://localhost:13138/tasks/<task_id>/stream` |

---

## 可选功能

- CLI 图片校验：`python src/cli/main.py --mode 3`
- 单张命令行预测：`python src/cli/main.py --mode 2`
- 环境检查：`python verify_env.py`

### 第三方大模型（LLM）识别

在 `.env` 中启用 LLM 识别后可获得更精确的识别结果：

```env
LLM_RECOGNITION_ENABLED=true
LLM_API_KEY=your_api_key
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL_NAME=deepseek-v4.1-pro
LLM_TIMEOUT_SEC=30
```

LLM 推理在单独的后台线程中执行，不会阻塞节点的主消息循环。

### 前端识别模式

上传页面支持两种模式：
- **快速模式**：默认使用 `auto` 识别方式（由节点自动选择 local/LLM），一键上传识别
- **高级模式**：可自定义识别方式（local/LLM/auto）和去背景方式（快速Canvas/AI深度学习）

---

## 注意事项

- 请先创建数据库表结构
- 确保 TCP 服务与节点在线
- 生产环境请替换 `base.py` 默认密钥
- 推荐使用 GPU 加速训练与推理
- AMD 用户（RX 580 等）可使用 PyTorch-DirectML 加速：`pip install torch-directml` + `.env` 中设置 `USE_DIRECTML=True`
- YOLO 裁剪模式仅保留 `person` 类别的检测结果，不会保留非 person 图片
- `MAX_IMAGES_PER_ROLE` 控制单个角色最大样本数，超出部分不会被裁剪保存

---

## License

本项目仅限内部研究使用，禁止商用及二次分发。如需商用或二次分发，请联系作者。

---

## 联系我们

- 邮箱：qijijiang@126.com
- 项目地址：<https://github.com/chijichan/37AC>
- 团队：37AC 二次元技术研究组

---

<div align="center">

**Enjoy 二次元美少女识别！(≧▽≦)/**

</div>
