<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<style>
    .api-key-card {
        background: var(--pico-card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        margin-bottom: 1.5rem;
        transition: box-shadow 0.2s;
    }

    .api-key-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .key-display {
        display: flex;
        gap: 1rem;
        align-items: center;
        background: var(--pico-card-sectioning-background-color);
        padding: 0.75rem 1rem;
        border-radius: var(--pico-border-radius);
        font-family: monospace;
        margin: 1rem 0;
        font-size: 0.9rem;
    }

    .key-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        user-select: all;
    }

    .key-actions {
        display: flex;
        gap: 0.25rem;
        flex-shrink: 0;
    }

    .key-actions button {
        padding: 0.3rem 0.5rem;
        font-size: 0.8rem;
        line-height: 1;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 5rem;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .status-badge.active {
        background: var(--pico-ins-color);
        color: #fff;
    }

    .status-badge.paused {
        background: var(--pico-secondary-background);
        color: var(--pico-secondary-inverse);
    }

    .status-badge.revoked {
        background: var(--pico-del-color);
        color: #fff;
    }

    .key-reveal {
        word-break: break-all;
        background: var(--pico-card-sectioning-background-color);
        padding: 1rem;
        border-radius: var(--pico-border-radius);
        font-family: monospace;
        font-size: 0.85rem;
        margin: 1rem 0;
        user-select: all;
    }

    .stat-summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }

    .stat-summary article {
        text-align: center;
        padding: 1.2rem;
    }

    .stat-summary h3 {
        margin: 0;
        font-size: 1.8rem;
    }

    .stat-summary small {
        color: var(--pico-muted-color);
    }

    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: var(--pico-muted-color);
    }

    .empty-state h3 {
        margin-bottom: 0.5rem;
    }

    .progress-bar {
        height: 6px;
        border-radius: 3px;
        background: var(--pico-card-sectioning-background-color);
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .progress-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s;
    }

    .progress-bar-fill.low {
        background: var(--pico-ins-color);
    }

    .progress-bar-fill.medium {
        background: #f0ad4e;
    }

    .progress-bar-fill.high {
        background: var(--pico-del-color);
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }

    .card-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
    }

    .card-meta dt {
        color: var(--pico-muted-color);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .card-meta dd {
        margin: 0;
        font-weight: 500;
    }

    .card-footer {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--pico-muted-border-color);
    }

    .create-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .create-form .full-width {
        grid-column: 1 / -1;
    }

    .create-form button {
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

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>🔑 API密钥管理</h1>
    <p>生成和管理你的 API 访问密钥。每个密钥都有独立的使用配额和权限控制。</p>
</header>

<!-- 统计概览 -->
<div class="stat-summary" id="key-stats">
    <article>
        <h3 id="stat-total">--</h3><small>总密钥数</small>
    </article>
    <article>
        <h3 id="stat-active" style="color: var(--pico-ins-color);">--</h3><small>活跃</small>
    </article>
    <article>
        <h3 id="stat-total-usage">--</h3><small>总使用次数</small>
    </article>
</div>

<!-- 生成新密钥 -->
<section style="margin-bottom: 2rem;">
    <article class="api-key-card">
        <h3>生成新密钥</h3>
        <p>为你的应用生成新的 API 密钥。创建后请立即复制并安全保存，关闭后将无法再次查看完整密钥。</p>
        <form id="form-create-key">
            <div class="create-form">
                <label class="full-width">
                    密钥名称
                    <input type="text" name="name" placeholder="例如：生产环境节点" required maxlength="50" />
                </label>
                <label>
                    权限级别
                    <select name="permission">
                        <option value="read">只读</option>
                        <option value="write" selected>读写</option>
                        <option value="admin">管理员</option>
                    </select>
                </label>
                <label>
                    最大使用次数
                    <input type="number" name="max_usage" value="10000" min="0" />
                    <small>0 表示无限制</small>
                </label>
                <button type="submit">🔐 生成密钥</button>
            </div>
        </form>
    </article>
</section>

<!-- 现有密钥列表 -->
<section>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2 style="margin: 0;">现有密钥</h2>
        <button class="outline secondary" onclick="loadKeys()" style="padding: 0.3rem 0.8rem;">🔄 刷新</button>
    </div>
    <div id="keys-list">
        <article class="api-key-card">
            <p style="text-align:center;"><span aria-busy="true"></span> 加载中…</p>
        </article>
    </div>
</section>

<?php $warnIconSvg = file_get_contents(ROOT_PATH . '/views/components/icons/warn.php'); ?>
<script>
    var pendingAction = null;
    var WARN_ICON_SVG = <?php echo json_encode($warnIconSvg); ?>;

    // 确认对话框（使用 PicoCSS 模态框）
    function showConfirm(title, message, onConfirm) {
        Modal.show(title, `<p>${message}</p>`, [{
                text: '取消',
                class: 'secondary',
                click: () => Modal.close()
            },
            {
                text: '确认',
                click: () => {
                    Modal.close();
                    if (onConfirm) onConfirm();
                }
            }
        ]);
    }

    async function loadKeys() {
        const container = document.getElementById('keys-list');
        container.innerHTML = '<article class="api-key-card"><p style="text-align:center;"><span aria-busy="true"></span> 加载中…</p></article>';

        try {
            const result = await Auth.get(`${window.API_BASE_URL}/api-keys`);
            const keys = result.data || [];

            // 更新统计
            const total = keys.length;
            const activeCount = keys.filter(k => k.status === 'active').length;
            const totalUsage = keys.reduce((sum, k) => sum + (k.usage_count || 0), 0);
            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-active').textContent = activeCount;
            document.getElementById('stat-total-usage').textContent = totalUsage.toLocaleString();

            if (!keys.length) {
                container.innerHTML = `
                    <article class="api-key-card empty-state">
                        <h3>🔑 暂无 API 密钥</h3>
                        <p>使用上方表单创建你的第一个密钥，开始使用 API 服务。</p>
                    </article>
                `;
                return;
            }

            container.innerHTML = keys.map(key => {
                const statusMap = {
                    active: '活跃',
                    paused: '暂停',
                    revoked: '已撤销'
                };
                const statusText = statusMap[key.status] || key.status;
                const usagePercent = key.max_usage > 0 ? Math.min(100, Math.round((key.usage_count / key.max_usage) * 100)) : 0;
                const usageText = key.max_usage > 0 ? `${key.usage_count.toLocaleString()} / ${key.max_usage.toLocaleString()}` : `${key.usage_count.toLocaleString()} / 无限制`;
                const permissionMap = {
                    read: '只读',
                    write: '读写',
                    admin: '管理员'
                };
                const progressClass = usagePercent < 60 ? 'low' : usagePercent < 85 ? 'medium' : 'high';
                const keyPrefix = `37ac_${key.id}_****`;

                return `
                    <article class="api-key-card" data-key-id="${key.id}">
                        <div class="card-header">
                            <div>
                                <h4 style="margin: 0;">${key.name}</h4>
                                <small style="color: var(--pico-muted-color);">创建于 ${key.created_at || '未知'}</small>
                            </div>
                            <span class="status-badge ${key.status}">${statusText}</span>
                        </div>

                        <div class="key-display">
                            <code class="key-text">${keyPrefix}</code>
                        </div>

                        <dl class="card-meta">
                            <div><dt>权限级别</dt><dd>${permissionMap[key.permission] || key.permission}</dd></div>
                            <div><dt>使用次数</dt><dd>${usageText}</dd></div>
                            <div><dt>最后使用</dt><dd>${key.last_used_at || '从未使用'}</dd></div>
                            <div><dt>密钥ID</dt><dd><small>${key.id}</small></dd></div>
                        </dl>

                        ${key.max_usage > 0 ? `
                            <div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                                    <span>使用进度</span>
                                    <span>${usagePercent}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-bar-fill ${progressClass}" style="width: ${usagePercent}%"></div>
                                </div>
                            </div>
                        ` : ''}

                        <div class="card-footer">
                            ${key.status === 'active' ? `
                                <button class="secondary outline" onclick="toggleKeyStatus(${key.id}, 'paused')">⏸ 暂停</button>
                            ` : key.status === 'paused' ? `
                                <button class="secondary outline" onclick="toggleKeyStatus(${key.id}, 'active')">▶ 启用</button>
                            ` : ''}
                            ${key.status !== 'revoked' ? `
                                <button class="outline" style="color: var(--pico-del-color); border-color: var(--pico-del-color);" onclick="confirmRevokeKey(${key.id}, '${key.name}')">撤销</button>
                            ` : ''}
                            <button class="outline" style="color: var(--pico-del-color); border-color: var(--pico-del-color);" onclick="confirmDeleteKey(${key.id}, '${key.name}')">删除</button>
                        </div>
                    </article>
                `;
            }).join('');
        } catch (e) {
            container.innerHTML = '<article class="api-key-card"><p style="text-align:center;color:var(--pico-del-color);">加载失败，请检查服务器连接</p></article>';
        }
    }

    // 复制文本
    function copyText(text, successMsg = '已复制') {
        navigator.clipboard.writeText(text).then(() => {
            Notify.success(successMsg);
        }).catch(() => {
            // 降级方案
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
        btn.setAttribute('aria-busy', 'true');
        btn.textContent = '生成中…';

        try {
            const result = await Auth.post(`${window.API_BASE_URL}/api-keys`, data);
            if (result.success) {
                form.reset();
                form.max_usage.value = '10000';
                const key = result.data.key;
                Notify.success('密钥创建成功！');
                loadKeys();

                // 使用 PicoCSS 模态框显示新密钥
                Modal.show('✅ 密钥创建成功', `
                    <p style="color: var(--pico-del-color); font-weight: 600;">${WARN_ICON_SVG} 请立即复制并安全保存此密钥，关闭后将无法再次查看完整密钥！</p>
                    <div class="key-reveal" id="new-key-display">${key}</div>
                `, [{
                        text: '📋 复制密钥',
                        click: () => {
                            const keyText = document.getElementById('new-key-display');
                            if (keyText) copyText(keyText.textContent, '✓ 密钥已复制到剪贴板');
                        }
                    },
                    {
                        text: '我已安全保存',
                        class: 'secondary',
                        click: () => Modal.close()
                    }
                ]);
            } else {
                Notify.error(result.message || '生成失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            btn.removeAttribute('aria-busy');
            btn.textContent = '🔐 生成密钥';
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
    function confirmRevokeKey(keyId, keyName) {
        showConfirm(
            WARN_ICON_SVG + ' 撤销密钥',
            `确定要撤销密钥「${keyName}」吗？撤销后该密钥将无法使用，但可以重新启用。`,
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
    function confirmDeleteKey(keyId, keyName) {
        showConfirm(
            '🗑️ 删除密钥',
            `确定要永久删除密钥「${keyName}」吗？此操作不可恢复！`,
            () => deleteKey(keyId)
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

    // 页面加载时自动加载
    loadKeys();
</script>