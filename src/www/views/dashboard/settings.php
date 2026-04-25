<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<style>
    .settings-section {
        background: var(--pico-card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        margin-bottom: 1.5rem;
    }

    .settings-section h3 {
        margin-top: 0;
        border-bottom: 1px solid var(--pico-muted-border-color);
        padding-bottom: 0.75rem;
        margin-bottom: 1.5rem;
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>⚙️ 设置</h1>
    <p>管理你的账户设置和偏好</p>
</header>

<!-- 个人信息 -->
<section class="settings-section">
    <h3>👤 个人信息</h3>
    <form id="form-profile">
        <div class="grid">
            <label>
                用户名
                <input type="text" name="username" id="profile-username" required />
            </label>
            <label>
                邮箱
                <input type="email" name="email" id="profile-email" />
            </label>
        </div>
        <label>
            个人简介
            <textarea name="bio" id="profile-bio" rows="3" placeholder="介绍一下自己…"></textarea>
        </label>
        <button type="submit">💾 保存修改</button>
    </form>
</section>

<!-- 修改密码 -->
<section class="settings-section">
    <h3>🔒 修改密码</h3>
    <form id="form-password">
        <div class="grid">
            <label>
                当前密码
                <input type="password" name="old_password" required />
            </label>
            <label>
                新密码
                <input type="password" name="new_password" required minlength="6" />
            </label>
            <label>
                确认新密码
                <input type="password" name="confirm_password" required minlength="6" />
            </label>
        </div>
        <button type="submit">🔄 更新密码</button>
    </form>
</section>

<!-- 通知设置 -->
<section class="settings-section">
    <h3>🔔 通知偏好</h3>
    <form id="form-notifications">
        <label>
            <input type="checkbox" name="email_notifications" checked />
            接收邮件通知
        </label>
        <label>
            <input type="checkbox" name="task_completed" checked />
            任务完成时通知
        </label>
        <label>
            <input type="checkbox" name="node_offline" checked />
            节点离线时通知
        </label>
        <button type="submit">💾 保存偏好</button>
    </form>
</section>

<!-- 账户操作 -->
<section class="settings-section">
    <h3>⚠️ 危险操作</h3>
    <p style="color: var(--pico-muted-color);">以下操作不可逆，请谨慎操作。</p>
    <div style="display: flex; gap: 1rem;">
        <button class="secondary" onclick="Auth.logout()">🚪 退出登录</button>
        <button class="outline" style="color: var(--pico-del-color);" onclick="showDeleteAccountConfirm()">🗑️ 删除账户</button>
    </div>
</section>

<script>
    function showDeleteAccountConfirm() {
        Modal.show('🗑️ 删除账户', `
            <p style="color: var(--pico-del-color); font-weight: 600;">⚠️ 此操作不可恢复！</p>
            <p>确定要删除你的账户吗？所有数据将被永久清除。</p>
        `, [{
                text: '取消',
                class: 'secondary',
                click: () => Modal.close()
            },
            {
                text: '确认删除',
                click: () => {
                    Modal.close();
                    Notify.info('请联系管理员删除账户');
                }
            }
        ]);
    }

    // 加载个人信息
    async function loadProfile() {
        try {
            const result = await Auth.get(`${window.API_BASE_URL}/users/profile`);
            if (result.success) {
                const user = result.data;
                document.getElementById('profile-username').value = user.username || '';
                document.getElementById('profile-email').value = user.email || '';
                document.getElementById('profile-bio').value = user.bio || '';
            }
        } catch (e) {
            // 静默失败
        }
    }

    // 保存个人信息
    document.getElementById('form-profile').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            username: form.username.value.trim(),
            email: form.email.value.trim(),
            bio: form.bio.value.trim(),
        };

        const btn = form.querySelector('button[type="submit"]');
        btn.setAttribute('aria-busy', 'true');

        try {
            const result = await Auth.put(`${window.API_BASE_URL}/users/profile`, data);
            if (result.success) {
                Notify.success('个人信息已更新');
                // 更新本地存储的用户名
                if (data.username) localStorage.setItem('username', data.username);
            } else {
                Notify.error(result.message || '更新失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        } finally {
            btn.removeAttribute('aria-busy');
        }
    });

    // 修改密码
    document.getElementById('form-password').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const oldPassword = form.old_password.value;
        const newPassword = form.new_password.value;
        const confirmPassword = form.confirm_password.value;

        if (newPassword !== confirmPassword) {
            Notify.error('两次输入的新密码不一致');
            return;
        }

        if (newPassword.length < 6) {
            Notify.error('新密码长度不能少于6位');
            return;
        }

        const btn = form.querySelector('button[type="submit"]');
        btn.setAttribute('aria-busy', 'true');

        try {
            const result = await Auth.put(`${window.API_BASE_URL}/users/change-password`, {
                old_password: oldPassword,
                new_password: newPassword,
            });
            if (result.success) {
                Notify.success('密码已更新');
                form.reset();
            } else {
                Notify.error(result.message || '密码修改失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        } finally {
            btn.removeAttribute('aria-busy');
        }
    });

    // 保存通知偏好
    document.getElementById('form-notifications').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            email_notifications: form.email_notifications.checked,
            task_completed: form.task_completed.checked,
            node_offline: form.node_offline.checked,
        };

        const btn = form.querySelector('button[type="submit"]');
        btn.setAttribute('aria-busy', 'true');

        try {
            // 保存到本地存储（后端预留接口）
            localStorage.setItem('notification_prefs', JSON.stringify(data));
            Notify.success('通知偏好已保存');
        } catch (e) {
            Notify.error('保存失败');
        } finally {
            btn.removeAttribute('aria-busy');
        }
    });

    // 页面加载时自动加载
    window.dashboardPageInit = loadProfile;
</script>