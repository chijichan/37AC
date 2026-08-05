<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<style>
    .dash-page-head {
        margin-bottom: 1.6rem;
    }

    .dash-page-head h2 {
        margin-bottom: .2rem;
    }

    .settings-section {
        background: var(--ac-surface);
        padding: 1.4rem 1.5rem;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        margin-bottom: 1.3rem;
    }

    .settings-section h3 {
        display: flex;
        align-items: center;
        gap: .45rem;
        margin: 0 0 1.1rem;
        padding-bottom: .75rem;
        border-bottom: 1px solid var(--ac-surface-2);
    }

    .settings-section h3 i {
        color: var(--ac-pink-500);
    }

    .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0 1rem;
    }

    .checkbox-row {
        display: flex;
        align-items: center;
        gap: .5rem;
        font-size: .95rem;
        font-weight: 600;
        color: var(--ac-ink-900);
        cursor: pointer;
        padding: .35rem 0;
        width: fit-content;
    }

    .checkbox-row input[type="checkbox"] {
        width: 18px;
        height: 18px;
        accent-color: var(--ac-pink-600);
        cursor: pointer;
    }

    .danger-zone {
        display: flex;
        gap: .8rem;
        flex-wrap: wrap;
    }

    @media (max-width: 640px) {
        .form-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<header class="dash-page-head">
    <h2>设置</h2>
    <p>管理你的账户设置和偏好。</p>
</header>

<!-- 个人信息 -->
<section class="settings-section">
    <h3><i class="ph ph-user"></i>个人信息</h3>
    <form id="form-profile">
        <div class="form-grid">
            <div class="field">
                <label>用户名</label>
                <input type="text" name="username" id="profile-username" class="input" required />
            </div>
            <div class="field">
                <label>邮箱</label>
                <input type="email" name="email" id="profile-email" class="input" />
            </div>
        </div>
        <div class="field">
            <label>个人简介</label>
            <textarea name="bio" id="profile-bio" class="textarea" rows="3" placeholder="介绍一下自己…"></textarea>
        </div>
        <button type="submit" class="btn btn-primary"><i class="ph ph-floppy-disk"></i> 保存修改</button>
    </form>
</section>

<!-- 修改密码 -->
<section class="settings-section">
    <h3><i class="ph ph-lock"></i>修改密码</h3>
    <form id="form-password">
        <div class="form-grid">
            <div class="field">
                <label>当前密码</label>
                <input type="password" name="old_password" class="input" required />
            </div>
            <div class="field">
                <label>新密码</label>
                <input type="password" name="new_password" class="input" required minlength="6" />
            </div>
            <div class="field">
                <label>确认新密码</label>
                <input type="password" name="confirm_password" class="input" required minlength="6" />
            </div>
        </div>
        <button type="submit" class="btn btn-primary"><i class="ph ph-arrows-clockwise"></i> 更新密码</button>
    </form>
</section>

<!-- 通知设置 -->
<section class="settings-section">
    <h3><i class="ph ph-bell"></i>通知偏好</h3>
    <form id="form-notifications">
        <label class="checkbox-row">
            <input type="checkbox" name="email_notifications" checked />
            接收邮件通知
        </label>
        <label class="checkbox-row">
            <input type="checkbox" name="task_completed" checked />
            任务完成时通知
        </label>
        <label class="checkbox-row">
            <input type="checkbox" name="node_offline" checked />
            节点离线时通知
        </label>
        <div style="margin-top: .9rem;">
            <button type="submit" class="btn btn-primary"><i class="ph ph-floppy-disk"></i> 保存偏好</button>
        </div>
    </form>
</section>

<!-- 账户操作 -->
<section class="settings-section">
    <h3><i class="ph ph-warning"></i>危险操作</h3>
    <p style="color: var(--ac-ink-500); font-size: .92rem; margin-bottom: 1rem;">以下操作不可逆，请谨慎操作。</p>
    <div class="danger-zone">
        <button class="btn btn-ghost" onclick="Auth.logout()">退出登录</button>
        <button class="btn btn-danger" onclick="showDeleteAccountConfirm()">删除账户</button>
    </div>
</section>

<script>
    function showDeleteAccountConfirm() {
        Modal.show('删除账户', `
            <p style="color: var(--ac-danger); font-weight: 600;">此操作不可恢复。</p>
            <p>确定要删除你的账户吗？所有数据将被永久清除。</p>
        `, [{
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            },
            {
                text: '确认删除',
                class: 'btn btn-danger btn-sm',
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
        btn.disabled = true;

        try {
            const result = await Auth.put(`${window.API_BASE_URL}/users/profile`, data);
            if (result.success) {
                Notify.success('个人信息已更新');
                if (data.username) localStorage.setItem('username', data.username);
            } else {
                Notify.error(result.message || '更新失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        } finally {
            btn.disabled = false;
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
            Notify.error('新密码长度不能少于 6 位');
            return;
        }

        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;

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
            btn.disabled = false;
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
        btn.disabled = true;

        try {
            // 保存到本地存储（后端预留接口）
            localStorage.setItem('notification_prefs', JSON.stringify(data));
            Notify.success('通知偏好已保存');
        } catch (e) {
            Notify.error('保存失败');
        } finally {
            btn.disabled = false;
        }
    });

    // 页面加载时自动加载，将 Promise 存入全局变量供 layout.php 等待
    window.dashboardPageInit = () => {
        window.__pageLoadPromise = loadProfile();
    };
</script>
