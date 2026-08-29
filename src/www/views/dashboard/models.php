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

    .model-card {
        background: var(--ac-surface);
        padding: 1.3rem 1.4rem;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        margin-bottom: 1.1rem;
    }

    .model-card .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }

    .model-card h4 {
        margin: 0 0 .15rem;
    }

    .model-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: .5rem;
        margin-top: .9rem;
        font-size: .88rem;
    }

    .model-meta dt {
        color: var(--ac-ink-500);
        font-size: .75rem;
        margin-bottom: .15rem;
    }

    .model-meta dd {
        margin: 0;
        font-weight: 600;
        color: var(--ac-ink-900);
        word-break: break-all;
    }

    .model-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .9rem;
    }

    .model-table th,
    .model-table td {
        text-align: left;
        padding: .6rem .7rem;
        border-bottom: 1px solid var(--ac-surface-2);
        vertical-align: top;
    }

    .model-table th {
        color: var(--ac-ink-500);
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .03em;
    }

    .model-table .mono {
        font-family: var(--ac-font-mono);
        font-size: .8rem;
        word-break: break-all;
    }

    .create-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0 1rem;
    }

    .create-form .full-width {
        grid-column: 1 / -1;
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

    /* 操作列：下拉选择操作 */
    .row-action-dropdown {
        position: relative;
        display: inline-block;
    }

    .row-action-menu {
        position: absolute;
        right: 0;
        top: calc(100% + 4px);
        min-width: 120px;
        background: var(--ac-surface);
        border: 1px solid var(--ac-ink-100);
        border-radius: var(--ac-radius-input);
        box-shadow: var(--ac-shadow-float);
        padding: .35rem;
        z-index: var(--ac-z-dropdown);
    }

    .row-action-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: .45rem .7rem;
        border: none;
        background: none;
        border-radius: 8px;
        font-size: .9rem;
        font-weight: 600;
        cursor: pointer;
        color: var(--ac-ink-700);
    }

    .row-action-item:hover {
        background: var(--ac-pink-50);
        color: var(--ac-pink-600);
    }

    .row-action-item.danger:hover {
        background: var(--ac-danger-bg, #fdecec);
        color: var(--ac-danger);
    }

    @media (max-width: 600px) {
        .create-form {
            grid-template-columns: 1fr;
        }
    }
</style>

<header class="dash-page-head">
    <h2>模型管理</h2>
    <p>管理识别模型，节点启动时会自动拉取并更新到当前激活的本地模型。</p>
</header>

<section style="margin-bottom:1.6rem;">
    <div class="model-card">
        <div class="card-header">
            <div>
                <h4>当前可用模型</h4>
                <small>来自服务端 GET /models，公开可读</small>
            </div>
            <button class="btn btn-ghost btn-sm" onclick="loadPublicModels()"><i class="ph ph-arrows-clockwise"></i> 刷新</button>
        </div>
        <div id="public-models" class="model-meta">
            <div class="skeleton" style="height: 60px;"></div>
        </div>
    </div>
</section>

<section id="admin-panel" style="display:none;">
    <div class="model-card">
        <h3 style="margin-bottom:.4rem;">新增模型</h3>
        <p style="font-size:.92rem; margin-bottom:1.1rem;">填写模型标识、展示名、类型、版本与下载信息；勾选“激活”可立即作为该模型的当前版本。</p>
        <form id="form-create-model">
            <div class="create-form">
                <div class="field">
                    <label>模型标识（model_id）</label>
                    <input type="text" name="model_id" class="input" placeholder="如 37ac" value="37ac" required maxlength="50" />
                </div>
                <div class="field">
                    <label>展示名称</label>
                    <input type="text" name="display_name" class="input" placeholder="如 37ac 本地模型" maxlength="100" />
                </div>
                <div class="field">
                    <label>类型</label>
                    <select name="type" class="select">
                        <option value="local" selected>local（本地）</option>
                        <option value="llm">llm（大模型）</option>
                    </select>
                </div>
                <div class="field">
                    <label>版本号</label>
                    <input type="text" name="version" class="input" placeholder="如 0.1.0" required maxlength="64" />
                </div>
                <div class="field full-width">
                    <label>配置文件下载地址（config.json）</label>
                    <input type="url" name="config_url" class="input" placeholder="https://huggingface.co/xxx/resolve/main/config.json" required />
                </div>
                <div class="field full-width">
                    <label>配置 SHA-256（可选）</label>
                    <input type="text" name="config_hash" class="input mono" placeholder="64 位十六进制哈希" maxlength="64" />
                </div>
                <div class="field">
                    <label class="checkbox-row" for="model-activate" style="font-weight:600;">
                        <input type="checkbox" id="model-activate" name="activate" checked />
                        <span>创建后立即激活（停用同名旧版本）</span>
                    </label>
                </div>
                <div class="field full-width">
                    <label>说明</label>
                    <textarea name="notes" class="input" rows="2" placeholder="可选"></textarea>
                </div>
                <div class="field full-width" style="margin-bottom:0;">
                    <button type="submit" class="btn btn-primary"><i class="ph-bold ph-plus"></i> 新增模型</button>
                </div>
            </div>
        </form>
    </div>

    <div class="model-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:.8rem;">
            <h3 style="margin:0;">模型列表</h3>
            <button class="btn btn-ghost btn-sm" onclick="loadModels()"><i class="ph ph-arrows-clockwise"></i> 刷新</button>
        </div>
        <div id="models-wrap">
            <div class="skeleton" style="height: 120px;"></div>
        </div>
    </div>
</section>

<script>
    var allModels = [];

    async function loadPublicModels() {
        const container = document.getElementById('public-models');
        container.innerHTML = '<div class="skeleton" style="height: 60px;"></div>';
        try {
            const resp = await fetch(`${window.API_BASE_URL}/models`);
            const data = await resp.json();
            const models = data.models || [];
            if (!models.length) {
                container.innerHTML = '<p>暂无可用模型</p>';
                return;
            }
            container.innerHTML = models.map((m) => `
                <div>
                    <dt>${escapeHtml(m.name)}</dt>
                    <dd>${escapeHtml(m.id)}${m.version ? ' · v' + escapeHtml(m.version) : ''}</dd>
                    ${m.config_url ? `<dd class="mono">config: ${escapeHtml(m.config_url.slice(0, 40))}…</dd>` : ''}
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = '<p>加载失败，请检查服务器连接</p>';
        }
    }

    function isAdmin() {
        const user = window.Auth ? Auth.getUser() : null;
        return !!(user && user.role === 'admin');
    }

    async function loadModels() {
        const wrap = document.getElementById('models-wrap');
        if (!isAdmin()) return;
        wrap.innerHTML = '<div class="skeleton" style="height: 120px;"></div>';
        try {
            const result = await Auth.get(`${window.API_BASE_URL}/models/admin`);
            const models = result.models || [];
            allModels = models;
            if (!models.length) {
                wrap.innerHTML = '<p>还没有模型，请先新增。</p>';
                return;
            }
            wrap.innerHTML = `
                <table class="model-table">
                    <thead><tr>
                        <th>ID</th><th>名称</th><th>展示名称</th><th>类型</th><th>版本</th><th>状态</th>
                        <th>配置哈希</th><th>说明</th><th>操作</th>
                    </tr></thead>
                    <tbody>
                        ${models.map((m) => `
                            <tr>
                                <td class="mono">${escapeHtml(m.id)}</td>
                                <td class="mono">${escapeHtml(m.model_id)}</td>
                                <td class="mono">${escapeHtml(m.display_name || '-')}</td>
                                <td><span class="badge ${m.type === 'llm' ? 'badge-mint' : 'badge-pink'}">${escapeHtml(m.type || 'local')}</span></td>
                                <td class="mono">v${escapeHtml(m.version)}</td>
                                <td>${m.status === 'active' ? '<span class="badge badge-success">激活</span>' : '<span class="badge badge-neutral">停用</span>'}</td>
                                <td class="mono">${escapeHtml((m.config_hash || '-').slice(0, 16))}</td>
                                <td>${escapeHtml(m.notes || '-')}</td>
                                <td>
                                    <div class="row-action-dropdown">
                                        <button type="button" class="btn btn-secondary btn-sm row-action-toggle" onclick="toggleRowMenu(this)">
                                            <i class="ph ph-dots-three-vertical"></i> 操作
                                        </button>
                                        <div class="row-action-menu" hidden>
                                            ${m.status !== 'active' ? `<button type="button" class="row-action-item" onclick="activateModel(${m.id})">激活</button>` : ''}
                                            <button type="button" class="row-action-item" onclick="editModel(${m.id})">修改</button>
                                            <button type="button" class="row-action-item danger" onclick="confirmDeleteModel(${m.id})">删除</button>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
        } catch (e) {
            wrap.innerHTML = '<p>加载失败（可能权限不足或服务器未就绪）</p>';
        }
    }

    /* 操作下拉菜单 */
    function toggleRowMenu(btn) {
        const menu = btn.parentElement.querySelector('.row-action-menu');
        const wasOpen = menu && !menu.hidden;
        document.querySelectorAll('.row-action-menu').forEach((m) => {
            m.hidden = true;
        });
        if (menu && !wasOpen) menu.hidden = false;
    }

    // 点击弹窗外区域关闭所有下拉菜单（只绑定一次，避免 SPA 重复加载重复监听）
    if (!window.__rowActionCloseBound) {
        window.__rowActionCloseBound = true;
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.row-action-dropdown')) {
                document.querySelectorAll('.row-action-menu').forEach((m) => {
                    m.hidden = true;
                });
            }
        });
    }

    document.getElementById('form-create-model').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            model_id: form.model_id.value.trim(),
            display_name: form.display_name.value.trim(),
            type: form.type.value,
            version: form.version.value.trim(),
            config_url: form.config_url.value.trim(),
            config_hash: form.config_hash.value.trim().toLowerCase(),
            notes: form.notes.value.trim(),
            activate: form.activate.checked,
        };
        if (!data.model_id || !data.version || !data.config_url) {
            Notify.error('请填写模型标识、版本号和 config.json 下载地址');
            return;
        }
        try {
            const result = await Auth.post(`${window.API_BASE_URL}/models`, data);
            if (result.success) {
                Notify.success('模型已新增');
                form.reset();
                form.model_id.value = '37ac';
                form.activate.checked = true;
                loadModels();
                loadPublicModels();
            } else {
                Notify.error(result.message || '新增失败');
            }
        } catch (err) {
            Notify.error('网络错误');
        }
    });

    async function activateModel(id) {
        try {
            const result = await Auth.post(`${window.API_BASE_URL}/models/${id}/activate`);
            if (result.success) {
                Notify.success('已激活该模型');
                loadModels();
                loadPublicModels();
            } else {
                Notify.error(result.message || '激活失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    }

    function editModel(id) {
        const m = allModels.find((x) => x.id === id);
        if (!m) return;
        const val = (v) => escapeHtml(v == null ? '' : String(v));

        const bodyHtml = `
            <p style="margin-bottom:1rem;">修改模型 <strong>${escapeHtml(m.display_name || m.model_id)}</strong> 的配置。</p>
            <form id="form-edit-model">
                <div class="field">
                    <label>模型标识（model_id）</label>
                    <input type="text" name="model_id" class="input" value="${val(m.model_id)}" required maxlength="50" />
                </div>
                <div class="field">
                    <label>展示名称</label>
                    <input type="text" name="display_name" class="input" value="${val(m.display_name)}" maxlength="100" />
                </div>
                <div class="field">
                    <label>类型</label>
                    <select name="type" class="select">
                        <option value="local" ${m.type === 'llm' ? '' : 'selected'}>local（本地）</option>
                        <option value="llm" ${m.type === 'llm' ? 'selected' : ''}>llm（大模型）</option>
                    </select>
                </div>
                <div class="field">
                    <label>版本号</label>
                    <input type="text" name="version" class="input" value="${val(m.version)}" required maxlength="64" />
                </div>
                <div class="field">
                    <label>配置文件下载地址（config.json）</label>
                    <input type="url" name="config_url" class="input" value="${val(m.config_url)}" required />
                </div>
                <div class="field">
                    <label>配置 SHA-256（可选）</label>
                    <input type="text" name="config_hash" class="input mono" value="${val(m.config_hash)}" maxlength="64" />
                </div>
                <div class="field" style="margin-bottom:0;">
                    <label>说明</label>
                    <textarea name="notes" class="input" rows="2">${val(m.notes)}</textarea>
                </div>
            </form>
        `;

        Modal.show('修改模型', bodyHtml, [{
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            },
            {
                text: '确认修改',
                class: 'btn btn-primary btn-sm',
                click: (e) => submitEditModel(id, e.target)
            }
        ]);
    }

    async function submitEditModel(id, btn) {
        const form = document.getElementById('form-edit-model');
        if (!form) return;
        const data = {
            model_id: form.model_id.value.trim(),
            display_name: form.display_name.value.trim(),
            type: form.type.value,
            version: form.version.value.trim(),
            config_url: form.config_url.value.trim(),
            config_hash: form.config_hash.value.trim().toLowerCase(),
            notes: form.notes.value.trim(),
        };
        if (!data.model_id || !data.version || !data.config_url) {
            Notify.error('请填写模型标识、版本号和 config.json 下载地址');
            return;
        }
        if (btn) {
            btn.disabled = true;
            btn.textContent = '保存中…';
        }
        try {
            const result = await Auth.put(`${window.API_BASE_URL}/models/${id}`, data);
            if (result.success) {
                Notify.success('模型已修改');
                Modal.close();
                loadModels();
                loadPublicModels();
            } else {
                Notify.error(result.message || '修改失败');
            }
        } catch (err) {
            Notify.error('网络错误');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '确认修改';
            }
        }
    }

    function confirmDeleteModel(id) {
        const m = allModels.find((x) => x.id === id);
        const label = m ? `${m.display_name || m.model_id} v${m.version}` : `#${id}`;
        Modal.show('删除模型', `<p>确定要删除模型 <b>${escapeHtml(label)}</b> 吗？此操作不可恢复。</p>`, [{
                text: '删除',
                class: 'btn btn-danger btn-sm',
                click: () => {
                    Modal.close();
                    deleteModel(id);
                }
            },
            {
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            }
        ]);
    }

    async function deleteModel(id) {
        try {
            const result = await Auth.del(`${window.API_BASE_URL}/models/${id}`);
            if (result.success) {
                Notify.success('已删除');
                loadModels();
                loadPublicModels();
            } else {
                Notify.error(result.message || '删除失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    }

    window.dashboardPageInit = () => {
        window.__pageLoadPromise = (async () => {
            await loadPublicModels();
            if (isAdmin()) {
                document.getElementById('admin-panel').style.display = 'block';
                await loadModels();
            }
        })();
    };
</script>