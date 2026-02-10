# 🔐 项目安全措施说明

## 已实施的安全措施

### 1. 目录结构保护 ✅
- **Web 根目录**: `public/` - 只有这个目录应该对外暴露
- **Views 目录**: `views/` - 在 public 之外,无法直接访问
- 所有 PHP 视图文件都在 `views/` 中,通过 `index.php` 路由访问

### 2. `.htaccess` 保护 (Apache) ✅

#### `public/.htaccess`
- ✅ 阻止访问隐藏文件 (`.git`, `.env` 等)
- ✅ 阻止访问敏感配置文件
- ✅ 禁用目录浏览
- ✅ 添加安全响应头
- ✅ URL 重写到 index.php

#### `views/.htaccess`
- ✅ 拒绝所有直接 HTTP 访问

### 3. PHP 代码层保护 ✅

#### `public/index.php`
- ✅ 设置安全 HTTP 头
- ✅ 定义 `APP_ACCESS` 常量
- ✅ 清理和验证 URI (防止路径遍历)

#### `views/layout.php`
- ✅ 检查 `APP_ACCESS` 常量
- ✅ 拒绝直接访问

### 4. 安全 HTTP 头 ✅
```
X-Frame-Options: SAMEORIGIN          # 防止点击劫持
X-Content-Type-Options: nosniff      # 防止 MIME 类型嗅探
X-XSS-Protection: 1; mode=block      # XSS 保护
```

---

## 建议的额外安全措施

### 🔒 生产环境部署时

1. **禁用 PHP 错误显示**
```php
// 在 index.php 顶部添加
ini_set('display_errors', 0);
error_reporting(0);
```

2. **添加 HTTPS 强制跳转** (在 `.htaccess`)
```apache
# 强制使用 HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

3. **添加 CSP (内容安全策略)**
```php
header("Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' https://static.322337.xyz data:; font-src 'self' data:;");
```

4. **文件上传安全** (针对 `/upload` 页面)
```php
// 验证文件类型
$allowed_types = ['image/jpeg', 'image/png', 'image/jpg'];
if (!in_array($_FILES['file']['type'], $allowed_types)) {
    die('Invalid file type');
}

// 验证文件大小
if ($_FILES['file']['size'] > 10 * 1024 * 1024) { // 10MB
    die('File too large');
}

// 重命名上传的文件
$new_filename = bin2hex(random_bytes(16)) . '.jpg';
```

5. **添加速率限制**
   - 防止暴力攻击
   - 限制 API 请求频率

6. **环境变量配置**
```php
// 创建 .env 文件存储敏感信息
// 使用 vlucas/phpdotenv 库加载
```

---

## 服务器配置建议

### Nginx (如果使用)
创建 `nginx.conf`:
```nginx
location ~ /views/ {
    deny all;
    return 403;
}

location ~ /\.(?!well-known) {
    deny all;
}

location / {
    try_files $uri $uri/ /index.php?$query_string;
}
```

### PHP-FPM 设置
```ini
expose_php = Off
allow_url_fopen = Off
allow_url_include = Off
max_execution_time = 30
memory_limit = 128M
upload_max_filesize = 10M
post_max_size = 10M
```

---

## 常见攻击防护

| 攻击类型 | 防护措施 | 状态 |
|---------|---------|------|
| 路径遍历 | URI 清理 + .htaccess | ✅ |
| 直接访问 Views | APP_ACCESS 检查 | ✅ |
| XSS 攻击 | 安全头 + 输入验证 | ⚠️ 需要在表单处理中添加 |
| CSRF 攻击 | CSRF Token | ❌ 待实现 |
| SQL 注入 | 使用 PDO/Prepared Statements | ❌ 当前无数据库 |
| 文件上传漏洞 | 类型验证 + 大小限制 | ⚠️ 已在前端实现,需后端加强 |
| 点击劫持 | X-Frame-Options | ✅ |
| 暴力破解 | 速率限制 | ❌ 待实现 |

---

## 安全检查清单

开发环境:
- [x] 目录结构合理
- [x] .htaccess 配置
- [x] 基本安全头
- [x] 防止直接访问

生产环境额外需要:
- [ ] HTTPS 证书
- [ ] 隐藏 PHP 版本信息
- [ ] 错误日志记录
- [ ] 定期安全更新
- [ ] 文件权限设置 (755 目录, 644 文件)
- [ ] 备份策略

---

## 总结

**当前安全等级**: 🟡 中等 (适合开发/测试)

**达到生产级别需要**:
1. ✅ 基础防护 (已完成)
2. ⚠️  输入验证和清理
3. ⚠️  CSRF 保护
4. ⚠️  速率限制
5. ❌ HTTPS 配置
6. ❌ 日志监控

---

## 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PHP Security Guide](https://www.php.net/manual/en/security.php)
- [Apache Security Tips](https://httpd.apache.org/docs/2.4/misc/security_tips.html)
