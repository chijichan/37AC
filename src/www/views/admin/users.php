<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/admin/layout.php';
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

    .toolbar {
        display: flex;
        gap: .6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }

    .toolbar .input {
        flex: 1;
        min-width: 200px;
    }

    .user-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .9rem;
    }

    .user-table th,
    .user-table td {
        text-align: left;
        padding: .65rem .7rem;
        border-bottom: 1px solid var(--ac-surface-2);
        vertical-align: middle;
    }

    .user-table th {
        color: var(--ac-ink-500);
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .03em;
    }

    .user-table .mono {
        font-family: var(--ac-font-mono);
        font-size: .82rem;
    }

    .pager {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        font-size: .88rem;
        color: var(--ac-ink-500);
    }

    .row-actions {
        display: flex;
        gap: .35rem;
        flex-wrap: wrap;
    }

    .modal-form .field {
        margin-bottom: .8rem;
    }
</style>

<header class="dash-page-head">
    <h2>用户管理</h2>
    <p>管理用户账号、角色与启用状态。</p>
</header>

<div class="toolbar">
    <input type="text" id="user-keyword" class="input" placeholder="搜索用户名 / 邮箱" />
    <button class="btn btn-secondary btn-sm" onclick="loadUsers(1)"><i class="ph ph-funnel"></i> 搜索</button>
    <button class="btn btn-primary btn-sm" onclick="showCreateUserModal()"><i class="ph-bold ph-plus"></i> 新增用户</button>
    <button class="btn btn-ghost btn-sm" onclick="loadUsers()"><i class="ph ph-arrows-clockwise"></i> 刷新</button>
</div>

<div class="card" style="padding:1.2rem 1.3rem;">
    <div id="users-wrap">
        <div class="skeleton" style="height: 120px;"></div>
    </div>
</div>

<script>
    var usersState = { page: 1, per_page: 20, total_pages: 1 };
    var currentUsers = [];

    async function loadUsers(page) {
        if (page) usersState.page = page;
        const wrap = document.getElementById('users-wrap');
        wrap.innerHTML = '<div class="skeleton" style="height: 120px;"></div>';
        const keyword = document.getElementById('user-keyword').value.trim();
        const url = `${window.API_BASE_URL}/admin/users?page=${usersState.page}&per_page=${usersState.per_page}` +
            (keyword ? `&keyword=${encodeURIComponent(keyword)}` : '');
        try {
            const result = await Auth.get(url);
            const data = result.data || {};
            const users = data.users || [];
            currentUsers = users;
            usersState.total_pages = data.total_pages || 1;
            if (!users.length) {
                wrap.innerHTML = '<p style="text-align:center;color:var(--ac-ink-500);">没有找到用户</p>';
                return;
            }
            wrap.innerHTML = `
                <table class="user-table">
                    <thead><tr>
                        <th>ID</th><th>用户名</th><th>邮箱</th><th>角色</th><th>状态</th><th>注册时间</th><th>操作</th>
                    </tr></thead>
                    <tbody>
                        ${users.map((u) => `
                            <tr>
                                <td class="mono">${u.id}</td>
                                <td>${escapeHtml(u.username || '-')}</td>
                                <td>${escapeHtml(u.email || '-')}</td>
                                <td>${u.role === 'admin' ? '<span class="badge badge-pink">管理员</span>' : '<span class="badge badge-neutral">普通用户</span>'}</td>
                                <td>${Number(u.status) === 1 ? '<span class="badge badge-success">启用</span>' : '<span class="badge badge-danger">禁用</span>'}</td>
                                <td class="mono">${escapeHtml(u.created_at || '-')}</td>
                                <td>
                                    <div class="row-actions">
                                        <button class="btn btn-secondary btn-sm" onclick="showEditUserModal(${u.id})">编辑</button>
                                        <button class="btn btn-ghost btn-sm" onclick="toggleUserStatus(${u.id}, ${Number(u.status) === 1 ? 0 : 1})">
                                            ${Number(u.status) === 1 ? '禁用' : '启用'}
                                        </button>
                                        <button class="btn btn-danger btn-sm" onclick="confirmDeleteUser(${u.id})">删除</button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div class="pager">
                    <span>共 ${data.total ?? users.length} 个用户，第 ${data.page ?? usersState.page} / ${usersState.total_pages} 页</span>
                    <span>
                        <button class="btn btn-ghost btn-sm" ${usersState.page <= 1 ? 'disabled' : ''} onclick="loadUsers(${usersState.page - 1})">上一页</button>
                        <button class="btn btn-ghost btn-sm" ${usersState.page >= usersState.total_pages ? 'disabled' : ''} onclick="loadUsers(${usersState.page + 1})">下一页</button>
                    </span>
                </div>`;
        } catch (e) {
            wrap.innerHTML = '<p style="text-align:center;color:var(--ac-danger);">加载失败（可能权限不足或服务器未就绪）</p>';
        }
    }

    function showCreateUserModal() {
        const body = `
            <form id="form-create-user">
                <div class="field"><label>用户名</label><input type="text" name="username" class="input" required maxlength="50" /></div>
                <div class="field"><label>密码</label><input type="password" name="password" class="input" required minlength="6" /></div>
                <div class="field"><label>邮箱（可选）</label><input type="email" name="email" class="input" /></div>
                <div class="field" style="margin-bottom:0;"><label>角色</label>
                    <select name="role" class="select"><option value="user" selected>普通用户</option><option value="admin">管理员</option></select>
                </div>
            </form>`;
        Modal.show('新增用户', body, [
            { text: '取消', class: 'btn btn-ghost btn-sm', click: () => Modal.close() },
            { text: '创建', class: 'btn btn-primary btn-sm', click: (e) => createUser(e.target) }
        ]);
    }

    async function createUser(btn) {
        const form = document.getElementById('form-create-user');
        if (!form) return;
        const data = {
            username: form.username.value.trim(),
            password: form.password.value,
            email: form.email.value.trim(),
            role: form.role.value,
        };
        if (!data.username || !data.password) { Notify.error('用户名和密码不能为空'); return; }
        if (btn) { btn.disabled = true; btn.textContent = '创建中…'; }
        try {
            const result = await Auth.post(`${window.API_BASE_URL}/admin/users`, data);
            if (result.success) {
                Notify.success('用户创建成功');
                Modal.close();
                loadUsers(1);
            } else {
                Notify.error(result.message || '创建失败');
            }
        } catch (e) { Notify.error('网络错误'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = '创建'; } }
    }

    function showEditUserModal(id) {
        const user = currentUsers.find((u) => u.id === id);
        if (!user) return;
        const body = `
            <form id="form-edit-user">
                <div class="field"><label>用户名</label><input type="text" class="input" value="${escapeHtml(user.username || '')}" disabled /></div>
                <div class="field"><label>邮箱</label><input type="email" name="email" class="input" value="${escapeHtml(user.email || '')}" /></div>
                <div class="field"><label>角色</label>
                    <select name="role" class="select">
                        <option value="user" ${user.role !== 'admin' ? 'selected' : ''}>普通用户</option>
                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>管理员</option>
                    </select>
                </div>
                <div class="field" style="margin-bottom:0;"><label>状态</label>
                    <select name="status" class="select">
                        <option value="1" ${Number(user.status) === 1 ? 'selected' : ''}>启用</option>
                        <option value="0" ${Number(user.status) === 0 ? 'selected' : ''}>禁用</option>
                    </select>
                </div>
            </form>`;
        Modal.show('编辑用户', body, [
            { text: '取消', class: 'btn btn-ghost btn-sm', click: () => Modal.close() },
            { text: '保存', class: 'btn btn-primary btn-sm', click: (e) => saveUser(id, e.target) }
        ]);
    }

    async function saveUser(id, btn) {
        const form = document.getElementById('form-edit-user');
        if (!form) return;
        const data = {
            email: form.email.value.trim(),
            role: form.role.value,
            status: parseInt(form.status.value, 10),
        };
        if (btn) { btn.disabled = true; btn.textContent = '保存中…'; }
        try {
            const result = await Auth.put(`${window.API_BASE_URL}/admin/users/${id}`, data);
            if (result.success) {
                Notify.success('用户已更新');
                Modal.close();
                loadUsers();
            } else {
                Notify.error(result.message || '更新失败');
            }
        } catch (e) { Notify.error('网络错误'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = '保存'; } }
    }

    async function toggleUserStatus(id, status) {
        try {
            const result = await Auth.put(`${window.API_BASE_URL}/admin/users/${id}/status`, { status });
            if (result.success) {
                Notify.success(status === 1 ? '已启用' : '已禁用');
                loadUsers();
            } else {
                Notify.error(result.message || '操作失败');
            }
        } catch (e) { Notify.error('网络错误'); }
    }

    function confirmDeleteUser(id) {
        const user = currentUsers.find((u) => u.id === id);
        const name = user ? user.username : `#${id}`;
        Modal.show('删除用户', `<p>确定要删除用户 <b>${escapeHtml(name)}</b> 吗？此操作不可恢复。</p>`, [
            { text: '删除', class: 'btn btn-danger btn-sm', click: () => { Modal.close(); deleteUser(id); } },
            { text: '取消', class: 'btn btn-ghost btn-sm', click: () => Modal.close() }
        ]);
    }

    async function deleteUser(id) {
        try {
            const result = await Auth.del(`${window.API_BASE_URL}/admin/users/${id}`);
            if (result.success) {
                Notify.success('用户已删除');
                loadUsers();
            } else {
                Notify.error(result.message || '删除失败');
            }
        } catch (e) { Notify.error('网络错误'); }
    }

    window.dashboardPageInit = function() {
        window.__pageLoadPromise = loadUsers(1);
        const input = document.getElementById('user-keyword');
        if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') loadUsers(1); });
    };
</script>
