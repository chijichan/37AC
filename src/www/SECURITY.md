# 项目安全措施说明

> 2026-08 随全站重构更新。本文档描述 `www/`（PHP Web 应用）的当前实际安全状态。

## 已实施的安全措施

### 1. 目录结构保护

- Web 根目录仅 `public/`，`views/`、`controllers/` 在其外，无法直接 HTTP 访问
- `www/.htaccess` 与 `public/.htaccess`：阻止隐藏文件、`.env`、版本控制目录等敏感路径
- 所有页面经 `public/index.php` 单入口路由分发

### 2. 密钥管理

- **站级 API Key 不下发前端**：上传相关请求走 `api_controller.php` 同源代理（`/api/upload`、`/api/tasks/*`），`X-API-Key` 由服务端从 `.env` 的 `UPLOAD_API_KEY` 读取注入
- 用户级接口使用 JWT（`Auth.fetch` 自动携带与刷新）
- `.env` 不提交仓库，模板见 `.env.example`

### 3. XSS 防护

- 全局 `escapeHtml()` 工具（`app.js`），所有 API 返回的动态文本插入 DOM 前必须转义
- `Notify` 通知使用 `textContent` 渲染，天然免疫注入
- `Modal.show` 的 `bodyHtml` 约定：动态数据由调用方先转义
- 操作按钮不再内联拼接用户数据（`onclick="fn('${name}')"` 类写法已消除，改为按 ID 回查）

### 4. 错误信息控制

- `display_errors` 由 `.env` 的 `APP_DEBUG` 控制，默认关闭；生产环境必须为 `false`
- 调试开启时仅用于本地开发

### 5. 认证与会话

- `require_auth()` 支持 Session 与 `access_token` Cookie 双通道，JWT 过期自动尝试 refresh
- 未登录访问受保护页面重定向 `/auth/login`
- 密码重置令牌一次性、带过期时间；重置页 canonical 不含令牌参数（防止凭证进入 SEO 元数据）

## 常见攻击防护现状

| 攻击类型 | 防护措施 | 状态 |
|---------|---------|------|
| 路径遍历 / 直接访问视图 | public 外目录 + .htaccess | ✅ |
| API Key 泄露 | 服务端代理注入，前端零密钥 | ✅ |
| XSS | escapeHtml + textContent 渲染 | ✅（新增代码需遵守约定） |
| 错误信息泄露 | APP_DEBUG 默认关闭 | ✅（生产需确认配置） |
| 点击劫持 | 依赖 .htaccess 安全头 | ⚠️ 生产建议复查 |
| CSRF | 表单未实现 Token 校验 | ❌ 待实现 |
| 暴力破解 / 频率限制 | 依赖 Flask 端限流中间件 | ⚠️ PHP 侧未独立实现 |
| HTTPS | 未强制 | ❌ 生产需配置 |

## 生产部署清单

1. `.env` 设置 `APP_DEBUG=false`，配置强随机 `UPLOAD_API_KEY`（与后端 `UPLOAD_API_KEYS` 一致）
2. 使用 Apache / Nginx + PHP-FPM（**不要用 `php -S`**：单线程，SSE 流式代理会阻塞其他请求）
3. 强制 HTTPS（`.htaccess` 或 Nginx 配置 301 跳转）
4. PHP 配置：`expose_php=Off`、`allow_url_include=Off`、`upload_max_filesize=10M`
5. 文件权限：目录 755、文件 644，`.env` 600

## 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PHP Security Guide](https://www.php.net/manual/en/security.php)
