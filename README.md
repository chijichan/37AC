# TAC - 二次元角色识别系统

**TAC**（**T**wo-Dimensional **A**nime **C**haracter recognition）是一个基于深度学习的二次元角色识别系统，支持**模型训练**与**在线预测**，并配套有简洁的 **Flask Web 界面**，方便用户上传图片进行角色识别。

---

## 📦 项目结构
```
TAC/
│
├── TAC/ # 后端核心代码（训练 & 预测脚本）
│ ├── dataset/ # 存放训练用的二次元角色图片数据集（每个角色一个子文件夹）
│ ├── models/ # 保存训练好的模型和类别文件
│ │ ├── character_resnet18.pth # 训练好的 ResNet18 模型
│ │ └── classes.txt # 角色类别名称（每行一个）
│ │
│ ├── anime_character_app.py # 主程序：训练、预测、验证、Web API逻辑
│ ├── anime_character_app.spec # PyInstaller 打包配置（可选）
│ ├── TAC.pyproj # Visual Studio 项目文件
│ │
├── AC_web/ # Flask 前端 Web 界面
│ ├── AC_web/ # Flask 应用主包
│ │ ├── init.py
│ │ ├── views.py # 路由与视图逻辑（含上传预测接口）
│ │ ├── static/ # 静态资源（CSS/JS/图片）
│ │ └── templates/ # HTML 模板（首页、上传页、结果页等）
│ │
│ ├── uploads/ # 用户上传的临时图片存放目录
│ ├── models/ # （符号链接或重复？可与上级共享，建议统一）
│ ├── runserver.py # 启动 Flask 开发服务器
│ ├── AC_web.pyproj # Visual Studio 项目文件
│ │
├── requirements.txt # Python 依赖包列表
├── README.md # 本项目说明文档
│
├── TAC.sln # Visual Studio 解决方案文件
├── TAC.slnLaunch.user # VS 启动配置（用户相关）
```
> 🔧 **注意：**
> - `AC_web/models/` 与 `TAC/models/` 建议**共用同一目录**，避免模型路径混乱。当前代码中 `views.py` 使用的是项目根目录下的 `../models/`，已做适配。
> - 数据集应放在 `TAC/dataset/` 下，每个角色一个子文件夹，文件夹名为角色名，里面放该角色的图片。

---

## 🚀 功能特性

✅ **模型训练**
- 基于 **ResNet18**（可替换），支持自定义数据集训练
- 自动从文件夹结构读取角色类别
- 支持数据校验（检测损坏/异常图片）
- 实时训练日志 + 准确率展示
- 保存最优模型及类别标签文件

✅ **角色预测**
- 支持单张图片的角色识别
- 输出预测角色名称 + 置信度
- 显示各类别概率分布
- 提供交互式命令行菜单

✅ **图片验证工具**
- 检测数据集中的图片是否损坏、格式是否正确、是否能正常解码
- 自动排查问题图片，提升训练稳定性

✅ **Web 在线预测（Flask）**
- 提供简洁友好的 Web 界面
- 支持用户上传图片并实时返回预测结果
- 支持 AJAX 异步请求（适合集成到其他系统）
- 展示预测角色 + 置信度 + 各类别概率

---

## 📂 数据集格式要求

请按如下格式组织你的二次元角色训练数据：
```
TAC/dataset/
├── 角色A/
│ ├── 001.jpg
│ ├── 002.png
│ └── ...
├── 角色B/
│ ├── 001.jpg
│ └── ...
└── ...
```
- 每个子文件夹代表一个角色类别，文件夹名即为角色名（也将作为类别标签）
- 支持 `.jpg`, `.jpeg`, `.png` 格式
- 推荐图片清晰、正面、无遮挡，以提升识别效果

---

## 🛠 技术栈

- **Python 3.x**
- **PyTorch** – 深度学习框架
- **ResNet18** – 主干特征提取网络（可替换）
- **Flask** – 轻量级 Web 框架，用于前端交互
- **PIL / Pillow** – 图像处理
- **torchvision** – 数据加载与图像预处理
- **tqdm** – 进度条工具
- **logging** – 日志记录
- **其他**：numpy, os, io, warnings, hashlib 等标准库

---

## 📥 安装依赖

### 1. 克隆或下载项目代码
bash
git clone https://github.com/chijichan/TAC.git
cd TAC
### 2. 创建 Python 虚拟环境（推荐）
bash
python -m venv venv
Windows
venv\Scripts\activate
macOS/Linux
source venv/bin/activate
### 3. 安装依赖包
bash
pip install -r requirements.txt
> 📌 如果项目根目录下没有 `requirements.txt`，请根据 `anime_character_app.py` 和 `views.py` 中的 import 手动安装，例如：
> ```bash
> pip install torch torchvision flask pillow tqdm
> ```

---

## ▶️ 使用方法

### 一、训练模型

#### 方法1：通过命令行交互菜单（推荐新手）

运行主程序，按提示选择【1】开始训练：
bash
python TAC/anime_character_app.py
按照界面操作：
- 选择 `1` → 训练模型
- 选择 `2` → 进行单张图片预测
- 选择 `3` → 验证数据集图片完整性
- 选择 `0` → 退出

📌 **注意：**
- 训练前请确保 `TAC/dataset/` 目录下已按规范放置好角色图片
- 模型默认保存在：`TAC/models/character_resnet18.pth`
- 类别名保存在：`TAC/models/classes.txt`

#### 方法2：直接调用函数（适合集成或二次开发）

你也可以直接修改 `anime_character_app.py` 脚本，或将其函数导入到其他系统中调用。

---

### 二、启动 Web 界面进行在线预测

#### 1. 启动 Flask 开发服务器

确保你已经训练好模型，并且 `models/character_resnet18.pth` 与 `models/classes.txt` 存在。

然后运行：
bash
python AC_web/runserver.py
🔧 默认配置：
- **HOST**: localhost
- **PORT**: 13137
- **DEBUG**: True

访问：http://localhost:13137 或 http://127.0.0.1:13137

#### 2. 使用 Web 界面
- 打开浏览器访问上述地址
- 点击【上传图片】，选择一张二次元角色图片
- 系统将返回预测的角色名及置信度，并展示各分类概率

> 🖼 支持格式：`.jpg`, `.jpeg`, `.png`
> 
> ⚠ 若提示“预测功能暂不可用”，请检查：
> - 模型文件是否存在
> - `views.py` 中的 `MODEL_PATH` 和 `CLASSES_FILE` 路径是否正确
> - 是否成功训练并生成了模型

---

## 🧪 图片验证（可选）

在训练前，你可以先运行以下功能，检查数据集中是否有损坏/异常图片：
bash
python TAC/anime_character_app.py
然后选择菜单中的 **3. 验证图像文件**，系统会扫描 `TAC/dataset/` 并报告哪些图片有问题。

---

## 📤 模型与类别文件说明

| 文件 | 作用 |
|------|------|
| `models/character_resnet18.pth` | 训练好的神经网络模型参数 |
| `models/classes.txt` | 角色类别名称，每行一个，与模型输出类别顺序对应 |

> ✅ 训练完成后会自动生成这两个文件  
> ❗ 预测时必须保证两者同时存在且路径正确

---

## 🤖 模型替换 / 扩展

目前使用的是 **ResNet18**，如你想更换为 **ResNet34 / ViT / EfficientNet** 等模型，可以修改：

- `anime_character_app.py` 中的模型定义部分
- 对应的 `views.py` 中的模型加载逻辑（如已启用）

> 提示：更换模型后，需重新训练，并确保输入尺寸等预处理与模型输入层匹配。

---

## 📜 文件说明

| 文件/目录 | 描述 |
|----------|------|
| `TAC/dataset/` | 训练数据集，每个角色一个子文件夹 |
| `TAC/models/` | 模型文件与类别文件存储位置 |
| `TAC/anime_character_app.py` | 核心逻辑：训练、预测、验证、命令行 UI |
| `AC_web/` | Flask Web 前端，含上传预测界面 |
| `AC_web/runserver.py` | 启动 Flask 服务 |
| `requirements.txt` | 项目依赖 Python 包 |
| `README.md` | 😊 你正在看的这个文档 |

---

## 📌 注意事项

- 确保你的训练图片质量较高、尽量正面、无遮挡，这样能显著提升模型效果
- 训练数据量越大、角色图片越多，模型效果越好（建议每个角色至少 10~20 张以上）
- 若使用 Web 界面预测，请保证模型文件已训练并正确配置路径
- 推荐使用 GPU 加速神经网络训练

---

## 🛡️ License

本项目目前为 **内部项目 / 示例代码**，未指定具体开源协议。如需用于商业或二次分发，请联系作者确认。

---

## 🙋 联系我们

如有问题、建议或合作意向，欢迎联系：

- 📧 Email: [qijijiang@126.com]
- 🌐 项目地址: [https://github.com/chijichan/TAC]
- 👥 团队: 37AC 二次元技术研究组

---

**Enjoy 二次元角色识别！(≧▽≦) /**