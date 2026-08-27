# 37AC 前端部署指南

> 提供两种部署方式：
> - **Windows**：Nginx + 多实例 `php-cgi.exe` 进程池（本机开发 / 内网）
> - **Linux**：Nginx + 原生 PHP-FPM + systemd（生产推荐）
>
> Windows 无 PHP-FPM，用多个 `php-cgi.exe` 组成进程池达到同等并发效果
> （SSE 长连接只占一个实例，其余请求并行处理；`php -S` 单线程仅用于快速调试）。

## 架构

浏览器 → Nginx(:8000) → php-cgi 进程池(:9001~9004) → Flask(:13138) → TCP(:13137) 节点

## 环境要求

| 组件 | 要求 |
|---|---|
| Nginx | 1.26+，加入 PATH 或设置 `NGINX_HOME`（start 脚本按此解析，无绝对路径） |
| PHP | 8.x 含 `php-cgi.exe`（Windows），加入 PATH 或设置 `PHP_HOME`；`php-cgi.ini` 放在 php-cgi.exe 同目录（可选，缺失时用默认配置） |
| MySQL | 5.7+ / 8.x，库名 `37ac`，utf8mb4 |
| Flask 服务端 | `python src/server/runserver.py`（监听 13138/13137） |

## 数据库安装

**方式 A（推荐）— 交互式脚本**（读取 `src/server/.env` 连接信息 → 建库建表 → 设置管理员账号，密码 bcrypt 哈希入库、不回显）：

```bash
python scripts/install_db.py
```

**方式 B — 纯 SQL**：

```bash
mysql -u<用户名> -p < scripts/install.sql
```

> 方式 B 默认 admin 密码为随机占位，需另行设置（启动后走「忘记密码」，或 SQL 更新
> `users.password_hash`）。已有库升级执行 `mysql -u<用户名> -p < scripts/alter_tables.sql`。

## Windows 部署

### 1. 安装 Nginx（一次性）

```powershell
Invoke-WebRequest -Uri "https://nginx.org/download/nginx-1.26.3.zip" -OutFile "C:\tools\nginx-1.26.3.zip"
Expand-Archive -Path "C:\tools\nginx-1.26.3.zip" -DestinationPath "C:\tools\" -Force
Rename-Item "C:\tools\nginx-1.26.3" "C:\tools\nginx"
```

### 2. PHP 专用配置 `php-cgi.ini`（一次性）

FastCGI 下 Xdebug 会拖慢每个请求、opcache 能显著提速。从 `E:\apps\PHP\php.ini` 生成
剔除 Xdebug、启用 opcache 的 `php-cgi.ini`（实测 `/upload` 响应 6~14s → 0.2s），
或用以下 PowerShell 片段：

```powershell
$src = Get-Content "E:\apps\PHP\php.ini"
$lines = foreach ($l in $src) {
    $t = $l.Trim()
    if ($t -match '^zend_extension=.*xdebug' -or $t -eq '[xdebug]' -or $t -match '^xdebug\.') { continue }
    if ($t -eq ';zend_extension=opcache') { 'zend_extension=opcache'; continue }
    if ($t -eq ';opcache.enable=1') { 'opcache.enable=1'; continue }
    $l
}
[System.IO.File]::WriteAllLines("E:\apps\PHP\php-cgi.ini", $lines, (New-Object System.Text.UTF8Encoding $false))
```

### 3. Nginx 配置 `C:\tools\nginx\conf\nginx.conf`

- `root <项目实际路径>/src/www/public;` — 改成你本机项目的真实路径（例如 `C:/pj/37AC/src/www/public`）
- `try_files $uri $uri/ /index.php?$query_string;` — 对应 `.htaccess` 重写
- `upstream php_backend { server 127.0.0.1:9001..9004; }` — PHP-CGI 进程池
- PHP location 内 `fastcgi_buffering off;`（SSE 实时透传）、`fastcgi_read_timeout 480s;`
- `client_max_body_size 12m;`（上传上限）

完整示例可参照 `src/www/start-nginx.bat`。

### 4. 启动 / 停止 / 验证

```bat
src\www\start-nginx.bat   :: 检查 8000 端口 → 启动 4 个 php-cgi(9001~9004) → 启动 Nginx
src\www\stop-nginx.bat
```

```powershell
curl.exe -s -o NUL -w "%{http_code} (%{time_total}s)`n" http://localhost:8000/upload   # 期望 200 (<1s)
curl.exe -s -N --max-time 480 -H "X-Stream-Response: true" -H "X-Requested-With: XMLHttpRequest" `
  -F "file=@test.png" -F "model=37ac" http://localhost:8000/api/upload                 # 期望 queued→…→completed
```

### 5. 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| 页面响应 6~14 秒 | Xdebug 在 FastCGI 下开销大 | 确认 `php-cgi.ini` 无 Xdebug |
| SSE 攒批返回 | Nginx 缓冲了响应 | 确认 `fastcgi_buffering off` |
| `nginx: [emerg] unknown directive "锘?` | conf 带 UTF-8 BOM | 用无 BOM 编码重写 |
| 端口被占用 | 旧服务未停止 | `stop-nginx.bat` 或 `taskkill /IM nginx.exe /F` |
| 上传 413 | 图片超限 | 调大 `client_max_body_size` |

## Linux 部署（Ubuntu / Debian，Nginx + PHP-FPM + systemd）

### 1. 安装依赖并部署代码

```bash
sudo apt install -y nginx php-fpm php-mysql mysql-server python3 python3-venv python3-pip git
sudo git clone <仓库地址> /opt/37AC && cd /opt/37AC
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/server/requirements.txt
cp src/server/.env.example src/server/.env && vi src/server/.env   # 填 DB 连接等
```

### 2. 安装数据库

```bash
source .venv/bin/activate && python scripts/install_db.py    # 方式 A（推荐）
# 或: mysql -u<用户名> -p < scripts/install.sql              # 方式 B
```

### 3. Nginx 站点 `/etc/nginx/sites-available/37ac`

```nginx
server {
    listen 80;
    server_name your.domain.com;
    root /opt/37AC/src/www/public;
    index index.php;

    location / { try_files $uri $uri/ /index.php?$query_string; }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;   # 版本号按实际调整
        fastcgi_buffering off;                        # SSE 实时透传
        fastcgi_read_timeout 480s;
    }
    client_max_body_size 12m;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/37ac /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
```

### 4. Flask 服务（systemd）`/etc/systemd/system/37ac-server.service`

```ini
[Unit]
Description=37AC Server (Flask)
After=network.target mysql.service
[Service]
WorkingDirectory=/opt/37AC
ExecStart=/opt/37AC/.venv/bin/python src/server/runserver.py
Restart=always
User=www-data
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now 37ac-server
```

### 5. 启动 / 验证 / 排查

```bash
sudo systemctl enable --now nginx php8.2-fpm 37ac-server
curl -s -o /dev/null -w "%{http_code} (%{time_total}s)\n" http://localhost/upload        # 期望 200
curl -s -N --max-time 480 -H "X-Stream-Response: true" -H "X-Requested-With: XMLHttpRequest" \
  -F "file=@test.png" -F "model=37ac" http://localhost/api/upload                        # 期望 queued→…→completed
```

| 现象 | 原因 | 解决 |
|---|---|---|
| 502 Bad Gateway | PHP-FPM 未启动或 socket 路径不符 | `systemctl status php8.2-fpm`；核对 `fastcgi_pass` |
| 403 权限不足 | Nginx 用户读不到站点目录 | `sudo chown -R www-data:www-data /opt/37AC` |
| Flask 无法连库 | `.env` 未配置或 MySQL 未就绪 | 核对 `src/server/.env`；`systemctl status mysql` |

## 生产环境建议

- 当前 Nginx 配置为开发/内网用途（无 TLS），生产启用 HTTPS、隐藏 server 版本
- 替换默认密钥与密码；节点 Token 仅存 SHA-256 哈希
