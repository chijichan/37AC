# 仪表盘功能说明

> 2026-08 随全站重构更新。视觉基于自研 AC 设计系统「樱花拿铁」（樱花粉单强调色），不再使用 Pico CSS。

## 功能概览

### 1. SPA 单页结构

- 二级导航（总览 / 节点管理 / API 密钥 / 使用记录 / 设置）无刷新切换
- 桌面端 pill 导航，移动端折叠为下拉菜单
- 子页模板由 PHP 端预渲染为 JSON 内嵌（`pageTemplates`），切换时注入 + 脚本重放
- URL 经 `history.pushState` 同步，支持浏览器前进后退
- 各子页注册 `window.dashboardPageInit` 钩子，数据加载 Promise 挂 `window.__pageLoadPromise`

### 2. 总览（overview）

- 统计卡：总访问量 / 图片上传 / 活跃用户 / 识别准确率（数字用 JetBrains Mono）
- 快速操作：上传图片、节点管理、系统设置、使用记录
- 系统状态：CPU / 内存 / 磁盘进度条 + 网络上下行速率
- 最近活动列表 + 最近上传记录表格
- 数据源：`GET /dashboard/summary`

### 3. 节点管理（nodes）

- 统计：总节点 / 在线 / 离线 / 已启用
- 节点卡片：名称、地址、状态徽章、负载与任务数、能力（local / local,llm）
- **权限**：普通用户仅显示/管理自己名下的节点，管理员可见全部（后端按 `user_id` 过滤）
- 节点卡片操作：详情 / 修改（详情弹窗内含删除入口，删除按钮在关闭按钮之前）
- 添加节点：名称、Token（可留空自动生成，创建后一次性弹窗展示）、地址（可选）、识别能力
- 修改节点：名称、Token（留空不修改）、地址、识别能力
- 详情弹窗：完整信息（不含 Token，避免敏感信息暴露）
- 删除节点：二次确认弹窗，在线节点有红字警告（删除后立即断开连接）
- 数据源：`GET /dashboard/nodes`、`POST /nodes`、`PUT /nodes/{id}`、`DELETE /nodes/{id}`

### 4. API 密钥（apikeys）

- 统计：总密钥 / 活跃 / 总调用次数
- 生成密钥：名称 + 权限级别（只读/读写/管理员）+ 最大使用次数
- 完整密钥仅在创建时通过 Modal 展示一次（复制按钮 + 确认关闭）
- 密钥卡片：状态徽章、使用进度条、暂停/启用/撤销/删除（危险操作二次确认）
- 数据源：`GET /api-keys`、`POST /api-keys`、`PUT /api-keys/{id}`、`POST /api-keys/{id}/revoke`、`DELETE /api-keys/{id}`

### 5. 使用记录（history）

- 统计：总请求 / 已完成 / 未完成 / 完成率（服务端全量统计，非当前页）
- 筛选：时间范围（7/30/90/365 天）、状态、每页条数
- 表格：任务 ID、时间、文件名、识别结果、置信度、API 密钥、状态
- 分页：服务端真实分页（`page` / `limit` / `total_pages` / `total_count` 等字段），仅多页时显示分页栏
- 任务详情 Modal：完整字段 + 原始返回 JSON（转义渲染）
- 数据源：`GET /dashboard/tasks?page=&limit=&time_range=&status=`

### 6. 设置（settings）

- 个人信息：用户名 / 邮箱 / 简介（`GET/PUT /users/profile`）
- 修改密码：旧密码 + 两次新密码校验（`PUT /users/change-password`）
- 通知偏好：本地存储（后端接口预留）
- 危险操作：退出登录、删除账户（引导联系管理员）

## 设计要点

- 统计卡与表格使用统一组件（`.stat` / `.table` / `.prob-bar` / `.badge`）
- 所有 API 返回的动态文本渲染前经 `escapeHtml()` 转义，操作按钮按 ID 回查数据（不再内联拼接参数）
- 通知用右上角 Toast（`Notify`），确认操作用居中 Modal（`Modal.show`）
- 空状态、骨架屏加载态均有覆盖

## 访问方式

```
http://127.0.0.1:8000/dashboard
```

未登录访问会被 PHP 端 `require_auth()` 重定向到 `/auth/login`（支持 Session 与 access_token Cookie）。

## 浏览器兼容性

- Chrome / Edge / Firefox / Safari 最新版
- 不支持 IE（依赖原生 `<dialog>`、ES Module、CSS 自定义属性）
