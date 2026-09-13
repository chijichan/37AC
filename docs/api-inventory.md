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
| 响应信封 | **三种并存**（见 §4.1） |
| 错误语义 | 只有中文 `message`，**没有机器可读错误码** |

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
| GET | `/nodes` | Bearer | 无（管理员返回全量） | `{type,timestamp,data:[node...]}` | 200 / 401 / 500 |
| POST | `/nodes` | Bearer | `name, addr?, token?, capabilities`（逗号串） | `{success,message,data:{id,capabilities,token}}` | 201 / 400 / 500 |
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
| GET | `/models` | 无 | 无 | `{success,models:[{id:"37ac",type,name,version,config_url,config_hash}]}` | 200 |
| GET | `/models/admin` | 管理员 | 无 | `{success,models:[{id:1,model_id:"37ac",...}]}` | 200 / 401 / 403 |
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
| GET | `/tasks/<task_id>` | `X-API-Key` | 无 | `{type:"task_result",status,result,...}` | 200 / **202**（未完成）/ 401 / 503 |
| GET | `/tasks/<task_id>/stream` | `X-API-Key` | 无 | SSE：`data: {status,result,...}` | 200（流）/ 401 |

## 3. 规范性问题清单（按严重度）

### 🔴 高：会影响联调正确性或数据安全

**3.1 `/tasks/<task_id>` 与 `/tasks/<task_id>/stream` 不校验任务归属（IDOR）**
现状：只校验 `X-API-Key` 是否有效，SQL 是 `SELECT result, status FROM task_results WHERE task_id = %s`，没有比对 `user_id`/`api_key_id`。
影响：任何持有有效 API Key 的用户，只要拿到别人的 `task_id`（UUID v4，难猜但会出现在日志/前端/分享链接里），就能读到他人的识别结果。
建议：查询加归属条件 `AND (user_id = %s OR api_key_id = %s)`，命中不到时返回 404（不要用 403，避免泄漏存在性）。

**3.2 三套响应信封并存**
| 信封 | 出现的接口 | 形态 |
|---|---|---|
| A | `/auth/*`、`/users/*`、`/api-keys/*`、`/admin/*`、`/models`(写) | `{success, message, data}` |
| B | `/dashboard/*`、`/nodes`、`/upload`、`/tasks/*`、`GET /models` | `{type, timestamp, data\|status\|result\|models}`（**无 success**） |
| C | `/dashboard/*` 的异常分支 | `{error: "..."}` |
影响：前端/Apifox 无法写一套断言或统一拦截；B 类判断成功只能看 HTTP 码，C 类连 `message` 都没有。
建议：统一 A 为外壳（B 的 `type/timestamp` 移入 `data` 或作为可选的顶层透传字段保留一个版本周期）。

**3.3 无机器可读错误码**
现状：失败只有中文 `message`（如「令牌无效或已过期」）。
影响：客户端做多语言/分支处理只能匹配字符串；Apifox 无法断言错误类型。
建议：加 `code`（如 `AUTH_TOKEN_INVALID`、`RATE_LIMITED`、`NODE_FORBIDDEN`），保留 `message` 作展示文案。

**3.4 同一个 `id` 在 `/models` 与 `/models/admin` 中含义不同**
- `GET /models` → `{"id": "37ac", "type": "local"}`（业务标识字符串）
- `GET /models/admin` → `{"id": 1, "model_id": "37ac"}`（数据库主键 int）
影响：Apifox 会把两者合并成同一个 Model，字段类型冲突；前端也容易混用。
建议：公共接口改用 `model_id`，或在 `/models/admin` 中把主键命名为 `db_id`。

**3.5 `capabilities` 是 JSON 字符串，且请求/响应格式不一致**
现状：响应 `{"capabilities": "[\"local\", \"llm\"]"}`（JSON-in-JSON 字符串）；请求体却收逗号分隔的 `capabilities: "local,llm"`。
影响：任何强类型客户端都要二次解析；空值/空格处理容易出错。
建议：请求与响应都用数组 `["local","llm"]`（服务端兼容旧字符串入参一个版本）。

### 🟠 中：风格与语义不统一，容易踩坑

**3.6 路由别名**：`/dashboard/summary` ≡ `/dashboard/overview`，`/dashboard/tasks` ≡ `/dashboard/history`。建议保留一个，另一个标 `deprecated: true`（Apifox 会显示废弃标记）。

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

## 4. 如果要动手，建议的顺序

1. **先修 3.1（越权读取）**——纯服务端 SQL 加条件，零兼容风险。
2. 再统一 3.2/3.3（信封 + 错误码）——建议新增 `code` 字段并保持旧字段不变，前端灰度切换。
3. 3.4/3.5（模型 id 语义、`capabilities` 数组化）——属于同一批「字段含义修正」，改前先在前端 grep 使用点。
4. 其余（3.6–3.21）可作为「文档先行」：在 OpenAPI 里标注 `deprecated`/语义说明，接口本身不动，等下一次不兼容窗口一起改。

## 5. 相关文件

- 机器可读接口定义：`docs/openapi.yaml`（本目录）
- 实测抓包（每个接口的真实状态码与响应体）：`.dsh-scratch/api-probe.json`（脚本 `.dsh-scratch/probe_api.py`，可重跑）
- 路由总览脚本：`.dsh-scratch/dump_routes.py`
