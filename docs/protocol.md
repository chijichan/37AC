# 通信协议规范

### 协议概览

- 协议：`TCP`
- 连接方式：节点主动长连接
- 文本：`JSON` UTF-8
- 图片：Base64 或原始二进制
- 边界：长度前缀模式

### HTTP 识别 API（模型）

- `GET /models`（无鉴权）→ 拉取当前可用的识别模型列表：
  ```json
  { "models": [ { "id": "37ac", "type": "local", "name": "37ac 本地模型" },
                { "id": "llm",   "type": "llm",   "name": "LLM 大模型" } ] }
  ```
  - `37ac` 为本地模型，任何节点默认支持
  - `llm` 是否出现取决于是否有启用 LLM 的在线节点
- `POST /upload` 使用 `model=37ac|llm` 字段选择模型（替代旧的 `recognition_type=local|llm|auto`）
- 支持 `multipart`（`file`/`image`）或 `image_base64`（JSON/表单字段）
- 内部 TCP 任务消息仍用 `recognition_type`（local/llm）表示推理路径

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
    "capabilities": "[\"local\",\"llm\"]",
    "llm_enabled": false,
    "llm_timeout_sec": 30
  }
}
```

- `capabilities`：JSON 数组字符串，声明节点支持的推理能力
  - `["local"]` — 仅支持本地 ResNet 模型（默认）
  - `["local","llm"]` — 同时支持本地模型和第三方多模态大模型
- `llm_enabled` / `llm_timeout_sec`：节点 LLM 能力与推理超时，服务端据此决策任务重试间隔
- 节点 Token 在数据库中仅存 **SHA-256 哈希**（新建节点时由服务端生成或用户自定义）
- 服务端 `NodeManager` 根据 `recognition_type` 匹配具备相应能力的空闲节点，实现智能分发

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

- `recognition_type`：内部推理路径（HTTP 层已由 `model=37ac|llm` 取代，此处为 TCP 内部字段）
  - `local` — 对应 `model=37ac`，使用本地 ResNet 模型
  - `llm` — 对应 `model=llm`，使用第三方多模态大模型 API

### 任务重试机制

任务分发时若无空闲节点，将进入等待队列自动重试：

| 识别方式 | 重试间隔 | 说明 |
|---------|---------|------|
| `local` | 10s | 本地推理快，短间隔快速重试 |
| `llm` | 90s（或节点上报 LLM 超时 +15s） | 大模型推理耗时数秒~数十秒，避免重复分发 |
| `auto` | 10s / 90s | **智能决策**：无在线 LLM 节点时走 10s 快路径，否则 90s 保守 |

- 最大重试次数：`TASK_MAX_RETRIES`（默认 3）
- 等待队列任务在节点上线后自动分发，前端 SSE 实时推送排队状态与预计重试时间

### 错误码

任务结果中的 `result` 字段在出错时包含 `error` 描述。

### 识别结果结构（统一）

全项目只有三种相关结构，规范定义见 `src/common/recognition.py`（CLI/Server 共用），
旧格式（`label`/`confidence`/`probability`/字符串百分比）统一在该模块归一化：

**① 类别对象（Class）** — `classes.json` 条目，类别名 = 整个对象：

```json
"原神/荧": { "id": "荧", "ip": "原神", "name_zh": "荧",
             "features_used": ["金发", "双辫"], "tags": ["长发", "女性角色"] }
```

**② 候选角色项（Candidate）** — `class_probs` 中每一项 = 类别对象 + 排名信息：

```json
{ "name": "原神/荧", "prob": 93.0, "id": "荧", "ip": "原神",
  "name_zh": "荧", "features_used": ["金发", "双辫"], "tags": ["长发", "女性角色"] }
```

**③ 识别结果（Result）** — 推理引擎的统一返回：

```json
{
  "success": true,
  "class_probs": [ Candidate, ... ],
  "image_path": "...",
  "recognition_type": "local" | "llm",
  "error": null,
  "features_used": [...],
  "tags": [...]
}
```

- `name`：唯一标识（`IP/角色`，数据集路径参考 / 模型索引 / JSON 键）
- `prob`：0-100 百分数；`class_probs` 按 `prob` 降序，**第一项即最佳结果**（无顶层 label/confidence）
- `id`/`ip`/`name_zh`/`features_used`/`tags`：存在 `classes.json` 档案时自动附加
- 顶层 `features_used`/`tags` 为 LLM 主结论的冗余快照（本地模型为空）

> `classes.json` 是**类别注册表**（类别对象的唯一存放处），不可删除。

#### LLM 识别置信度：特征/标签交叉计算

启用实验性数据库识别模式（`LLM_DB_RECOGNITION=true`）后，LLM 的单一
`label` + `confidence` 不再作为最终结论，而是把 LLM 提取的 `features_used` / `tags`
与 `classes.json` 中该角色的档案做匹配度计算后**交叉加权**：

```
交叉置信度 = 70% × LLM 置信度 + 30% × 特征/标签匹配度(0-100)
特征/标签匹配度 < 25% 时置信度封顶 45%
```

- 匹配度高 → 置信度基本保留（甚至小幅提升）
- 匹配度低 → 置信度被明显压低，`class_probs` 按交叉后的概率重新排序
- 需先用 `LLM_ENRICH_FEATURES=true` 训练生成角色档案（features_used/tags）

---
