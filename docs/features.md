# 可选功能

- CLI 图片校验：`python src/cli/main.py dataset verify`
- 单张命令行预测：`python src/cli/main.py predict --image <图片路径>`
- LLM 识别：`python src/cli/main.py predict --llm`
- 环境检查：`python verify_env.py`

### 运行测试

确保已安装测试依赖：

```bash
pip install -r tests/requirements-test.txt
```

> ⚠️ **注意**：CLI 与 Server 各自拥有独立的 `config` 包，不能在同一个 Python 进程中共存。
> 必须**分目录运行**测试：

```bash
# CLI 模块测试（89 个）
pytest tests/cli/

# 服务端模块测试（94 个）
pytest tests/server/
```

指定测试文件：

```bash
pytest tests/cli/test_file_utils.py

# 带覆盖率报告
pytest --cov=src --cov-report=html
```

测试覆盖范围：

| 模块 | 覆盖内容 |
|------|---------|
| CLI 配置 | 环境变量读取、默认值、特性开关、节点配置、能力列表 |
| 文件工具 | 哈希计算、目录创建、类别文件读写、模型文件检查 |
| 图片工具 | 有效/损坏/非图片文件验证、尺寸检查、色彩模式转换 |
| 数据集验证 | IP/角色两级目录结构、隐藏目录跳过、无效图片检测 |
| 角色模型 | 模型构建、前向传播、冻结/解冻、保存/加载、类别数变化兼容 |
| 数据集加载 | IPRoleImageFolder 的类别映射、样本索引、隐藏目录过滤 |
| 训练器 | 标签平滑损失、数据集拆分、模型备份、函数签名 |
| 预测器 | 参数校验、图片预处理、结果展示、模型缓存逻辑 |
| 日志系统 | 日志级别、处理器配置、传播控制 |
| 验证器 | 邮箱/用户名/密码格式验证 |
| JWT 工具 | 令牌生成、解码、过期检测、篡改检测 |
| 密码服务 | 哈希、验证、密码修改、弱密码拒绝 |
| 认证服务 | 注册/登录/令牌刷新、重复用户/禁用账号/令牌类型检查 |
| 用户服务 | 用户查询、资料更新、列表分页 |
| API 密钥 | 创建/查询/哈希、权限校验、密钥格式 |
| 限流中间件 | 滑动窗口结构、禁用开关、装饰器封装 |
| SSE 事件总线 | 订阅/发布/取消、多订阅者、超时处理、JSON 序列化 |
| 认证中间件 | 令牌提取、登录/管理员装饰器、refresh token 拒绝 |

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

#### 角色档案（features_used / tags）

训练结束后可用 LLM 为每个角色生成**视觉特征**（`features_used`，如 `["青色头发", "双马尾"]`）与**标签**（`tags`，如 `["长发", "女性角色", "偶像风"]`），写入 `classes.json`：

```env
# 训练结束后为每个角色生成 features_used / tags（需同时启用 LLM 识别，按角色逐个调用 API）
LLM_ENRICH_FEATURES=true
```

生成的 `classes.json` 条目形如：

```json
"Piapro_Characters/初音未来": {
  "id": "初音未来",
  "ip": "Piapro_Characters",
  "name_zh": "初音未来",
  "features_used": ["青色头发", "双马尾"],
  "tags": ["长发", "绿发", "金瞳", "女性角色", "偶像风", "连衣裙"]
}
```

已生成档案的角色会被跳过（不重复消耗 API）。

#### 实验性：基于角色数据库的 LLM 识别

启用后，LLM 识别请求会把 `classes.json` 中已知角色的特征/标签附加到提示词，让大模型**对照角色数据库**匹配识别：

```env
LLM_DB_RECOGNITION=true
```

> 实验性功能：需先通过 `LLM_ENRICH_FEATURES=true` 训练生成角色档案；角色较多时提示词会变长，注意模型上下文限制。

### 前端上传页功能

上传页（`/upload`）支持：

- **本地上传**：点击选择或拖拽（JPG/PNG，最大 10MB），选择后立即显示预览
- **链接上传**：粘贴图片 URL 直接加载（走相同的处理流程）
- **图片处理**（可选）：手动框选裁剪（Cropper.js，粉色主题适配）/ 自动裁剪（YOLO）；AI 去背景（imgly + onnxruntime，WASM 模型自托管）
- **流式识别**：经 PHP 代理 `/api/upload` SSE 透传，实时显示上传/排队/识别进度
  - 排队时显示预计重试倒计时（"约 X 秒后自动重试，节点上线即分发"）
  - SSE 等待超时按识别方式动态计算（local 约 3 分钟 / LLM 约 7 分钟），超时友好提示而非误报失败
  - 结果含置信度条与识别来源徽章（本地模型 / 大模型）

---
