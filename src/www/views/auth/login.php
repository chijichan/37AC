<?php
$extra_css = ['/static/css/pages/auth.css'];
require_once ROOT_PATH . '/views/layout.php';
?>

<div class="auth-wrap">
    <div class="auth-card">
        <h1>登录</h1>
        <p class="subtitle">欢迎回来，请登录你的账号</p>

        <div id="error-message" class="auth-message error"></div>
        <div id="success-message" class="auth-message success"></div>

        <form id="login-form">
            <div class="field">
                <label for="username">用户名</label>
                <input type="text" id="username" name="username" class="input" placeholder="请输入用户名"
                    autocomplete="username" required />
            </div>

            <div class="field">
                <label for="password">密码</label>
                <input type="password" id="password" name="password" class="input" placeholder="请输入密码"
                    autocomplete="current-password" required />
            </div>

            <div class="field">
                <label class="checkbox-row" for="remember">
                    <input id="remember" type="checkbox" name="remember" />
                    记住我（30 天）
                </label>
            </div>

            <button type="submit" class="btn btn-primary btn-block btn-lg" id="login-btn">登录</button>
        </form>

        <div class="auth-divider">或者</div>

        <div class="auth-footer">
            还没有账号？<a href="/auth/register">立即注册</a>
        </div>
        <div class="auth-footer">
            <a href="/auth/forgot-password">忘记密码？</a>
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

    async function handleLogin(event) {
        event.preventDefault();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const remember = document.getElementById('remember').checked;
        const btn = document.getElementById('login-btn');

        if (!username || !password) {
            showError('请输入用户名和密码');
            return;
        }

        btn.disabled = true;
        btn.textContent = '登录中…';

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
                const tokenData = result.data;
                localStorage.setItem('access_token', tokenData.access_token);
                localStorage.setItem('refresh_token', tokenData.refresh_token);
                localStorage.setItem('user_id', tokenData.user_id);
                localStorage.setItem('username', tokenData.username);
                localStorage.setItem('role', tokenData.role);

                // 同时写入 Cookie（PHP 端可读）
                const maxAge = remember ? 86400 * 30 : 86400;
                document.cookie = `access_token=${tokenData.access_token}; path=/; max-age=${maxAge}`;
                document.cookie = `user_id=${tokenData.user_id}; path=/; max-age=${maxAge}`;
                document.cookie = `username=${tokenData.username}; path=/; max-age=${maxAge}`;
                document.cookie = `role=${tokenData.role}; path=/; max-age=${maxAge}`;

                showSuccess('登录成功，正在跳转…');

                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 800);
            } else {
                showError(result.message || '登录失败');
                btn.disabled = false;
                btn.textContent = '登录';
            }
        } catch (error) {
            showError('网络错误，请检查服务器连接');
            btn.disabled = false;
            btn.textContent = '登录';
        }
    }

    document.getElementById('login-form').addEventListener('submit', handleLogin);
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>
