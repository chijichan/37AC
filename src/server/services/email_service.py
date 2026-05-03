# services/email_service.py
"""邮件发送服务 - 使用 SMTP 发送系统邮件（密码重置、通知等）"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from config.email_config import SMTP_CONFIG, RESET_PASSWORD_EMAIL_TEMPLATE
from config.log_config import get_logger

logger = get_logger("email_service")


def is_configured() -> bool:
    """检查 SMTP 是否已配置"""
    return bool(SMTP_CONFIG.get("host") and SMTP_CONFIG.get("user") and SMTP_CONFIG.get("password"))


def send_email(to_email: str, subject: str, html_content: str) -> dict:
    """发送邮件

    Args:
        to_email: 收件人邮箱地址
        subject: 邮件主题
        html_content: HTML 格式的邮件内容

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not is_configured():
        return {"success": False, "message": "SMTP 未配置，请设置环境变量 SMTP_HOST、SMTP_USER、SMTP_PASSWORD"}

    cfg = SMTP_CONFIG

    # 构建邮件
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to_email
    msg["Subject"] = Header(subject, "utf-8")

    # 添加 HTML 内容
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        if cfg.get("use_tls"):
            # 使用 TLS（端口 587）
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["user"], [to_email], msg.as_string())
        else:
            # 使用 SSL（端口 465）
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context()) as server:
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["user"], [to_email], msg.as_string())

        return {"success": True, "message": "邮件发送成功"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP 认证失败，请检查邮箱地址和授权码"}
    except smtplib.SMTPException as e:
        return {"success": False, "message": f"邮件发送失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"发送邮件时发生未知错误: {str(e)}"}


def send_password_reset_email(to_email: str, username: str, reset_url: str, expires_at: str) -> dict:
    """发送密码重置邮件

    Args:
        to_email: 收件人邮箱
        username: 用户名
        reset_url: 重置链接
        expires_at: 过期时间

    Returns:
        {"success": True/False, "message": "..."}
    """
    subject = "【37AC】密码重置请求"

    html_content = RESET_PASSWORD_EMAIL_TEMPLATE.format(
        username=username,
        reset_url=reset_url,
        expires_at=expires_at
    )

    return send_email(to_email, subject, html_content)
