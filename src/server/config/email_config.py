# config/email_config.py
"""邮件配置 - SMTP 设置、限制规则、HTML 模板"""

import os

# SMTP 邮件配置（从环境变量读取，用于密码重置等邮件发送）
# 如果未配置，重置链接将直接返回给前端（仅开发/调试模式）
SMTP_CONFIG = {
    "host": os.environ.get("SMTP_HOST", "smtp.163.com"),          # SMTP 服务器地址，如 smtp.qq.com
    "port": int(os.environ.get("SMTP_PORT", "465")),  # SMTP 端口，465(SSL) 或 587(TLS)
    "user": os.environ.get("SMTP_USER", "xhbbs123@163.com"),          # 发送邮箱地址
    "password": os.environ.get("SMTP_PASSWORD", "JCvNtQD4nP6RrEWY"),  # 邮箱授权码/密码
    "use_tls": os.environ.get("SMTP_USE_TLS", "0") == "1",  # 是否使用 TLS（否则使用 SSL）
    "from_name": os.environ.get("SMTP_FROM_NAME", "37AC 系统"),  # 发件人显示名称
}

# 密码重置限制（防止滥用）
RESET_RATE_LIMIT = {
    "max_requests": 3,  # 每邮箱最多请求次数
    "window_minutes": 15,  # 时间窗口（分钟）
}

# 密码重置邮件 HTML 模板
# {username}、{reset_url}、{expires_at} 将在运行时替换
# 样式遵循 login.php 的 Pico CSS 风格：蓝色强调色 + 红色警告 + 白色卡片背景
RESET_PASSWORD_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 420px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }}
        .header {{
            padding: 28px 24px 0 24px;
            text-align: center;
        }}
        .header h1 {{
            color: #111827;
            margin: 0 0 4px 0;
            font-size: 22px;
            font-weight: 600;
        }}
        .header .subtitle {{
            color: #6b7280;
            font-size: 14px;
            margin: 0 0 24px 0;
        }}
        .body {{
            padding: 0 24px 24px 24px;
            color: #374151;
            line-height: 1.8;
        }}
        .body p {{
            margin: 0 0 16px 0;
            font-size: 14px;
        }}
        .reset-btn {{
            display: inline-block;
            padding: 12px 32px;
            background: transparent;
            color: #0066cc !important;
            text-decoration: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 500;
            margin: 8px 0;
            border: 1px solid #0066cc;
        }}
        .reset-btn:hover {{
            background: transparent;
            text-decoration: underline;
        }}
        .url-box {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px 14px;
            word-break: break-all;
            font-size: 12px;
            color: #6b7280;
            margin: 12px 0;
        }}
        .warning {{
            background: transparent;
            color: #6b7280;
            border-radius: 0;
            padding: 8px 0;
            font-size: 13px;
            margin: 16px 0;
            line-height: 1.6;
        }}
        .warning strong {{
            color: #374151;
        }}
        .footer {{
            padding: 20px 24px;
            text-align: center;
            color: #9ca3af;
            font-size: 12px;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>密码重置请求</h1>
            <p class="subtitle">重置你的 37AC 账号密码</p>
        </div>
        <div class="body">
            <p>你好，<strong>{username}</strong>：</p>
            <p>你最近请求重置你的 37AC 账号密码。请点击下方按钮重置密码：</p>

            <div style="text-align: center;">
                <a href="{reset_url}" class="reset-btn" target="_blank">重置密码</a>
            </div>

            <p>如果按钮无法点击，请复制以下链接到浏览器地址栏打开：</p>
            <div class="url-box">{reset_url}</div>

            <div class="warning">
                此链接有效期为 <strong>1 小时</strong>（{expires_at} 前有效）。
                <br><br>如果你没有请求重置密码，请忽略此邮件，你的账号是安全的。
            </div>
        </div>
        <div class="footer">
            37AC 系统
        </div>
    </div>
</body>
</html>"""
