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
</style>

<div class="auth-container">
    <h1>登录</h1>
    <p class="subtitle">欢迎回来，请登录你的账号</p>

    <div id="error-message" class="error-message"></div>
    <div id="success-message" class="success-message"></div>

    <form id="login-form" onsubmit="return handleLogin(event)">
        <div class="form-group">
            <label for="username">用户名</label>
            <input
                type="text"
                id="username"
                name="username"
                placeholder="请输入用户名"
                aria-label="用户名"
                autocomplete="username"
                required />
        </div>

        <div class="form-group">
            <label for="password">密码</label>
            <input
                type="password"
                id="password"
                name="password"
                placeholder="请输入密码"
                aria-label="密码"
                autocomplete="current-password"
                required />
        </div>

        <fieldset>
            <label for="remember">
                <input role="switch" id="remember" type="checkbox" name="remember" />
                记住我
            </label>
        </fieldset>

        <button type="submit" id="login-btn">登录</button>
    </form>

    <div class="divider">或者</div>

    <div class="auth-footer">
        还没有账号？<a href="/auth/register">立即注册</a>
    </div>
    <div class="auth-footer" style="margin-top: 0.5rem;">
        <a href="/auth/forgot-password">忘记密码？</a>
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

    async function handleLogin(event) {
        event.preventDefault();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const remember = document.getElementById('remember').checked;
        const btn = document.getElementById('login-btn');

        if (!username || !password) {
            showError('请输入用户名和密码');
            return false;
        }

        btn.setAttribute('aria-busy', 'true');
        btn.textContent = '登录中...';

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password
                })
            });

            const result = await response.json();

            if (result.success) {
                // 存储令牌到 localStorage
                const tokenData = result.data;
                localStorage.setItem('access_token', tokenData.access_token);
                localStorage.setItem('refresh_token', tokenData.refresh_token);
                localStorage.setItem('user_id', tokenData.user_id);
                localStorage.setItem('username', tokenData.username);
                localStorage.setItem('role', tokenData.role);

                // 同时写入 Cookie（PHP 端可读）
                document.cookie = `access_token=${tokenData.access_token}; path=/; max-age=${remember ? 86400 * 30 : 86400}`;
                document.cookie = `user_id=${tokenData.user_id}; path=/; max-age=${remember ? 86400 * 30 : 86400}`;
                document.cookie = `username=${tokenData.username}; path=/; max-age=${remember ? 86400 * 30 : 86400}`;
                document.cookie = `role=${tokenData.role}; path=/; max-age=${remember ? 86400 * 30 : 86400}`;

                showSuccess('登录成功！正在跳转...');

                // 跳转到控制台
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 800);
            } else {
                showError(result.message || '登录失败');
                btn.removeAttribute('aria-busy');
                btn.textContent = '登录';
            }
        } catch (error) {
            showError('网络错误，请检查服务器连接');
            btn.removeAttribute('aria-busy');
            btn.textContent = '登录';
        }

        return false;
    }
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>