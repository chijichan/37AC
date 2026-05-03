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

    .loading-spinner {
        text-align: center;
        padding: 2rem;
        color: var(--pico-muted-color);
    }

    .token-invalid-container {
        text-align: center;
        padding: 1rem 0;
    }

    .token-invalid-container .icon-large {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }

    .form-group {
        margin-bottom: 1.25rem;
    }

    .form-group label {
        display: block;
        margin-bottom: 0.375rem;
        font-weight: 500;
    }

    .password-strength {
        margin-top: 0.5rem;
        height: 4px;
        border-radius: 2px;
        background: var(--pico-muted-border-color);
        transition: all 0.3s ease;
    }

    .password-strength-bar {
        height: 100%;
        border-radius: 2px;
        width: 0%;
        transition: all 0.3s ease;
    }

    .password-strength-text {
        font-size: 0.75rem;
        margin-top: 0.25rem;
        display: block;
        text-align: right;
    }

    .password-requirements {
        list-style: none;
        padding: 0;
        margin: 0.5rem 0 0 0;
        font-size: 0.8rem;
    }

    .password-requirements li {
        padding: 2px 0;
        color: var(--pico-muted-color);
    }

    .password-requirements li.valid {
        color: var(--pico-ins-color);
    }

    .password-requirements li.invalid {
        color: var(--pico-del-color);
    }

    .match-indicator {
        font-size: 0.8rem;
        display: none;
        margin-top: 0.25rem;
    }

    .match-indicator.match {
        color: var(--pico-ins-color);
    }

    .match-indicator.no-match {
        color: var(--pico-del-color);
    }
</style>

<div class="auth-container">
    <div id="token-verifying">
        <h1>验证令牌</h1>
        <div class="loading-spinner">
            <span aria-busy="true">正在验证重置链接...</span>
        </div>
    </div>

    <div id="token-invalid" style="display: none;">
        <h1>重置密码</h1>
        <div class="token-invalid-container">
            <span class="icon-large"><?php require ROOT_PATH . '/views/components/icons/warn.php'; ?></span>
            <p id="token-error-message">重置链接无效或已过期</p>
            <div class="auth-footer">
                <a href="/auth/forgot-password">重新申请重置链接</a>
            </div>
            <div class="auth-footer" style="margin-top: 0.25rem;">
                <a href="/auth/login">返回登录</a>
            </div>
        </div>
    </div>

    <div id="reset-form-container" style="display: none;">
        <h1>重置密码</h1>
        <p class="subtitle">请设置你的新密码</p>

        <div id="error-message" class="error-message"></div>
        <div id="success-message" class="success-message"></div>

        <form id="reset-form">
            <div class="form-group">
                <label for="password">新密码</label>
                <input
                    type="password"
                    id="password"
                    name="password"
                    placeholder="请输入新密码（至少6位）"
                    aria-label="新密码"
                    autocomplete="new-password"
                    minlength="6"
                    required />
                <div class="password-strength">
                    <div id="strength-bar" class="password-strength-bar"></div>
                </div>
                <span id="strength-text" class="password-strength-text"></span>
                <ul class="password-requirements">
                    <li id="req-length">至少 6 个字符</li>
                </ul>
            </div>

            <div class="form-group">
                <label for="confirm-password">确认新密码</label>
                <input
                    type="password"
                    id="confirm-password"
                    name="confirm-password"
                    placeholder="请再次输入新密码"
                    aria-label="确认新密码"
                    autocomplete="new-password"
                    minlength="6"
                    required />
                <span id="match-text" class="match-indicator"></span>
            </div>

            <button type="submit" id="submit-btn">重置密码</button>
        </form>

        <div class="divider">或者</div>

        <div class="auth-footer">
            <a href="/auth/login">返回登录</a>
        </div>
        <div class="auth-footer" style="margin-top: 0.25rem;">
            <a href="/auth/forgot-password">重新发送重置链接</a>
        </div>
    </div>

    <div id="success-container" style="display: none;">
        <h1>密码重置成功</h1>
        <div class="token-invalid-container">
            <p>你的密码已成功重置</p>
            <div class="auth-footer" style="margin-top: 1.5rem;">
                <a href="/auth/login" role="button" style="text-decoration: none;">前往登录</a>
            </div>
        </div>
    </div>
</div>

<script>
    const API_BASE_URL = '<?= API_BASE_URL ?>';

    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('token') || '<?= htmlspecialchars(isset($token) ? $token : '') ?>';

    function showError(message) {
        const el = document.getElementById('error-message');
        if (el) {
            el.textContent = message;
            el.style.display = 'block';
            const successEl = document.getElementById('success-message');
            if (successEl) successEl.style.display = 'none';
        }
    }

    function showSuccess(message) {
        const el = document.getElementById('success-message');
        if (el) {
            el.textContent = message;
            el.style.display = 'block';
            const errorEl = document.getElementById('error-message');
            if (errorEl) errorEl.style.display = 'none';
        }
    }

    function hideAlerts() {
        const errorEl = document.getElementById('error-message');
        const successEl = document.getElementById('success-message');
        if (errorEl) errorEl.style.display = 'none';
        if (successEl) successEl.style.display = 'none';
    }

    function checkPasswordStrength(password) {
        const bar = document.getElementById('strength-bar');
        const text = document.getElementById('strength-text');
        const reqLength = document.getElementById('req-length');

        if (password.length >= 6) {
            reqLength.className = 'valid';
            reqLength.innerHTML = '至少 6 个字符';
        } else {
            reqLength.className = 'invalid';
            reqLength.innerHTML = '至少 6 个字符（当前 ' + password.length + ' 位）';
        }

        let strength = 0;
        if (password.length >= 6) strength += 20;
        if (password.length >= 10) strength += 15;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 20;
        if (/\d/.test(password)) strength += 15;
        if (/[^a-zA-Z0-9]/.test(password)) strength += 15;
        if (password.length >= 14) strength += 15;

        strength = Math.min(100, strength);

        bar.style.width = strength + '%';
        if (strength < 40) {
            bar.style.background = 'var(--pico-del-color)';
            text.textContent = '弱';
            text.style.color = 'var(--pico-del-color)';
        } else if (strength < 70) {
            bar.style.background = '#ffc107';
            text.textContent = '中等';
            text.style.color = '#ffc107';
        } else {
            bar.style.background = 'var(--pico-ins-color)';
            text.textContent = '强';
            text.style.color = 'var(--pico-ins-color)';
        }
    }

    function checkPasswordMatch(value) {
        const password = document.getElementById('password').value;
        const matchText = document.getElementById('match-text');

        if (value.length === 0) {
            matchText.style.display = 'none';
            return;
        }

        matchText.style.display = 'block';
        if (value === password) {
            matchText.className = 'match-indicator match';
            matchText.textContent = '密码匹配';
        } else {
            matchText.className = 'match-indicator no-match';
            matchText.textContent = '密码不匹配';
        }
    }

    async function verifyToken() {
        if (!resetToken) {
            document.getElementById('token-verifying').style.display = 'none';
            document.getElementById('token-invalid').style.display = 'block';
            document.getElementById('token-error-message').textContent = '缺少重置令牌，请重新申请';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/auth/verify-reset-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    token: resetToken
                })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('token-verifying').style.display = 'none';
                document.getElementById('reset-form-container').style.display = 'block';
            } else {
                document.getElementById('token-verifying').style.display = 'none';
                document.getElementById('token-invalid').style.display = 'block';
                document.getElementById('token-error-message').textContent = result.message || '重置链接无效或已过期';
            }
        } catch (error) {
            document.getElementById('token-verifying').style.display = 'none';
            document.getElementById('token-invalid').style.display = 'block';
            document.getElementById('token-error-message').textContent = '网络错误，请检查服务器连接';
        }
    }

    async function handleResetPassword(event) {
        event.preventDefault();

        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const btn = document.getElementById('submit-btn');

        if (!password || password.length < 6) {
            showError('密码长度不能少于6位');
            return;
        }

        if (password !== confirmPassword) {
            showError('两次输入的密码不一致');
            return;
        }

        hideAlerts();
        btn.setAttribute('aria-busy', 'true');
        btn.textContent = '重置中...';
        btn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    token: resetToken,
                    password: password,
                    confirm_password: confirmPassword
                })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('reset-form-container').style.display = 'none';
                document.getElementById('success-container').style.display = 'block';
            } else {
                showError(result.message || '密码重置失败，请重试');
                btn.removeAttribute('aria-busy');
                btn.textContent = '重置密码';
                btn.disabled = false;
            }
        } catch (error) {
            showError('网络错误：无法连接到服务器，请检查网络或联系管理员');
            btn.removeAttribute('aria-busy');
            btn.textContent = '重置密码';
            btn.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        verifyToken();

        document.getElementById('password').addEventListener('input', function() {
            checkPasswordStrength(this.value);
        });

        document.getElementById('confirm-password').addEventListener('input', function() {
            checkPasswordMatch(this.value);
        });

        document.getElementById('reset-form').addEventListener('submit', handleResetPassword);
    });
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>