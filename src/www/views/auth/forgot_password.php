<?php require_once ROOT_PATH . '/views/layout.php'; ?>

<style>
    .auth-container {
        max-width: 420px;
        margin: 3rem auto;
        padding: 2rem;
        background: var(--pico-card-background-color);
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
    }

    .auth-container h1 {
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .auth-container .subtitle {
        text-align: center;
        color: var(--pico-muted-color);
        margin-bottom: 2rem;
        font-size: 0.9rem;
    }

    .auth-container .auth-footer {
        text-align: center;
        margin-top: 1.5rem;
        font-size: 0.875rem;
        color: var(--pico-muted-color);
    }

    .auth-container .auth-footer a {
        color: var(--pico-primary);
        text-decoration: none;
    }

    .auth-container .auth-footer a:hover {
        text-decoration: underline;
    }

    .auth-container .error-message {
        background: var(--pico-del-color);
        color: var(--pico-primary-inverse);
        padding: 0.75rem 1rem;
        border-radius: var(--pico-border-radius);
        margin-bottom: 1rem;
        display: none;
        font-size: 0.875rem;
    }

    .auth-container .success-message {
        background: var(--pico-ins-color);
        color: var(--pico-primary-inverse);
        padding: 0.75rem 1rem;
        border-radius: var(--pico-border-radius);
        margin-bottom: 1rem;
        display: none;
        font-size: 0.875rem;
    }

    .auth-container .info-box {
        background: var(--pico-card-sectioning-background-color);
        border: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        padding: 1rem;
        margin-bottom: 1.5rem;
        font-size: 0.875rem;
        color: var(--pico-muted-color);
        line-height: 1.6;
    }
</style>

<div class="auth-container">
    <h1>忘记密码</h1>
    <p class="subtitle">输入你的邮箱，我们将发送重置链接</p>

    <div id="error-message" class="error-message"></div>
    <div id="success-message" class="success-message"></div>

    <div class="info-box">
        <strong>说明：</strong>请输入你注册时使用的邮箱地址，
        系统将向该邮箱发送密码重置链接。如果未收到邮件，
        请检查垃圾邮件箱或联系管理员。
    </div>

    <form id="forgot-form" onsubmit="return handleForgotPassword(event)">
        <div class="form-group">
            <label for="email">注册邮箱</label>
            <input
                type="email"
                id="email"
                name="email"
                placeholder="请输入你的注册邮箱"
                aria-label="邮箱"
                autocomplete="email"
                required />
        </div>

        <button type="submit" id="submit-btn">发送重置链接</button>
    </form>

    <div class="auth-footer">
        <a href="/auth/login">返回登录</a>
    </div>
    <div class="auth-footer" style="margin-top: 0.25rem;">
        还没有账号？<a href="/auth/register">立即注册</a>
    </div>
</div>

<script>
    const API_BASE_URL = 'http://127.0.0.1:13138';

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

    async function handleForgotPassword(event) {
        event.preventDefault();

        const email = document.getElementById('email').value.trim();
        const btn = document.getElementById('submit-btn');

        if (!email) {
            showError('请输入邮箱地址');
            return false;
        }

        btn.setAttribute('aria-busy', 'true');
        btn.textContent = '发送中...';

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
            } else {
                showError(result.message || '发送失败，请稍后重试');
                btn.removeAttribute('aria-busy');
                btn.textContent = '发送重置链接';
            }
        } catch (error) {
            showError('网络错误，请检查服务器连接');
            btn.removeAttribute('aria-busy');
            btn.textContent = '发送重置链接';
        }

        return false;
    }
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>