# 37AC 二次元美少女识别系统

<div align="center">

**37AC**（**A**nime **C**haracter recognition）—— 一个基于深度学习的分布式二次元角色识别系统。

![Python](https://img.shields.io/badge/Python-3.9-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0-orange)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![PHP](https://img.shields.io/badge/PHP-7+-purple)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)
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
  - [训练模型](#一训练模型)
  - [启动 Flask 服务端](#二启动-flask-服务端)
  - [启动 PHP 仪表盘](#三启动-php-仪表盘)
  - [启动边缘节点](#四启动边缘节点)
- [通信协议规范](#通信协议规范)
- [访问方式](#访问方式)
- [可选功能](#可选功能)
- [注意事项](#注意事项)
- [License](#license)
- [联系我们](#联系我们)

---

## 项目概述

**37AC** 是一个采用 **分布式 C/S 架构** 的二次元角色识别系统，支持 **模型训练**、**在线预测** 和 **多节点并行推理**。系统由四个核心部分组成：

- **训练客户端** — 基于 PyTorch 和 ResNet18 训练角色识别模型
- **Flask 服务端** — 提供 Web API、TCP 服务、节点管理和任务分发
- **PHP Web 应用** — 现代风格的管理仪表盘，支持用户认证与系统监控
- **边缘推理节点** — 负责实际模型推理，支持多节点并行处理

---

## 系统架构

```
+-------------------------------------------------------+
|                    用户 / 浏览器                        |
+------------------+----------------------+-------------+
                   |   HTTP/API          |   HTTP
                   v                     v
        +-------------------+  +---------------------+
        |   Flask 服务端     |  |  PHP Web 仪表盘      |
        |  (端口 13138)      |  |  (端口 8000)         |
        |  API + 静态页面     |  |  MVC 架构            |
        +----------+--------+  +---------------------+
                   | TCP (端口 13137)
                   v
        +-------------------------------------------+
        |            TCP 服务 (Node Manager)          |
        |   节点注册 . 心跳检测 . 任务分发 . 结果回传    |
        +----------+----------+----------+-----------+
                   |          |          |
        +----------+ +--------+ +--------+----------+
        | 节点 1    | | 节点 2  | | 节点 N            |
        | 推理服务   | | 推理服务 | | 推理服务           |
        +-----------+ +---------+ +------------------+
```

---

## 功能特性

### 模型训练与预测
- 基于 **ResNet18** 的深度学习模型，支持从文件夹自动读取角色类别
- 支持数据校验，自动排查损坏/异常图片，提升训练稳定性
- 实时显示训练进度、损失值与准确率
- 自动保存最佳模型权重（`character_resnet18.pth`）与类别映射文件（`classes.txt`）

### Web 在线角色识别
- 提供直观的 **Flask Web 界面** 和 **PHP 仪表盘** 双前端
- 支持 **拖放 / 点击上传图片**
- 图片限制：格式 **JPG / JPEG / PNG**，最大 **10MB**
- 支持 **异步推理**：上传后自动分发任务至边缘节点，轮询获取推理结果
- 展示识别结果：**角色名称、置信度、各类别概率分布（含可视化进度条）**

### 分布式边缘推理
- 用户上传的图片由 **Flask 后端通过 TCP 分发至边缘节点**
- 边缘节点负责实际模型推理，减轻中心服务器压力
- 支持 **节点注册、心跳检测、任务派发、结果回传**
- 动态负载均衡：自动选择空闲节点，支持任务并发处理
- 推理结果保存至 **MySQL**，支持历史查询

### 现代管理仪表盘
- 基于 **Pico CSS 2** 的响应式设计，支持移动端和桌面端
- 用户注册、登录、密码找回等完整认证系统
- 节点状态监控：在线/离线状态、任务负载、地址信息
- API Key 管理：生成、启用/禁用、删除
- 推理历史查询与统计
- 系统设置与配置管理

### 图片安全与健壮性
- 前端限制上传类型与大小，防止非法文件上传
- 后端严格区分 **文本消息（JSON 控制指令）** 与 **二进制数据（图片）**
- 支持图片格式校验、大小限制、错误提示、任务状态追踪
- 任务失败自动重试机制（最多 3 次）

---

## 项目结构

```
37AC/
+-- src/                           # 源代码目录
|   +-- cli/                       # 命令行客户端（边缘节点）
|   |   +-- main.py                # 主入口程序（交互式菜单 + CLI 参数）
|   |   +-- config.py              # 训练/推理配置文件
|   |   +-- data/
|   |   |   +-- dataset.py         # 自定义数据集加载器
|   |   +-- models/
|   |   |   +-- character_model.py # ResNet18 角色识别模型定义
|   |   +-- training/
|   |   |   +-- trainer.py         # 模型训练逻辑
|   |   +-- prediction/
|   |   |   +-- predictor.py       # 图片推理/预测
|   |   +-- services/
|   |   |   +-- node_service.py    # TCP 客户端（连接中心服务器）
|   |   |   +-- menu_service.py    # 交互式菜单服务
|   |   +-- utils/
|   |   |   +-- file_utils.py      # 文件工具函数
|   |   |   +-- image_utils.py     # 图片处理工具
|   |   |   +-- validation_utils.py# 数据验证工具
|   |   +-- requirements.txt       # CLI 依赖
|   |   +-- saves/                 # 模型/日志保存目录
|   |
|   +-- server/                    # Flask 服务端
|   |   +-- runserver.py           # 服务启动入口
|   |   +-- requirements.txt       # 服务端依赖
|   |   +-- AC_web/                # Flask Web 应用包
|   |   |   +-- __init__.py        # Flask 应用初始化 + CORS + 蓝图注册
|   |   |   +-- config/            # 配置模块
|   |   |   |   +-- __init__.py
|   |   |   |   +-- base.py        # 基础配置（数据库、端口、JWT）
|   |   |   |   +-- email_config.py# 邮件配置
|   |   |   |   +-- log_config.py  # 日志配置
|   |   |   +-- routes/            # API 路由蓝图
|   |   |   |   +-- __init__.py
|   |   |   |   +-- admin_routes.py# 管理员接口
|   |   |   |   +-- api_key_routes.py # API Key 管理
|   |   |   |   +-- auth_routes.py # 用户认证
|   |   |   |   +-- dashboard_routes.py # 仪表盘数据
|   |   |   |   +-- node_routes.py # 节点管理
|   |   |   |   +-- upload_routes.py # 图片上传/推理
|   |   |   |   +-- user_routes.py # 用户管理
|   |   |   +-- middleware/        # 中间件
|   |   |   |   +-- auth_middleware.py # JWT 认证中间件
|   |   |   +-- services/          # 服务模块
|   |   |   |   +-- api_key_service.py  # API Key 服务
|   |   |   |   +-- auth_service.py     # 认证服务
|   |   |   |   +-- dashboard_service.py# 仪表盘数据服务
|   |   |   |   +-- email_service.py    # 邮件服务
|   |   |   |   +-- file_service.py     # 文件处理服务
|   |   |   |   +-- tcp_service.py      # TCP 服务（节点管理核心！）
|   |   |   +-- models/            # 数据模型
|   |   |   +-- data/              # 数据处理
|   |   |   +-- utils/             # 工具函数
|   |   +-- saves/                 # 上传文件/日志保存
|   |
|   +-- www/                       # PHP Web 应用（完整 MVC 架构）
|       +-- public/                # 公共入口
|       |   +-- index.php          # 入口文件 + 路由注册
|       |   +-- static/            # 静态资源
|       |       +-- css/pico.min.css
|       |       +-- scripts/       # JavaScript（jQuery, auth 等）
|       |       +-- fonts/
|       |       +-- img/
|       +-- router.php             # 路由引擎
|       +-- controllers/           # 控制器层
|       |   +-- controller.php     # 基类控制器
|       |   +-- home_controller.php# 首页控制器
|       |   +-- auth_controller.php# 认证控制器
|       |   +-- dashboard_controller.php # 仪表盘控制器
|       +-- models/                # 模型层
|       |   +-- user_model.php     # 用户模型
|       +-- views/                 # 视图层
|       |   +-- layout.php         # 主布局模板
|       |   +-- footer.php         # 页脚
|       |   +-- scripts.php        # JS 引用
|       |   +-- home/              # 首页视图
|       |   |   +-- index.php      # 首页
|       |   |   +-- about.php      # 关于我们
|       |   |   +-- contact.php    # 联系我们
|       |   |   +-- upload.php     # 图片上传
|       |   +-- auth/              # 认证视图
|       |   |   +-- login.php
|       |   |   +-- register.php
|       |   |   +-- forgot_password.php
|       |   |   +-- reset_password.php
|       |   +-- dashboard/         # 仪表盘视图
|       |   |   +-- index.php      # 仪表盘首页
|       |   |   +-- layout.php     # 仪表盘布局
|       |   |   +-- overview.php   # 总览
|       |   |   +-- nodes.php      # 节点管理
|       |   |   +-- apikeys.php    # API Key 管理
|       |   |   +-- history.php    # 推理历史
|       |   |   +-- settings.php   # 系统设置
|       |   +-- components/icons/  # SVG 图标组件
|       +-- DASHBOARD.md           # 仪表盘功能说明文档
|       +-- SECURITY.md            # 安全配置文档
|       +-- start-server.bat       # Windows 启动脚本
|
+-- docs/                          # 项目文档
|   +-- 项目结构总结.md             # 项目结构详细分析
+-- scripts/                       # SQL 脚本
|   +-- alter_tables.sql           # 数据库建表/修改脚本
+-- tests/                         # 测试目录
+-- verify_env.py                  # 环境验证脚本
+-- .editorconfig                  # 编辑器配置
+-- .gitattributes                 # Git 属性
+-- .gitignore                     # Git 忽略规则
+-- README.md                      # 项目说明文档（就是本文件！）
```

---

## 数据集格式要求

训练数据应按照以下结构组织，每个子文件夹代表一个角色，文件夹名即为角色类别名：

```
/dataset/
+-- IP-1/              <- 作品/系列文件夹（可选层级）
|   +-- 角色A/         <- 文件夹名为角色名
|   |   +-- 001.jpg
|   |   +-- 002.png
|   |   +-- ...
|   +-- 角色B/
|       +-- 001.jpg
|       +-- ...
+-- IP-2/
|   +-- ...
+-- ...
```

- 支持图片格式：`.jpg`、`.jpeg`、`.png`
- 图片应尽量清晰、正面、无遮挡，以提升识别准确率
- 每个角色建议提供 **至少 100 张图片** 以获得更好效果

---

## 技术栈

### 深度学习与后端
| 技术 | 用途 |
|------|------|
| Python 3.9 | 主要开发语言 |
| PyTorch | 深度学习框架 |
| ResNet18 | 骨干网络（支持替换） |
| Flask | Web 框架，提供 RESTful API |
| PIL / Pillow | 图像处理 |
| torchvision | 数据加载与增强 |
| tqdm | 训练进度条 |

### 数据库与通信
| 技术 | 用途 |
|------|------|
| MySQL 8.0 | 数据持久化（用户/节点/任务/结果） |
| TCP Socket | 中心服务器与边缘节点通信 |
| 自定义协议 | 长度前缀 + JSON/二进制混合协议 |

### Web 前端
| 技术 | 用途 |
|------|------|
| PHP 7+ | 后端脚本语言 |
| Pico CSS 2 | 轻量级响应式 CSS 框架 |
| jQuery 1.10+ | DOM 操作与 AJAX 请求 |

### 安全与认证
| 技术 | 用途 |
|------|------|
| JWT (HS256) | API 认证 |
| bcrypt | 密码哈希 |
| CORS | 跨域资源共享 |

---

## 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/chijichan/37AC.git
cd 37AC
```

### 2. 创建并激活虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 安装 CLI 客户端依赖
pip install -r src/cli/requirements.txt

# 安装服务端依赖
pip install -r src/server/requirements.txt
```

> 你也可以统一安装：
> ```bash
> pip install torch torchvision flask flask-cors pillow tqdm pymysql bcrypt pyjwt
> ```

### 4. 配置数据库

执行 SQL 脚本创建数据库表：

```bash
mysql -u root -p < scripts/alter_tables.sql
```

然后编辑 `src/server/config/base.py`，配置你的数据库连接信息。

### 5. （可选）配置 PHP 环境

如果使用 PHP 仪表盘，需要安装 PHP 7+ 和 Apache，配置虚拟主机指向 `src/www/public/` 目录。

---

## 使用方法

### 一、训练模型

#### 方式 1：交互式菜单
```bash
python src/cli/main.py
```
按菜单提示选择：
- **1** -> 训练模型
- **2** -> 预测角色
- **3** -> 验证图片文件
- **4** -> 启动节点服务
- **0** -> 退出

#### 方式 2：命令行参数
```bash
# 训练模型
python src/cli/main.py --mode 1

# 预测角色
python src/cli/main.py --mode 2

# 验证图片
python src/cli/main.py --mode 3

# 启动节点
python src/cli/main.py --mode 4
```

训练完成后，模型保存在 `src/cli/saves/character_resnet18.pth`，类别文件保存在 `src/cli/saves/classes.txt`。

### 二、启动 Flask 服务端

确保模型文件存在后，启动 Flask 服务：

```bash
python src/server/runserver.py
```

服务将同时启动：
- **Flask Web 服务** -> `http://127.0.0.1:13138`
- **TCP 节点服务** -> `0.0.0.0:13137`

### 三、启动 PHP 仪表盘

**Windows：**
```bash
src/www/start-server.bat
```

**手动启动：**
```bash
cd src/www
php -S 127.0.0.1:8000 -t public/
```

然后访问 `http://127.0.0.1:8000` 即可。

### 四、启动边缘节点

```bash
python src/cli/main.py --mode 4
```

节点启动后将自动连接中心服务器，等待任务分发。

> **启动顺序建议：** Flask 服务端 -> PHP 仪表盘 -> 边缘节点

---

## 通信协议规范

37AC 系统采用 **TCP 协议** 实现推理节点与中心服务之间的通信。支持多种消息类型。

### 接口概述

| 项目 | 说明 |
|------|------|
| 传输协议 | TCP |
| 连接方式 | 长连接（节点主动连接） |
| 文本协议 | JSON 格式，UTF-8 编码 |
| 二进制协议 | 原始字节流（图片 base64 编码嵌入 JSON） |
| 消息边界 | 长度前缀模式（`header@content_length`） |

### 消息类型

| 类型 | 方向 | 协议 | 说明 |
|------|------|------|------|
| register | 节点 -> 服务器 | JSON | 节点注册 |
| register_ack | 服务器 -> 节点 | JSON | 注册确认 |
| heartbeat | 节点 -> 服务器 | JSON | 心跳检测 |
| heartbeat_ack | 服务器 -> 节点 | JSON | 心跳确认 |
| task | 服务器 -> 节点 | JSON (含 base64 图片) | 任务下发 |
| task_result | 节点 -> 服务器 | JSON | 推理结果回传 |

### 错误码规范

```json
{
    "1000": "认证失败",
    "1001": "协议版本不兼容",
    "2000": "任务处理失败",
    "2001": "图片格式错误",
    "3000": "系统内部错误"
}
```

### 超时配置

| 参数 | 值 |
|------|-----|
| 心跳超时 | 60 秒 |
| 任务处理超时 | 300 秒 |
| 最大重试次数 | 3 次 |

---

## 访问方式

| 服务 | 地址 | 说明 |
|------|------|------|
| Flask Web 界面 | http://localhost:13138 | 基础上传/识别页面 |
| PHP 仪表盘 | http://localhost:8000 | 完整管理后台 |
| PHP 仪表盘 | http://localhost:8000/dashboard | 登录后进入仪表盘 |
| API 接口 | http://localhost:13138/api/* | RESTful API |

---

## 可选功能

- **图片校验**：运行 CLI 客户端，选择菜单 **3**，检测数据集中损坏图片
- **单张预测**：命令行交互式预测（菜单选项 **2**）
- **环境验证**：运行 `python verify_env.py` 检查系统环境

---

## 注意事项

- 训练图片建议清晰、正面、无遮挡
- 每个角色建议提供 100+ 图片以获得更高精度
- 推理依赖边缘节点在线，确保 TCP 服务正常运行
- 推荐使用 GPU 加速模型训练与推理
- 生产环境请替换 `base.py` 中的默认密钥和密码
- 首次使用前请确保 MySQL 数据库表结构已创建

---

## License

本项目仅限内部研究使用，禁止商用及二次分发。如需商用或二次分发，请联系作者。

---

## 联系我们

- 邮箱：qijijiang@126.com
- 项目地址：[https://github.com/chijichan/37AC](https://github.com/chijichan/37AC)
- 团队：37AC 二次元技术研究组

---

<div align="center">

**Enjoy 二次元美少女识别！(≧▽≦)/**

</div>
