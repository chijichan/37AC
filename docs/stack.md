# 技术栈

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
| AC 设计系统（自研） | 设计变量 + 组件库（替代原 Pico CSS） |
| Nunito / JetBrains Mono | 自托管可变字体 |
| Phosphor Icons | 图标（自托管 web font） |
| Cropper.js 1.6.2 | 图片裁剪（自托管） |
| @imgly/background-removal 1.7.0 | AI 去背景（ESM 自托管，WASM 模型自托管） |
| Auth.js | JWT 认证模块 |
| EventSource (SSE) | 实时结果推送 |

> 前端页面零外部 CDN 引用，第三方依赖全部本地化于 `src/www/public/static/vendor/`。

### 安全与认证

| 技术 | 用途 |
|------|------|
| JWT | API 身份验证 |
| bcrypt | 密码哈希 |
| CORS | 跨域支持 |

---

