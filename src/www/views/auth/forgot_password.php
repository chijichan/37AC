<?php
$extra_css = ['/static/css/pages/auth.css'];
require_once ROOT_PATH . '/views/layout.php';
?>

<div class="auth-wrap">
    <div class="auth-card">
        <h1>忘记密码</h1>
        <p class="subtitle">输入你的邮箱，我们将发送重置链接</p>

        <div id="error-message" class="auth-message error"></div>
        <div id="success-message" class="auth-message success"></div>

        <div class="auth-info-box">
            请输入注册时使用的邮箱地址，系统将向该邮箱发送密码重置链接。如果未收到邮件，请检查垃圾邮件箱或联系管理员。
        </div>

        <!-- 开发环境重置链接 -->
        <div id="reset-link-section" style="display: none;">
            <div class="auth-info-box warning">
                <strong>开发环境重置链接（点击直接访问）：</strong><br>
                <a id="reset-url" href="#" target="_blank"></a>
                <br><br>
                <strong>过期时间：</strong><span id="expires-at"></span>
                <br>
                <small>（此链接仅开发/本地环境可见，生产环境不会显示）</small>
            </div>
        </div>

        <form id="forgot-form">
            <div class="field">
                <label for="email">注册邮箱</label>
                <input type="email" id="email" name="email" class="input" placeholder="请输入你的注册邮箱"
                    autocomplete="email" required />
            </div>

            <button type="submit" class="btn btn-primary btn-block btn-lg" id="submit-btn">发送重置链接</button>
        </form>

        <!-- 冷却倒计时面板 -->
        <div id="cooldown-panel" class="cooldown-timer">
            <div class="timer-label">请等待</div>
            <div class="timer-display" id="cooldown-countdown">15:00</div>
            <div class="timer-label">后重新尝试</div>
        </div>

        <div class="auth-footer">
            <a href="/auth/login">返回登录</a>
        </div>
        <div class="auth-footer">
            还没有账号？<a href="/auth/register">立即注册</a>
        </div>
    </div>
</div>

<script>
    function showError(message) {
        const el = document.getElementById('error-message');
        el.textContent = message;
        el.style.display = 'block';
        document.getElementById('success-message').style.display = 'none';
    }

    function showSuccess(message) {
        const el = document.getElementById('success-message');
        el.textContent = message;
        el.style.display = 'block';
        document.getElementById('error-message').style.display = 'none';
    }

    function hideAlerts() {
        document.getElementById('error-message').style.display = 'none';
        document.getElementById('success-message').style.display = 'none';
    }

    let cooldownTimer = null;

    function startCooldown(seconds) {
        const panel = document.getElementById('cooldown-panel');
        const display = document.getElementById('cooldown-countdown');
        const btn = document.getElementById('submit-btn');
        const form = document.getElementById('forgot-form');

        form.style.display = 'none';
        panel.style.display = 'block';

        let remaining = seconds;

        function updateDisplay() {
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            display.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
        }

        clearInterval(cooldownTimer);
        updateDisplay();

        cooldownTimer = setInterval(() => {
            remaining--;
            updateDisplay();

            if (remaining <= 0) {
                clearInterval(cooldownTimer);
                cooldownTimer = null;
                panel.style.display = 'none';
                form.style.display = 'block';
                btn.disabled = false;
                btn.textContent = '发送重置链接';
            }
        }, 1000);
    }

    async function handleForgotPassword(event) {
        event.preventDefault();

        const email = document.getElementById('email').value.trim();
        const btn = document.getElementById('submit-btn');
        const resetLinkSection = document.getElementById('reset-link-section');

        if (!email) {
            showError('请输入邮箱地址');
            return;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showError('请输入有效的邮箱地址');
            return;
        }

        hideAlerts();
        btn.disabled = true;
        btn.textContent = '发送中…';

        try {
            const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email
                })
            });

            const result = await response.json();

            if (result.success) {
                showSuccess('重置链接已发送，请检查你的邮箱');
                btn.textContent = '已发送';
                btn.disabled = true;

                if (result.data && result.data.retry_after_minutes) {
                    startCooldown(result.data.retry_after_minutes * 60);
                } else {
                    startCooldown(60);
                }

                // 开发/本地环境无邮件系统时返回令牌
                if (result.data && result.data.token) {
                    const resetUrl = window.location.origin +
                        '/auth/reset-password?token=' + encodeURIComponent(result.data.token);
                    const urlEl = document.getElementById('reset-url');
                    urlEl.textContent = resetUrl;
                    urlEl.href = resetUrl;
                    document.getElementById('expires-at').textContent = result.data.expires_at;
                    resetLinkSection.style.display = 'block';
                }
            } else {
                if (result.data && result.data.retry_after_minutes) {
                    showError(result.message || '请求过于频繁');
                    startCooldown(result.data.retry_after_minutes * 60);
                } else {
                    showError(result.message || '发送失败，请稍后重试');
                    btn.disabled = false;
                    btn.textContent = '发送重置链接';
                }
            }
        } catch (error) {
            showError('网络错误：无法连接到服务器，请检查网络或联系管理员');
            btn.disabled = false;
            btn.textContent = '发送重置链接';
        }
    }

    document.getElementById('forgot-form').addEventListener('submit', handleForgotPassword);

    window.addEventListener('beforeunload', function() {
        if (cooldownTimer) {
            clearInterval(cooldownTimer);
        }
    });
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>
