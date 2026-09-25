# 37AC HTTP 接口清单与规范审计

> 范围：`src/server`（Flask 应用 `AC_web`）对外暴露的全部 HTTP 接口。
> 规模：**49 个接口操作 / 48 条路由**（不含 `/static`），由 **46 个处理函数**提供，其中
> `/dashboard/summary|overview`、`/dashboard/tasks|history` 是别名，`/upload` 的 GET/POST 共用一个函数。
> 实测：2026-09-13，`http://127.0.0.1:13138`（Flask 直连）；nginx `:8000` 只服务 PHP 站点，**未反代 API**。
> 机器可读版本：[`docs/openapi.yaml`](openapi.yaml)（OpenAPI 3.0.3，Apifox 可直接导入）。

## 0. 导入 Apifox 的最短路径

| 步骤 | 做法 |
|---|---|
| 1 | Apifox → 项目设置 → **导入数据 → OpenAPI/Swagger** → 选 `docs/openapi.yaml` |
| 2 | 环境变量：`baseUrl = http://127.0.0.1:13138`（部署时换实际地址） |
| 3 | 取 Bearer Token：`POST /auth/login`（body `{username,password}`）→ `data.access_token`；在 Apifox 里配「Bearer Token」鉴权并引用环境变量 |
| 4 | 取 API Key：管理员 `POST /api-keys`（`{name,permission,max_usage}`）→ `data.key`，**只在创建时返回一次**，同样存环境变量 |
| 5 | 无需鉴权：`GET /models`、`GET /upload` |

## 1. 全局约定（现状）

| 项 | 现状 |
|---|---|
| Base URL | `http://127.0.0.1:13138`（`WEB_HOST`/`WEB_PORT`，默认仅监听 127.0.0.1） |
| 内容类型 | 请求 `application/json`（`/models` 写接口兼容 `form`，`/upload` 用 `multipart`）；响应 `application/json`，SSE 端点为 `text/event-stream` |
| 鉴权 ① | `Authorization: Bearer <JWT>`：`/users/*`、`/api-keys*`、`/nodes*`、`/dashboard/*`、`/models` 写接口、`/admin/*` |
| 鉴权 ② | `X-API-Key: 37ac_xxx`：`POST /upload`、`GET /tasks/*` |
| 鉴权 ③ | body `{"api_key": "..."}`：`POST /api-keys/verify`（供内部服务调用） |
| 限流 | **仅** `POST /upload`：默认 5 次/1 秒（滑动窗口，按客户端 IP）；超限 429，**无 `Retry-After` 头** |
| CORS | `ALLOWED_ORIGINS=*` |
| 维护模式 | `settings.maintenance_mode=1` 时，除 `/auth`、`/admin`、`/static`、`OPTIONS` 和「持有有效管理员令牌」的请求外，一律 `503 {"maintenance": true}` |
| 响应信封 | 仍然**三种并存**（见 §3.2），但已做灰度收口：所有 JSON 响应都会**补上** `success` 与 `code`，旧字段一个不动 |
| 错误语义 | 中文 `message` + **机器可读 `code`**（2026-09-13 新增，见 §1.1） |

### 1.1 统一信封与错误码（2026-09-13 新增，灰度）

规则：**只加字段，不改字段**。任何 JSON 响应都会带上
- `success`：布尔。原本就有则保持原值；B/C 形态按 HTTP 状态码补（2xx → true）。
- `code`：机器可读字符串。优先取端点显式指定的值，否则按状态码推导。
- `message`：B/C 形态如果没有 `message` 但有 `error`，用 `error` 的值补一份。

Werkzeug 默认的 HTML 错误页（404/405/413/500…）也换成了同款 JSON 信封（含 `code`）。

| HTTP | 默认 code |
|---|---|
| 200 / 201 / 202 | `OK` / `CREATED` / `ACCEPTED` |
| 400 | `INVALID_PARAMS` |
| 401 | `UNAUTHORIZED` |
| 403 | `FORBIDDEN` |
| 404 / 405 | `NOT_FOUND` / `METHOD_NOT_ALLOWED` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 429 | `RATE_LIMITED`（限流） |
| 500 | `INTERNAL_ERROR` |
| 501 / 503 | `NOT_IMPLEMENTED` / `SERVICE_UNAVAILABLE` |

业务码（覆盖上表默认值）：

| code | 出现位置 |
|---|---|
| `AUTH_TOKEN_MISSING` | 受保护接口未带 Bearer 令牌 |
| `AUTH_TOKEN_INVALID` | 令牌无效/过期/用户被禁用 |
| `AUTH_TOKEN_TYPE_INVALID` | 拿 refresh token 当 access token |
| `AUTH_INVALID_CREDENTIALS` | `POST /auth/login` 账号或密码错误 |
| `AUTH_REFRESH_TOKEN_INVALID` | `POST /auth/refresh` 刷新令牌无效 |
| `PERMISSION_DENIED` | 非管理员访问 `/admin/*`、模型写接口 |
| `API_KEY_MISSING` / `API_KEY_INVALID` | `POST /upload`、`GET /tasks/*` |
| `DB_UNAVAILABLE` | `/tasks/<id>` 查库失败（503） |
| `IMAGE_EXPIRED` | `GET /tasks/<id>/image` 图片已被回收或不存在（410） |
| `MAINTENANCE_MODE` | 维护模式拦截（503，带 `maintenance: true`） |

> 前端灰度建议：新代码只判 `code`，旧代码继续判 `success`/`message`，两者当前完全兼容。

## 2. 接口总表

### 2.1 认证 `/auth`（9）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| POST | `/auth/register` | 无 | `username, password, email` | `{success,message,data}` | 201 / 400 |
| POST | `/auth/login` | 无 | `username, password` | `{success,message,data:{access_token,refresh_token,...}}` | 200 / 401 |
| POST | `/auth/refresh` | 无 | `refresh_token` | 同上 | 200 / 401 |
| GET | `/auth/verify` | Bearer | 无 | `{success,message,data:{user_id,username,role}}` | 200 / 401 |
| POST | `/auth/logout` | Bearer | 无 | `{success,message}` | 200 / 401 |
| POST | `/auth/forgot-password` | 无 | `email` | `{success,message}` | 200 / 400 |
| POST | `/auth/reset-password` | 无 | `token, password, confirm_password` | `{success,message}` | 200 / 400 |
| POST | `/auth/verify-reset-token` | 无 | `token` | `{success,message}` | 200 / 400 |
| POST | `/auth/verify-email` | 无 | — | `501 功能开发中` | **501（未实现）** |

### 2.2 用户 `/users`（5）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/users/profile` | Bearer（可选登录） | 无 | `{success,data:{id,username,email,role,status,...}}` | 200 / 401 |
| PUT | `/users/profile` | Bearer | 任意资料字段（部分更新） | `{success,message,data?}` | 200 / 400 |
| PUT | `/users/change-password` | Bearer | `old_password, new_password` | `{success,message}` | 200 / 400 |
| GET | `/users/sessions` | Bearer | 无 | `{success,data:{sessions:[...]}}` | 200（**预留，返回假数据**） |
| DELETE | `/users/sessions/<session_id>` | Bearer | — | `{success,message}` | 200（**预留，空实现**） |

### 2.3 API 密钥 `/api-keys`（6）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/api-keys` | Bearer | 无 | `{success,data:[{id,name,permission,status,max_usage,usage_count,...}]}` | 200 |
| POST | `/api-keys` | Bearer | `name, permission(read/write/admin), max_usage` | `{success,data:{id,key,...}}` | 201 / 400 |
| PUT | `/api-keys/<key_id>` | Bearer | 任意可更新字段 | `{success,message,data?}` | 200 / 400 |
| POST | `/api-keys/<key_id>/revoke` | Bearer | 无 | `{success,message}` | 200 / 400 |
| DELETE | `/api-keys/<key_id>` | Bearer | 无 | `{success,message}` | 200 / 400 |
| POST | `/api-keys/verify` | 无（内部） | `api_key` 或 `X-API-Key` 头 | `{success,data:{key_id,user_id,username,role,permission}}` | 200 / 401 |

### 2.4 节点 `/nodes`（4）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/nodes` | Bearer | 无（管理员返回全量） | `{type,timestamp,data:[node...]}`；node 同时给 `capabilities`（字符串，旧）与 `capabilities_list`（数组，新） | 200 / 401 / 500 |
| POST | `/nodes` | Bearer | `name, addr?, token?, capabilities`（**数组或逗号串均可**） | `{success,message,data:{id,capabilities:[...],token}}` | 201 / 400 / 500 |
| PUT | `/nodes/<node_id>` | Bearer | 同上（可选字段） | `{success,message}` | 200 / 400 / **403** / 500 |
| DELETE | `/nodes/<node_id>` | Bearer | 无 | `{success,message}` | 200 / **403** / 500 |

### 2.5 仪表盘 `/dashboard`（6 条路由 / 4 个函数）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/dashboard/summary` | Bearer | 无 | `{type,timestamp,data:{...}}` | 200 / 401 / 500 |
| GET | `/dashboard/overview` | Bearer | 同上（**别名**） | 同上 | 同上 |
| GET | `/dashboard/stats` | Bearer | 无 | `{type,timestamp,data:{accuracy,online_nodes,...}}` | 200 / 500 |
| GET | `/dashboard/nodes` | Bearer | 无（管理员全量） | `{type,timestamp,data:[node...]}` | 200 / 500 |
| GET | `/dashboard/tasks` | Bearer | `page, limit, time_range, status` | `{type,timestamp,data:[...],page,total_pages,total_count,completed_count,pending_count}` | 200 / 500 |
| GET | `/dashboard/history` | Bearer | 同上（**别名**） | 同上 | 同上 |

### 2.6 模型 `/models`（6）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/models` | 无 | 无 | `{success,models:[{id,model_id,db_id?,type,name,version,config_url,config_hash}]}` | 200 |
| GET | `/models/admin` | 管理员 | 无 | `{success,models:[{id,db_id,model_id,display_name,...}]}` | 200 / 401 / 403 |
| POST | `/models` | 管理员 | `model_id, version, config_url, display_name?, type?, config_hash?, notes?, activate?` | `{success,message,data?}` | 201 / 400 |
| PUT | `/models/<model_id>` | 管理员 | 同上（可选字段） | `{success,message,data?}` | 200 / 400 |
| DELETE | `/models/<model_id>` | 管理员 | 无 | `{success,message}` | 200 / 400 |
| POST | `/models/<model_id>/activate` | 管理员 | 无 | `{success,message}` | 200 / 400 |

### 2.7 后台管理 `/admin`（9）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/admin/users` | 管理员 | `page, per_page, keyword` | `{success,data:{users:[...],page,per_page,total,total_pages}}` | 200 / 400 |
| POST | `/admin/users` | 管理员 | `username, password, email?, role?` | `{success,message,data?}` | 201 / 400 |
| GET | `/admin/users/<user_id>` | 管理员 | 无 | `{success,data:{user}}` | 200 / 404 |
| PUT | `/admin/users/<user_id>` | 管理员 | 任意可更新字段 | `{success,message,data?}` | 200 / 400 |
| DELETE | `/admin/users/<user_id>` | 管理员 | 无 | `{success,message}` | 200 / 400 |
| PUT | `/admin/users/<user_id>/roles` | 管理员 | `role` | `{success,message}` | 200 / 400 |
| PUT | `/admin/users/<user_id>/status` | 管理员 | `status`（**必须 int 0/1**） | `{success,message}` | 200 / 400 |
| GET | `/admin/settings` | 管理员 | 无 | `{success,data:{auto_split_ratio,rate_limit_enabled,task_max_retries,maintenance_mode}}` | 200 |
| PUT | `/admin/settings` | 管理员 | 上述四个键（值都是**字符串**） | `{success,data:{...}}` | 200 / 400 |

### 2.8 识别任务 `/upload`、`/tasks`（4）
| 方法 | 路径 | 鉴权 | 入参 | 成功响应 | 状态码 |
|---|---|---|---|---|---|
| GET | `/upload` | 无 | 无 | `{type:"info",message,usage:{...}}` | 200 |
| POST | `/upload` | `X-API-Key` + 限流 | multipart `file`/`image` 或 `image_base64`，`model=37ac\|llm\|auto` | `{type:"dispatch_task",status:"queued",task_id,model}`；或 SSE 流 | **200**（语义应为 202）/ 400 / 401 / 429 |
| GET | `/tasks/<task_id>` | `X-API-Key` | 无 | `{type:"task_result",status,result,image:{...},...}` | 200 / **202**（未完成）/ 401 / 503 |
| GET | `/tasks/<task_id>/image` | `X-API-Key` 或 Bearer | `original=1`、`max_side=N` | 图片二进制（响应头 `X-Image-Source: cache\|tmp\|node`） | 200 / 401 / **410**（本地与节点都没有） |
| GET | `/tasks/<task_id>/stream` | `X-API-Key` | 无 | SSE：`data: {status,result,...}` | 200（流）/ 401 |

### 2.9 识别结果结构（多人物，2026-09-13 起）

节点侧开始返回**多个人物**的识别结果（YOLO 检测到几个人物就识别几次），结果存在 `task_results.result` 里：

```json
{
  "success": true,
  "recognition_type": "local",
  "crop_method": "yolo",
  "image": {"width": 1024, "height": 1536},
  "characters": [
    {
      "index": 0,
      "bbox":         {"x": 0.3125, "y": 0.1042, "w": 0.2100, "h": 0.6320},
      "bbox_percent": {"x": 31.25,  "y": 10.42,  "w": 21.00,  "h": 63.20},
      "detector_confidence": 0.91,
      "confidence": 96.06,
      "class_probs": [{"name": "原神/荧", "prob": 96.06}]
    }
  ],
  "character_count": 1,
  "class_probs": [{"name": "原神/荧", "prob": 96.06}]
}
```

- 坐标分母是**原图**尺寸（检测前的缩放会换算回来，见 `src/cli/detection/bbox.py`）。
- 两种坐标都给（`bbox` 0-1、`bbox_percent` 0-100），避免「百分比（小数）」的歧义。
- `characters` 按检测框面积降序，最多 `MAX_CHARACTERS`（默认 10）；顶层 `class_probs` = 置信度最高的人物（旧前端零改动）。
- 未检出人物时 `characters: []`、`crop_method: "full"`，顶层回落整图识别（老行为）。
- 裁剪方式（env `CROP_METHOD`）：`yolo` / `mediapipe` / `auto`；auto = YOLO 优先，未命中回落 mediapipe，再没有则整图。
- 图片文件：上传后服务端在 `saves/tmp`（原图）与 `saves/cache`（压缩副本）各留一份，节点一份；回收策略见 `docs/design-image-pipeline.md`。

### 2.10 图片补拉（服务端回收后仍能取图，2026-09-25）

    GET /tasks/<id>/image
      -> 本地 saves/cache、saves/tmp 都没有
      -> 查 task_results.node_id，向该节点发 image_request
      <- 节点回 image_response（base64），服务端写回 tmp + cache 后再返回
      节点离线 / 超过 IMAGE_RETAIN_SEC（默认 900s）/ 响应超时 8s -> 410 IMAGE_EXPIRED

- 开关：服务端 `IMAGE_NODE_REFETCH`（默认 true）、节点侧 `IMAGE_RETAIN_SEC`（0 = 恢复"推理完即删"）。
- 命中补拉时响应头是 `X-Image-Source: node`（写回本地后下一次即为 `cache`）。
- 依赖列 `task_results.node_id`（迁移见 `scripts/alter_tables.sql`）；列不存在时服务端自动退回旧 SQL，仅补拉不可用。

## 3. 规范性问题清单（按严重度）

### 🔴 高：会影响联调正确性或数据安全

**3.1 `/tasks/<task_id>` 与 `/tasks/<task_id>/stream` 不校验任务归属（IDOR）** —— ⏸ **按需求保留（特性），本轮不改**
现状：只校验 `X-API-Key` 是否有效，SQL 是 `SELECT result, status FROM task_results WHERE task_id = %s`，没有比对 `user_id`/`api_key_id`。
影响：任何持有有效 API Key 的用户，只要拿到别人的 `task_id`（UUID v4，难猜但会出现在日志/前端/分享链接里），就能读到他人的识别结果。
决定（2026-09-13）：作为特性保留——`task_id` 本身即凭证，跨 Key 查询是需求之一。相应地`task_id` 不能出现在公开日志/分享链接里。
（若以后要收紧：查询加 `AND (user_id = %s OR api_key_id = %s)`，命中不到返回 404。）

**3.2 三套响应信封并存** —— ✅ **已修（灰度增量）**：出口统一补 `success`/`code`，旧结构原样保留（见 §1.1）
| 信封 | 出现的接口 | 形态 |
|---|---|---|
| A | `/auth/*`、`/users/*`、`/api-keys/*`、`/admin/*`、`/models`(写) | `{success, message, data}` |
| B | `/dashboard/*`、`/nodes`、`/upload`、`/tasks/*`、`GET /models` | `{type, timestamp, data\|status\|result\|models}`（**无 success**） |
| C | `/dashboard/*` 的异常分支 | `{error: "..."}` |
影响：前端/Apifox 无法写一套断言或统一拦截；B 类判断成功只能看 HTTP 码，C 类连 `message` 都没有。
处理：**不动旧结构**，统一补 `success`/`code`（C 形态再补 `message`）。前端可按 `code` 写统一拦截器。
后续（不兼容窗口再做）：把 B 的 `type/timestamp` 收进 `data`。

**3.3 无机器可读错误码** —— ✅ **已修（灰度增量）**
处理：全量响应带 `code`（状态码推导 + 业务码覆盖），`message` 仍作展示文案，见 §1.1 的码表。

**3.4 同一个 `id` 在 `/models` 与 `/models/admin` 中含义不同**
- `GET /models` → `{"id": "37ac", "type": "local"}`（业务标识字符串）
- `GET /models/admin` → `{"id": 1, "model_id": "37ac"}`（数据库主键 int）
影响：Apifox 会把两者合并成同一个 Model，字段类型冲突；前端也容易混用。
处理：**两个都补**——`GET /models` 每条加 `model_id`（同 id）与 `db_id`（来自 models 表时才有）；`GET /models/admin` 每条加 `db_id`。旧 `id` 保留不动。

**3.5 `capabilities` 是 JSON 字符串，且请求/响应格式不一致**
现状：响应 `{"capabilities": "[\"local\", \"llm\"]"}`（JSON-in-JSON 字符串）；请求体却收逗号分隔的 `capabilities: "local,llm"`。
影响：任何强类型客户端都要二次解析；空值/空格处理容易出错。
处理：请求侧兼容三种写法（JSON 数组 / JSON 数组字符串 / 逗号串，数组不再 500）；响应侧新增数组字段 `capabilities_list`，旧字符串 `capabilities` 保留。前端可先读 `capabilities_list`。

### 🟠 中：风格与语义不统一，容易踩坑

**3.6 路由别名** —— 📄 **文档先行（已标注）**：`/dashboard/summary` ≡ `/dashboard/overview`，`/dashboard/tasks` ≡ `/dashboard/history`。OpenAPI 里已给 `overview` / `history` 标 `deprecated: true`（Apifox 会显示废弃标记），接口本身保留。

**3.7 路径风格混用**：资源名有复数（`/nodes`、`/models`、`/api-keys`），也有动词路径（`/upload`、`/auth/verify`、`/users/change-password`、`/api-keys/<id>/revoke`、`/models/<id>/activate`）；`/models/admin` 又不像 `/admin/*` 前缀那样归属清晰。建议：`/models/admin` → `/admin/models`（旧路径保留别名），动词类保留但文档标注语义。

**3.8 `/upload` 一址两用**：GET 返回「用法说明」，POST 才是业务。建议 `GET /upload/info`（或 `/api-info`）。

**3.9 排队成功返回 200 而非 202**：`POST /upload` 实为「已受理」，`/tasks/<id>` 未完成时反而正确用了 202。建议 POST 返回 **202**，并在响应里给出 `data.status_url` 或 `Location` 头。

**3.10 分页参数与元数据不统一**
- `/admin/users`：`page` + `per_page`，元数据在 `data` 里；
- `/dashboard/tasks`：`page` + `limit`，元数据（`page/total_pages/total_count`）在**顶层**。
建议：统一 `page` + `page_size`，元数据集中到 `meta`（或 `data.pagination`）。

**3.11 状态码语义漂移**
- `/nodes/<id>` 的 POST/PUT/DELETE 在「不存在」和「无权限」两种情况下都返回 **403** 且文案是「请确认节点存在或无权操作」；建议 404 / 403 分开。
- `/users/profile` 用 `optional_login` 注入身份，函数里又判一次未登录返回 401（重复实现，可直接用 `login_required`）。
- `POST /auth/verify-email` 稳定返回 **501「功能开发中」**：建议从对外文档/OpenAPI 里移除，或标注 `x-not-implemented`，免得 Apifox 用例里出现一个永远失败的接口。

**3.12 时间格式两套**：`created_at/updated_at` 是 `YYYY-MM-DD HH:MM:SS`（本地时区、无偏移），而 `/dashboard/*`、`/upload`、`/tasks/*` 的 `timestamp` 是 **epoch 秒**。建议统一 ISO 8601（带时区）并固定字段名 `created_at`；`timestamp` 保留但注明单位。

**3.13 `PUT` 实际是部分更新（PATCH 语义）**：`PUT /users/profile`、`PUT /models/<id>`、`PUT /nodes/<id>` 都只更新传入字段（`/nodes/<id>` 全空时返回 400「没有需要更新的字段」）。建议改 `PATCH`，或在文档里明确「未传字段保持不变」。

**3.14 `PUT /admin/users/<user_id>/status` 要求 `status` 是 **int 0/1**，而 `/api-keys` 的 `status` 是字符串 `active/disabled`，任务状态又是 `pending/completed/failed` —— 同一名词三种类型。建议分别命名（`is_active` / `status`）或统一字符串枚举。

**3.15 限流覆盖面太窄**：只有 `POST /upload` 受限流保护，`/auth/login`、`/auth/register`、`/auth/forgot-password` 完全没有 → 口令爆破与邮件轰炸风险。建议对 `/auth/*` 加同一套限流，并在 429 响应加标准 `Retry-After` 头。

**3.16 SSE 端点的鉴权方式对浏览器不可用**：`GET /tasks/<id>/stream` 只要 `X-API-Key`，而浏览器 `EventSource` 不能自定义请求头；前端目前只能用 `POST /upload` 的流式返回。建议支持短期签名查询参数（`?token=`）或在文档明确「仅服务端/CLI 使用」。

### 🟡 低：代码卫生与可维护性

**3.17 死代码**：`POST /upload` 里 `X-Requested-With: XMLHttpRequest` 分支与默认分支返回**完全相同**的 JSON，可以删掉。
**3.18 布尔真值陷阱**：`/models` 写接口的 `activate=bool(data.get("activate", False))` —— 传字符串 `""false"` 也会得到 `True`。建议显式解析 `in ("1","true",True,1)`。
**3.19 参数静默降级**：`/upload` 的 `model` 非法值被改写成 `37ac`，而不是返回 400；客户端拼错字段名时不会报错，只会「莫名走了本地模型」。建议白名单校验失败返回 400，或至少回显 `model` 的同时给出 `model_fallback: true`。
**3.20 没有 API 版本前缀**：所有路径都在根下（`/models`、`/nodes`…），一旦不兼容变更只能同时改客户端。建议新接口走 `/v1/*`，或在 OpenAPI `info.version` + CHANGELOG 里维护兼容策略。
**3.21 预留接口返回假数据**：`GET /users/sessions` 返回一条硬编码「当前会话」（`created_at: "当前会话"` 这种非日期值），`DELETE /users/sessions/<id>` 是空实现却回 200「会话已登出」。建议未实现就返回 501，或干脆先下线。

## 4. 本轮实施情况（2026-09-13）

| 项 | 状态 | 说明 |
|---|---|---|
| 3.1 任务结果跨 Key 可读 | ⏸ **按需求保留（特性）** | 不改代码；`task_id` 视为凭证 |
| 3.2 三套信封 | ✅ 已修（灰度） | `after_request` 统一补 `success`/`code`，旧字段不动（§1.1） |
| 3.3 无错误码 | ✅ 已修（灰度） | 全量响应带 `code` + 业务码表（§1.1） |
| 3.4 模型 id 语义 | ✅ 已修（灰度） | `/models` 补 `model_id`/`db_id`，`/models/admin` 补 `db_id` |
| 3.5 capabilities 格式 | ✅ 已修（灰度） | 请求兼容数组，响应补 `capabilities_list` |
| 3.6–3.21 其余 | 📄 文档先行 | OpenAPI 已标 `deprecated`（别名路由）与语义说明，接口行为不动 |

实现位置：`src/server/utils/api_response.py`（信封收口 + 错误码表 + JSON 错误页）、`src/server/AC_web/__init__.py`（安装钩子）、`middleware/{auth_middleware,rate_limiter}.py`、`routes/{auth_routes,upload_routes,node_routes,model_routes}.py`、`services/dashboard/node_service.py`。

验证：`pytest tests/server` **128 passed**；对备用实例（13139）实测 31 个响应**全部**带 `success`+`code`；字段语义 12/12 通过。

## 5. 如果要继续动，建议顺序

1. 3.2 第二步：把 B 形态的 `type/timestamp` 收进 `data`（不兼容变更，需前端同步）。
2. 3.15 限流覆盖 `/auth/*` + 加 `Retry-After` 头。
3. 3.11 状态码语义（`/nodes/<id>` 的 404/403 拆分）、3.12 时间格式统一。
4. 3.17–3.21 代码卫生（死代码、`activate` 真值陷阱、参数静默降级、版本前缀、假数据预留接口）。

## 6. 相关文件

- 机器可读接口定义：`docs/openapi.yaml`（本目录，含 `code` 字段与 deprecated 标注）
- 字段语义实测脚本：`.dsh-scratch/verify_field_semantics.py`（`API_BASE` 可指向任意实例）
- 实测抓包（每个接口的真实状态码与响应体）：`.dsh-scratch/api-probe.json`（脚本 `.dsh-scratch/probe_api.py`，可重跑）
- 路由总览脚本：`.dsh-scratch/dump_routes.py`
