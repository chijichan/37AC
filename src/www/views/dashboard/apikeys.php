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

    .stat-summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1.1rem;
        margin-bottom: 1.6rem;
    }

    .api-key-card {
        background: var(--ac-surface);
        padding: 1.4rem 1.5rem;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        margin-bottom: 1.1rem;
        transition: box-shadow var(--ac-dur) var(--ac-ease-out);
    }

    .api-key-card:hover {
        box-shadow: var(--ac-shadow-float);
    }

    .key-display {
        display: flex;
        gap: .8rem;
        align-items: center;
        background: var(--ac-bg);
        padding: .65rem 1rem;
        border-radius: var(--ac-radius-input);
        font-family: var(--ac-font-mono);
        margin: .9rem 0;
        font-size: .88rem;
    }

    .key-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        user-select: all;
    }

    .key-reveal {
        word-break: break-all;
        background: var(--ac-pink-50);
        border: 1.5px dashed var(--ac-pink-300);
        padding: .9rem 1rem;
        border-radius: var(--ac-radius-input);
        font-family: var(--ac-font-mono);
        font-size: .85rem;
        margin: 1rem 0 0;
        user-select: all;
        color: var(--ac-pink-700);
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }

    .card-header h4 {
        margin: 0 0 .15rem;
    }

    .card-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: .5rem;
        margin: .5rem 0 0;
        font-size: .88rem;
    }

    .card-meta dt {
        color: var(--ac-ink-500);
        font-size: .75rem;
        margin-bottom: .15rem;
    }

    .card-meta dd {
        margin: 0;
        font-weight: 600;
        color: var(--ac-ink-900);
    }

    .usage-row {
        margin-top: .9rem;
    }

    .usage-row .usage-label {
        display: flex;
        justify-content: space-between;
        font-size: .8rem;
        color: var(--ac-ink-500);
        margin-bottom: .4rem;
    }

    .card-footer {
        display: flex;
        gap: .5rem;
        justify-content: flex-end;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--ac-surface-2);
    }

    .create-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0 1rem;
    }

    .create-form .full-width {
        grid-column: 1 / -1;
    }

    @media (max-width: 600px) {
        .create-form {
            grid-template-columns: 1fr;
        }

        .card-header {
            flex-direction: column;
        }
    }
</style>

<header class="dash-page-head">
    <h2>API 密钥管理</h2>
    <p>生成和管理 API 访问密钥，每个密钥都有独立的使用配额和权限控制。</p>
</header>

<div class="stat-summary" id="key-stats">
    <div class="stat"><span class="stat-value" id="stat-total">--</span><span class="stat-label">总密钥数</span></div>
    <div class="stat"><span class="stat-value" id="stat-active" style="color:var(--ac-success)">--</span><span class="stat-label">活跃</span></div>
    <div class="stat"><span class="stat-value" id="stat-total-usage">--</span><span class="stat-label">总使用次数</span></div>
</div>

<section style="margin-bottom: 1.6rem;">
    <div class="api-key-card">
        <h3 style="margin-bottom:.4rem;">生成新密钥</h3>
        <p style="font-size:.92rem; margin-bottom:1.1rem;">创建后请立即复制并安全保存，关闭提示后将无法再次查看完整密钥。</p>
        <form id="form-create-key">
            <div class="create-form">
                <div class="field full-width">
                    <label>密钥名称</label>
                    <input type="text" name="name" class="input" placeholder="例如：生产环境节点" required maxlength="50" />
                </div>
                <div class="field">
                    <label>权限级别</label>
                    <select name="permission" class="select">
                        <option value="read">只读</option>
                        <option value="write" selected>读写</option>
                        <option value="admin">管理员</option>
                    </select>
                </div>
                <div class="field">
                    <label>最大使用次数</label>
                    <input type="number" name="max_usage" class="input" value="10000" min="0" />
                    <span class="hint">0 表示无限制</span>
                </div>
                <div class="field full-width" style="margin-bottom:0;">
                    <button type="submit" class="btn btn-primary"><i class="ph ph-lock"></i> 生成密钥</button>
                </div>
            </div>
        </form>
    </div>
</section>

<section>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0;">现有密钥</h3>
        <button class="btn btn-ghost btn-sm" onclick="loadKeys()"><i class="ph ph-arrows-clockwise"></i> 刷新</button>
    </div>
    <div id="keys-list">
        <div class="api-key-card"><div class="skeleton" style="height: 100px;"></div></div>
    </div>
</section>

<script>
    var allKeys = [];

    // 确认对话框
    function showConfirm(title, message, onConfirm, danger = false) {
        Modal.show(title, `<p>${message}</p>`, [{
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            },
            {
                text: '确认',
                class: danger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm',
                click: () => {
                    Modal.close();
                    if (onConfirm) onConfirm();
                }
            }
        ]);
    }

    async function loadKeys() {
        const container = document.getElementById('keys-list');
        container.innerHTML = '<div class="api-key-card"><div class="skeleton" style="height: 100px;"></div></div>';

        try {
            const result = await Auth.get(`${window.API_BASE_URL}/api-keys`);
            const keys = result.data || [];
            allKeys = keys;

            // 更新统计
            document.getElementById('stat-total').textContent = keys.length;
            document.getElementById('stat-active').textContent = keys.filter(k => k.status === 'active').length;
            document.getElementById('stat-total-usage').textContent =
                keys.reduce((sum, k) => sum + (k.usage_count || 0), 0).toLocaleString();

            if (!keys.length) {
                container.innerHTML = `
                    <div class="api-key-card empty">
                        <div class="empty-icon"><i class="ph ph-key"></i></div>
                        <h3>暂无 API 密钥</h3>
                        <p>使用上方表单创建你的第一个密钥，开始使用 API 服务。</p>
                    </div>`;
                return;
            }

            container.innerHTML = keys.map(key => {
                const statusMap = {
                    active: '<span class="badge badge-success">活跃</span>',
                    paused: '<span class="badge badge-warning">暂停</span>',
                    revoked: '<span class="badge badge-danger">已撤销</span>',
                };
                const statusBadge = statusMap[key.status] || `<span class="badge badge-neutral">${escapeHtml(key.status)}</span>`;
                const usagePercent = key.max_usage > 0 ? Math.min(100, Math.round((key.usage_count / key.max_usage) * 100)) : 0;
                const usageText = key.max_usage > 0 ?
                    `${key.usage_count.toLocaleString()} / ${key.max_usage.toLocaleString()}` :
                    `${key.usage_count.toLocaleString()} / 无限制`;
                const permissionMap = {
                    read: '只读',
                    write: '读写',
                    admin: '管理员'
                };
                const keyPrefix = `37ac_${key.id}_****`;

                return `
                    <div class="api-key-card" data-key-id="${key.id}">
                        <div class="card-header">
                            <div>
                                <h4>${escapeHtml(key.name)}</h4>
                                <small>创建于 ${escapeHtml(key.created_at || '未知')}</small>
                            </div>
                            ${statusBadge}
                        </div>

                        <div class="key-display">
                            <code class="key-text">${escapeHtml(keyPrefix)}</code>
                        </div>

                        <dl class="card-meta">
                            <div><dt>权限级别</dt><dd>${permissionMap[key.permission] || escapeHtml(key.permission)}</dd></div>
                            <div><dt>使用次数</dt><dd>${escapeHtml(usageText)}</dd></div>
                            <div><dt>最后使用</dt><dd>${escapeHtml(key.last_used_at || '从未使用')}</dd></div>
                            <div><dt>密钥 ID</dt><dd class="mono">${key.id}</dd></div>
                        </dl>

                        ${key.max_usage > 0 ? `
                            <div class="usage-row">
                                <div class="usage-label">
                                    <span>使用进度</span>
                                    <span>${usagePercent}%</span>
                                </div>
                                <span class="prob-bar"><i style="width:${usagePercent}%"></i></span>
                            </div>
                        ` : ''}

                        <div class="card-footer">
                            ${key.status === 'active' ? `
                                <button class="btn btn-ghost btn-sm" onclick="toggleKeyStatus(${key.id}, 'paused')">暂停</button>
                            ` : key.status === 'paused' ? `
                                <button class="btn btn-secondary btn-sm" onclick="toggleKeyStatus(${key.id}, 'active')">启用</button>
                            ` : ''}
                            ${key.status !== 'revoked' ? `
                                <button class="btn btn-ghost btn-sm" onclick="confirmRevokeKey(${key.id})">撤销</button>
                            ` : ''}
                            <button class="btn btn-danger btn-sm" onclick="confirmDeleteKey(${key.id})">删除</button>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            container.innerHTML = '<div class="api-key-card empty"><div class="empty-icon"><i class="ph ph-warning"></i></div><p>加载失败，请检查服务器连接。</p></div>';
        }
    }

    // 复制文本
    function copyText(text, successMsg = '已复制') {
        navigator.clipboard.writeText(text).then(() => {
            Notify.success(successMsg);
        }).catch(() => {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            Notify.success(successMsg);
        });
    }

    // 生成密钥
    document.getElementById('form-create-key').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const name = form.name.value.trim();
        if (!name) {
            Notify.error('请输入密钥名称');
            return;
        }

        const data = {
            name: name,
            permission: form.permission.value,
            max_usage: parseInt(form.max_usage.value) || 0,
        };

        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '生成中…';
        }

        try {
            const result = await Auth.post(`${window.API_BASE_URL}/api-keys`, data);
            if (result.success) {
                form.reset();
                form.max_usage.value = '10000';
                const key = result.data.key;
                Notify.success('密钥创建成功');
                loadKeys();

                Modal.show('密钥创建成功', `
                    <p style="color: var(--ac-danger); font-weight: 600;">请立即复制并安全保存此密钥，关闭后将无法再次查看。</p>
                    <div class="key-reveal" id="new-key-display">${escapeHtml(key)}</div>
                `, [{
                        text: '复制密钥',
                        class: 'btn btn-primary btn-sm',
                        click: () => {
                            const keyText = document.getElementById('new-key-display');
                            if (keyText) copyText(keyText.textContent, '密钥已复制到剪贴板');
                        }
                    },
                    {
                        text: '我已安全保存',
                        class: 'btn btn-ghost btn-sm',
                        click: () => Modal.close()
                    }
                ]);
            } else {
                Notify.error(result.message || '生成失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="ph ph-lock"></i> 生成密钥';
            }
        }
    });

    // 切换密钥状态
    async function toggleKeyStatus(keyId, newStatus) {
        const statusText = newStatus === 'active' ? '启用' : '暂停';
        try {
            const result = await Auth.put(`${window.API_BASE_URL}/api-keys/${keyId}`, {
                status: newStatus
            });
            if (result.success) {
                Notify.success(`密钥已${statusText}`);
                loadKeys();
            } else {
                Notify.error(result.message || '操作失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    }

    // 确认撤销
    function confirmRevokeKey(keyId) {
        const key = allKeys.find(k => k.id === keyId);
        const name = key ? escapeHtml(key.name) : `#${keyId}`;
        showConfirm(
            '撤销密钥',
            `确定要撤销密钥「${name}」吗？撤销后该密钥将无法使用，但可以重新启用。`,
            () => revokeKey(keyId)
        );
    }

    async function revokeKey(keyId) {
        try {
            const result = await Auth.post(`${window.API_BASE_URL}/api-keys/${keyId}/revoke`);
            if (result.success) {
                Notify.success('密钥已撤销');
                loadKeys();
            } else {
                Notify.error(result.message || '操作失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    }

    // 确认删除
    function confirmDeleteKey(keyId) {
        const key = allKeys.find(k => k.id === keyId);
        const name = key ? escapeHtml(key.name) : `#${keyId}`;
        showConfirm(
            '删除密钥',
            `确定要永久删除密钥「${name}」吗？此操作不可恢复。`,
            () => deleteKey(keyId),
            true
        );
    }

    async function deleteKey(keyId) {
        try {
            const result = await Auth.del(`${window.API_BASE_URL}/api-keys/${keyId}`);
            if (result.success) {
                Notify.success('密钥已永久删除');
                loadKeys();
            } else {
                Notify.error(result.message || '操作失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    }

    // 页面加载时自动加载，将 Promise 存入全局变量供 layout.php 等待
    window.dashboardPageInit = () => {
        window.__pageLoadPromise = loadKeys();
    };
</script>
