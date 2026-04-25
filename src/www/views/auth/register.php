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

    .auth-container .divider {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 1.5rem 0;
        color: var(--pico-muted-color);
        font-size: 0.875rem;
    }

    .auth-container .divider::before,
    .auth-container .divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid var(--pico-muted-border-color);
    }

    .password-hint {
        font-size: 0.8rem;
        color: var(--pico-muted-color);
        margin-top: 0.25rem;
    }
</style>

<div class="auth-container">
    <h1>📝 注册</h1>
    <p class="subtitle">创建你的账号，开始使用</p>

    <div id="error-message" class="error-message"></div>
    <div id="success-message" class="success-message"></div>

    <form id="register-form" onsubmit="return handleRegister(event)">
        <div class="form-group">
            <label for="username">用户名</label>
            <input
                type="text"
                id="username"
                name="username"
                placeholder="3-50个字符，支持中文"
                aria-label="用户名"
                autocomplete="username"
                required />
        </div>

        <div class="form-group">
            <label for="email">邮箱</label>
            <input
                type="email"
                id="email"
                name="email"
                placeholder="请输入邮箱"
                aria-label="邮箱"
                autocomplete="email"
                required />
        </div>

        <div class="form-group">
            <label for="password">密码</label>
            <input
                type="password"
                id="password"
                name="password"
                placeholder="至少6个字符"
                aria-label="密码"
                autocomplete="new-password"
                required />
            <div class="password-hint">密码长度至少6个字符</div>
        </div>

        <div class="form-group">
            <label for="confirm-password">确认密码</label>
            <input
                type="password"
                id="confirm-password"
                name="confirm-password"
                placeholder="再次输入密码"
                aria-label="确认密码"
                autocomplete="new-password"
                required />
        </div>

        <fieldset>
            <label for="agree">
                <input role="switch" id="agree" type="checkbox" name="agree" required />
                我已阅读并同意 <a href="/about" target="_blank">服务条款</a>
            </label>
        </fieldset>

        <button type="submit" id="register-btn">注册</button>
    </form>

    <div class="divider">或者</div>

    <div class="auth-footer">
        已有账号？<a href="/auth/login">立即登录</a>
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

    async function handleRegister(event) {
        event.preventDefault();

        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const agree = document.getElementById('agree').checked;
        const btn = document.getElementById('register-btn');

        if (!username || !email || !password) {
            showError('请填写用户名、邮箱和密码');
            return false;
        }

        if (password !== confirmPassword) {
            showError('两次输入的密码不一致');
            return false;
        }

        if (!agree) {
            showError('请阅读并同意服务条款');
            return false;
        }

        btn.setAttribute('aria-busy', 'true');
        btn.textContent = '注册中...';

        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password,
                    email
                })
            });

            const result = await response.json();

            if (result.success) {
                showSuccess('注册成功！正在跳转到登录页...');
                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 1500);
            } else {
                showError(result.message || '注册失败');
                btn.removeAttribute('aria-busy');
                btn.textContent = '注册';
            }
        } catch (error) {
            showError('网络错误，请检查服务器连接');
            btn.removeAttribute('aria-busy');
            btn.textContent = '注册';
        }

        return false;
    }
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>