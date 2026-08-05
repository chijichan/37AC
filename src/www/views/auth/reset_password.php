<?php
$extra_css = ['/static/css/pages/auth.css'];
require_once ROOT_PATH . '/views/layout.php';
?>

<div class="auth-wrap">
    <div class="auth-card">
        <div id="token-verifying">
            <h1>验证令牌</h1>
            <div class="auth-status-block">
                <span class="status-icon"><i class="ph ph-circle-notch"></i></span>
                <p>正在验证重置链接…</p>
            </div>
        </div>

        <div id="token-invalid" style="display: none;">
            <h1>重置密码</h1>
            <div class="auth-status-block">
                <span class="status-icon"><i class="ph ph-warning-circle"></i></span>
                <p id="token-error-message">重置链接无效或已过期</p>
                <div class="auth-footer">
                    <a href="/auth/forgot-password">重新申请重置链接</a>
                </div>
                <div class="auth-footer">
                    <a href="/auth/login">返回登录</a>
                </div>
            </div>
        </div>

        <div id="reset-form-container" style="display: none;">
            <h1>重置密码</h1>
            <p class="subtitle">请设置你的新密码</p>

            <div id="error-message" class="auth-message error"></div>
            <div id="success-message" class="auth-message success"></div>

            <form id="reset-form">
                <div class="field">
                    <label for="password">新密码</label>
                    <div class="password-toggle">
                        <input type="password" id="password" name="password" class="input"
                            placeholder="请输入新密码（至少 6 位）" autocomplete="new-password" minlength="6" required />
                        <button type="button" class="toggle-btn" id="toggle-pw" aria-label="切换密码可见性">显示</button>
                    </div>
                    <div class="password-strength">
                        <div id="strength-bar" class="password-strength-bar"></div>
                    </div>
                    <span id="strength-text" class="password-strength-text"></span>
                    <ul class="password-requirements">
                        <li id="req-length">至少 6 个字符</li>
                    </ul>
                </div>

                <div class="field">
                    <label for="confirm-password">确认新密码</label>
                    <div class="password-toggle">
                        <input type="password" id="confirm-password" name="confirm-password" class="input"
                            placeholder="请再次输入新密码" autocomplete="new-password" minlength="6" required />
                        <button type="button" class="toggle-btn" id="toggle-confirm-pw" aria-label="切换确认密码可见性">显示</button>
                    </div>
                    <span id="match-text" class="match-indicator"></span>
                </div>

                <button type="submit" class="btn btn-primary btn-block btn-lg" id="submit-btn">重置密码</button>
            </form>

            <div class="auth-divider">或者</div>

            <div class="auth-footer">
                <a href="/auth/login">返回登录</a>
            </div>
            <div class="auth-footer">
                <a href="/auth/forgot-password">重新发送重置链接</a>
            </div>
        </div>

        <div id="success-container" style="display: none;">
            <h1>密码重置成功</h1>
            <div class="auth-status-block">
                <span class="status-icon" style="color: var(--ac-success);"><i class="ph ph-check-circle"></i></span>
                <p>你的密码已成功重置。</p>
                <div class="redirect-countdown">
                    <span id="redirect-countdown-text">5</span> 秒后自动跳转到登录页…
                </div>
                <div class="auth-footer" style="margin-top: 1rem;">
                    <a href="/auth/login" class="btn btn-primary">立即登录</a>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
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

    function hideAlerts() {
        const errorEl = document.getElementById('error-message');
        const successEl = document.getElementById('success-message');
        if (errorEl) errorEl.style.display = 'none';
        if (successEl) successEl.style.display = 'none';
    }

    function togglePasswordVisibility(inputId, btnId) {
        const input = document.getElementById(inputId);
        const btn = document.getElementById(btnId);
        if (!input || !btn) return;

        if (input.type === 'password') {
            input.type = 'text';
            btn.textContent = '隐藏';
        } else {
            input.type = 'password';
            btn.textContent = '显示';
        }
    }

    function checkPasswordStrength(password) {
        const bar = document.getElementById('strength-bar');
        const text = document.getElementById('strength-text');
        const reqLength = document.getElementById('req-length');

        if (password.length >= 6) {
            reqLength.className = 'valid';
            reqLength.textContent = '已满足：至少 6 个字符';
        } else {
            reqLength.className = 'invalid';
            reqLength.textContent = `至少 6 个字符（当前 ${password.length} 位）`;
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
            bar.style.background = 'var(--ac-danger)';
            text.textContent = '弱';
            text.style.color = 'var(--ac-danger)';
        } else if (strength < 70) {
            bar.style.background = 'var(--ac-warning)';
            text.textContent = '中等';
            text.style.color = 'var(--ac-warning)';
        } else {
            bar.style.background = 'var(--ac-success)';
            text.textContent = '强';
            text.style.color = 'var(--ac-success)';
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

    let redirectTimer = null;

    function startRedirectCountdown(seconds) {
        const countdownEl = document.getElementById('redirect-countdown-text');
        let remaining = seconds;

        function updateCountdown() {
            countdownEl.textContent = remaining;
            remaining--;
            if (remaining < 0) {
                clearInterval(redirectTimer);
                window.location.href = '/auth/login';
            }
        }

        updateCountdown();
        redirectTimer = setInterval(updateCountdown, 1000);
    }

    async function handleResetPassword(event) {
        event.preventDefault();

        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const btn = document.getElementById('submit-btn');

        if (!password || password.length < 6) {
            showError('密码长度不能少于 6 位');
            return;
        }

        if (password !== confirmPassword) {
            showError('两次输入的密码不一致');
            return;
        }

        hideAlerts();
        btn.disabled = true;
        btn.textContent = '重置中…';

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
                startRedirectCountdown(5);
            } else {
                showError(result.message || '密码重置失败，请重试');
                btn.disabled = false;
                btn.textContent = '重置密码';
            }
        } catch (error) {
            showError('网络错误：无法连接到服务器，请检查网络或联系管理员');
            btn.disabled = false;
            btn.textContent = '重置密码';
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        verifyToken();

        document.getElementById('toggle-pw').addEventListener('click', function() {
            togglePasswordVisibility('password', 'toggle-pw');
        });
        document.getElementById('toggle-confirm-pw').addEventListener('click', function() {
            togglePasswordVisibility('confirm-password', 'toggle-confirm-pw');
        });

        document.getElementById('password').addEventListener('input', function() {
            checkPasswordStrength(this.value);
        });

        document.getElementById('confirm-password').addEventListener('input', function() {
            checkPasswordMatch(this.value);
        });

        document.getElementById('reset-form').addEventListener('submit', handleResetPassword);

        window.addEventListener('beforeunload', function() {
            if (redirectTimer) {
                clearInterval(redirectTimer);
            }
        });
    });
</script>

<?php require_once ROOT_PATH . '/views/footer.php'; ?>
