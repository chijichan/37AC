<?php
$extra_css = ['/static/css/pages/auth.css'];
require_once ROOT_PATH . '/views/layout.php';
?>

<div class="auth-wrap">
    <div class="auth-card">
        <h1>注册</h1>
        <p class="subtitle">创建你的账号，开始使用</p>

        <div id="error-message" class="auth-message error"></div>
        <div id="success-message" class="auth-message success"></div>

        <form id="register-form">
            <div class="field">
                <label for="username">用户名</label>
                <input type="text" id="username" name="username" class="input" placeholder="3-50 个字符，支持中文"
                    autocomplete="username" required />
            </div>

            <div class="field">
                <label for="email">邮箱</label>
                <input type="email" id="email" name="email" class="input" placeholder="请输入邮箱"
                    autocomplete="email" required />
            </div>

            <div class="field">
                <label for="password">密码</label>
                <input type="password" id="password" name="password" class="input" placeholder="至少 6 个字符"
                    autocomplete="new-password" required />
                <span class="hint">密码长度至少 6 个字符</span>
            </div>

            <div class="field">
                <label for="confirm-password">确认密码</label>
                <input type="password" id="confirm-password" name="confirm-password" class="input"
                    placeholder="再次输入密码" autocomplete="new-password" required />
            </div>

            <div class="field">
                <label class="checkbox-row" for="agree">
                    <input id="agree" type="checkbox" name="agree" required />
                    <span>我已阅读并同意 <a href="/about" target="_blank">服务条款</a></span>
                </label>
            </div>

            <button type="submit" class="btn btn-primary btn-block btn-lg" id="register-btn">注册</button>
        </form>

        <div class="auth-divider">或者</div>

        <div class="auth-footer">
            已有账号？<a href="/auth/login">立即登录</a>
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
            return;
        }

        if (password !== confirmPassword) {
            showError('两次输入的密码不一致');
            return;
        }

        if (!agree) {
            showError('请阅读并同意服务条款');
            return;
        }

        btn.disabled = true;
        btn.textContent = '注册中…';

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
                showSuccess('注册成功，正在跳转到登录页…');
                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 1500);
            } else {
                showError(result.message || '注册失败');
                btn.disabled = false;
                btn.textContent = '注册';
            }
        } catch (error) {
            showError('网络错误，请检查服务器连接');
            btn.disabled = false;
            btn.textContent = '注册';
        }
    }

    document.getElementById('register-form').addEventListener('submit', handleRegister);
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>
