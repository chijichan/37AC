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

    .action-bar {
        display: flex;
        gap: .7rem;
        flex-wrap: wrap;
        margin-bottom: 1.6rem;
    }

    .node-card {
        background: var(--ac-surface);
        padding: 1.4rem 1.5rem;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        margin-bottom: 1.1rem;
        transition: transform var(--ac-dur) var(--ac-ease-spring),
            box-shadow var(--ac-dur) var(--ac-ease-out);
    }

    .node-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--ac-shadow-float);
    }

    .node-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .node-header h3 {
        margin: 0 0 .15rem;
    }

    .node-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: .7rem;
        margin: 1rem 0;
    }

    .node-meta-item {
        text-align: center;
        padding: .7rem .5rem;
        background: var(--ac-bg);
        border-radius: var(--ac-radius-input);
    }

    .node-meta-value {
        font-family: var(--ac-font-mono);
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--ac-ink-900);
    }

    .node-meta-label {
        font-size: .75rem;
        color: var(--ac-ink-500);
        margin-top: .2rem;
    }

    .node-info-line {
        font-size: .85rem;
        color: var(--ac-ink-500);
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: .4rem .8rem;
    }

    .node-detail-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: .45rem 0;
        font-size: .88rem;
        border-bottom: 1px solid var(--ac-surface-2);
    }

    .node-detail-row:last-child {
        border-bottom: none;
    }

    .node-detail-label {
        color: var(--ac-ink-500);
        flex-shrink: 0;
    }

    .node-detail-value {
        font-family: var(--ac-font-mono);
        font-size: .82rem;
        text-align: right;
        word-break: break-all;
    }

    .card-footer {
        display: flex;
        gap: .5rem;
        justify-content: flex-end;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--ac-surface-2);
    }

    @media (max-width: 600px) {
        .node-header {
            flex-direction: column;
        }
    }
</style>

<header class="dash-page-head">
    <h2>节点管理</h2>
    <p>管理和监控推理节点的运行状态。</p>
</header>

<div class="stat-summary" id="node-stats">
    <div class="stat"><span class="stat-value" id="stat-total">--</span><span class="stat-label">总节点数</span></div>
    <div class="stat"><span class="stat-value" id="stat-online" style="color:var(--ac-success)">--</span><span class="stat-label">在线</span></div>
    <div class="stat"><span class="stat-value" id="stat-offline" style="color:var(--ac-danger)">--</span><span class="stat-label">离线</span></div>
    <div class="stat"><span class="stat-value" id="stat-active">--</span><span class="stat-label">已启用</span></div>
</div>

<div class="action-bar">
    <button class="btn btn-primary" id="btn-add-node"><i class="ph-bold ph-plus"></i> 添加新节点</button>
    <button class="btn btn-ghost" id="btn-refresh-nodes"><i class="ph ph-arrows-clockwise"></i> 刷新状态</button>
</div>

<section>
    <div id="nodes-list">
        <div class="card">
            <div class="skeleton" style="height: 120px;"></div>
        </div>
    </div>
</section>

<script>
    var allNodes = [];

    // 格式化能力列表 JSON 为可读文本
    function formatCapabilities(caps) {
        if (!caps) return 'local';
        try {
            const arr = JSON.parse(caps);
            return Array.isArray(arr) ? arr.join(', ') : caps;
        } catch (e) {
            return caps;
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

    async function loadNodes() {
        const container = document.getElementById('nodes-list');
        container.innerHTML = '<div class="card"><div class="skeleton" style="height: 120px;"></div></div>';

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/dashboard/nodes`);
            const payload = await response.json();
            if (!response.ok || payload.error) {
                const message = payload.error || '无法获取节点数据';
                Notify.error(message);
                allNodes = [];
                container.innerHTML = `
                    <div class="card empty">
                        <div class="empty-icon"><i class="ph ph-warning"></i></div>
                        <h3>节点加载失败</h3>
                        <p>${escapeHtml(message)}</p>
                    </div>`;
                return;
            }

            const nodes = payload.data || [];
            allNodes = nodes;

            // 更新统计
            document.getElementById('stat-total').textContent = nodes.length;
            document.getElementById('stat-online').textContent = nodes.filter(n => n.status === 'online').length;
            document.getElementById('stat-offline').textContent = nodes.filter(n => n.status === 'offline').length;
            document.getElementById('stat-active').textContent = nodes.filter(n => n.is_active).length;

            if (!nodes.length) {
                container.innerHTML = `
                    <div class="card empty">
                        <div class="empty-icon"><i class="ph ph-share-network"></i></div>
                        <h3>暂无节点</h3>
                        <p>点击上方"添加新节点"创建你的第一个推理节点。</p>
                    </div>`;
                return;
            }

            container.innerHTML = nodes.map(node => {
                const isOnline = node.status === 'online';
                const statusBadge = isOnline ?
                    '<span class="badge badge-success"><span class="status-dot online"></span>在线</span>' :
                    '<span class="badge badge-neutral"><span class="status-dot offline"></span>离线</span>';
                const activeBadge = node.is_active ?
                    '<span class="badge badge-success">已启用</span>' :
                    '<span class="badge badge-danger">已禁用</span>';

                return `
                    <div class="node-card" data-node-id="${node.id}">
                        <div class="node-header">
                            <div>
                                <h3>${escapeHtml(node.name || '未命名节点')}</h3>
                                <small>${escapeHtml(node.addr || '地址未知')} · ${activeBadge}</small>
                            </div>
                            ${statusBadge}
                        </div>

                        <div class="node-meta">
                            <div class="node-meta-item">
                                <div class="node-meta-value">${node.load_percentage ?? 0}%</div>
                                <div class="node-meta-label">负载</div>
                            </div>
                            <div class="node-meta-item">
                                <div class="node-meta-value">${node.current_tasks ?? 0}</div>
                                <div class="node-meta-label">当前任务</div>
                            </div>
                            <div class="node-meta-item">
                                <div class="node-meta-value">${node.max_tasks ?? 0}</div>
                                <div class="node-meta-label">最大任务</div>
                            </div>
                            <div class="node-meta-item">
                                <div class="node-meta-value" style="font-size:.95rem;">${node.updated_at ? new Date(node.updated_at).toLocaleTimeString() : '--'}</div>
                                <div class="node-meta-label">最后更新</div>
                            </div>
                        </div>

                        <div class="node-info-line">
                            <span><i class="ph ph-user"></i> ${escapeHtml(node.username || '未分配')}</span>
                            <span>ID: ${node.id}</span>
                            <span>能力: ${escapeHtml(formatCapabilities(node.capabilities))}</span>
                        </div>

                        <div class="card-footer">
                            <button class="btn btn-ghost btn-sm" onclick="showNodeDetail(${node.id})">详情</button>
                            <button class="btn btn-secondary btn-sm" onclick="showEditNodeModal(${node.id})">修改</button>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            container.innerHTML = '<div class="card empty"><div class="empty-icon"><i class="ph ph-warning"></i></div><p>加载失败，请检查网络连接。</p></div>';
        }
    }

    // 节点详情弹窗
    function showNodeDetail(nodeId) {
        const node = allNodes.find(n => n.id === nodeId);
        if (!node) return;

        const isOnline = node.status === 'online';
        const rows = [
            ['节点 ID', node.id],
            ['名称', node.name || '--'],
            ['状态', isOnline ? '在线' : '离线'],
            ['启用状态', node.is_active ? '已启用' : '已禁用'],
            ['地址', node.addr || '--'],
            ['所属用户', node.username || '未分配'],
            ['负载', (node.load_percentage ?? 0) + '%'],
            ['当前任务', node.current_tasks ?? 0],
            ['最大任务', node.max_tasks ?? 0],
            ['识别能力', formatCapabilities(node.capabilities)],
            ['创建时间', node.created_at || '--'],
            ['最后更新', node.updated_at || '--'],
        ];

        const bodyHtml = rows.map(([label, value]) => `
            <div class="node-detail-row">
                <span class="node-detail-label">${escapeHtml(label)}</span>
                <span class="node-detail-value">${escapeHtml(String(value))}</span>
            </div>
        `).join('');

        Modal.show(node.name || '未命名节点', bodyHtml, [{
            text: '删除',
            class: 'btn btn-danger btn-sm',
            click: () => confirmDeleteNode(node.id)
        }, {
            text: '关闭',
            class: 'btn btn-ghost btn-sm',
            click: () => Modal.close()
        }]);
    }

    // 添加节点弹窗
    function showAddNodeModal() {
        const bodyHtml = `
            <p style="margin-bottom:1rem;">添加一个推理节点到集群中。节点需要运行客户端程序并配置正确的 Token。</p>
            <form id="form-add-node">
                <div class="field">
                    <label>节点名称</label>
                    <input type="text" name="name" class="input" placeholder="例如：推理节点-01" required maxlength="50" />
                </div>
                <div class="field">
                    <label>节点 Token</label>
                    <input type="text" name="token" class="input" placeholder="节点通信密钥（可留空自动生成）" />
                    <span class="hint">节点客户端配置的通信密钥；留空则由服务器自动生成，创建后一次性显示</span>
                </div>
                <div class="field">
                    <label>节点地址</label>
                    <input type="text" name="addr" class="input" placeholder="例如：192.168.1.100:13137" />
                    <span class="hint">可选，节点 IP 和端口</span>
                </div>
                <div class="field" style="margin-bottom:0;">
                    <label>识别能力</label>
                    <select name="capabilities" class="select">
                        <option value="local">仅本地模型 (local)</option>
                        <option value="local,llm">本地模型 + LLM (local,llm)</option>
                    </select>
                    <span class="hint">节点支持的识别能力类型，可通过客户端 LLM_RECOGNITION_ENABLED 配置</span>
                </div>
            </form>
        `;

        Modal.show('添加新节点', bodyHtml, [{
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            },
            {
                text: '确认添加',
                class: 'btn btn-primary btn-sm',
                click: (e) => submitAddNode(e.target)
            }
        ]);
    }

    async function submitAddNode(btn) {
        const form = document.getElementById('form-add-node');
        if (!form) return;

        const data = {
            name: form.name.value.trim(),
            token: form.token.value.trim(),
            addr: form.addr.value.trim() || undefined,
            capabilities: form.capabilities.value.trim() || "local",
        };

        if (!data.name) {
            Notify.error('请输入节点名称');
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.textContent = '添加中…';
        }

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/nodes`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.success) {
                Modal.close();
                Notify.success('节点添加成功');
                loadNodes();
                // 服务端自动生成 Token 时，一次性展示给用户复制
                const generatedToken = result.data && result.data.token;
                if (generatedToken) {
                    showGeneratedToken(generatedToken);
                }
            } else {
                Notify.error(result.message || '添加失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '确认添加';
            }
        }
    }

    // 展示一次性生成的节点 Token
    function showGeneratedToken(token) {
        const bodyHtml = `
            <p style="margin-bottom:1rem;">节点已创建！这是该节点唯一的通信 Token，<strong>请立即复制保存</strong>，关闭后将无法再次查看。</p>
            <div style="display:flex;gap:.5rem;align-items:center;">
                <code style="flex:1;padding:.6rem .8rem;background:var(--ac-bg);border-radius:var(--ac-radius-input);word-break:break-all;font-size:.82rem;">${escapeHtml(token)}</code>
                <button class="btn btn-primary btn-sm" onclick="copyText('${token.replace(/'/g, "\\'")}', 'Token 已复制')">复制</button>
            </div>
            <p style="margin-top:1rem;font-size:.85rem;color:var(--ac-ink-500);">将 Token 填入节点客户端 .env 的 <code>TOKEN=</code> 配置项。</p>
        `;
        Modal.show('节点 Token（仅显示一次）', bodyHtml, [{
            text: '我已保存',
            class: 'btn btn-ghost btn-sm',
            click: () => Modal.close()
        }]);
    }

    // 修改节点弹窗
    function showEditNodeModal(nodeId) {
        const node = allNodes.find(n => n.id === nodeId);
        if (!node) return;

        let capsStr = 'local';
        try {
            const arr = JSON.parse(node.capabilities);
            capsStr = Array.isArray(arr) ? arr.join(',') : node.capabilities;
        } catch (e) {
            capsStr = node.capabilities || 'local';
        }

        const bodyHtml = `
            <p style="margin-bottom:1rem;">修改节点 <strong>${escapeHtml(node.name || '未命名')}</strong> 的配置。</p>
            <form id="form-edit-node">
                <div class="field">
                    <label>节点名称</label>
                    <input type="text" name="name" class="input" value="${escapeHtml(node.name || '')}" placeholder="例如：推理节点-01" required maxlength="50" />
                </div>
                <div class="field">
                    <label>节点 Token</label>
                    <input type="text" name="token" class="input" placeholder="留空则不修改 Token" autocomplete="off" />
                    <span class="hint">可选,留空保持原 Token；填写后节点需用新 Token 重新注册</span>
                </div>
                <div class="field">
                    <label>节点地址</label>
                    <input type="text" name="addr" class="input" value="${escapeHtml(node.addr || '')}" placeholder="例如：192.168.1.100:13137" />
                    <span class="hint">可选，节点 IP 和端口</span>
                </div>
                <div class="field" style="margin-bottom:0;">
                    <label>识别能力</label>
                    <select name="capabilities" class="select">
                        <option value="local" ${capsStr === 'local' ? 'selected' : ''}>仅本地模型 (local)</option>
                        <option value="local,llm" ${capsStr === 'local,llm' ? 'selected' : ''}>本地模型 + LLM (local,llm)</option>
                    </select>
                    <span class="hint">节点支持的识别能力类型</span>
                </div>
            </form>
        `;

        Modal.show('修改节点', bodyHtml, [{
                text: '取消',
                class: 'btn btn-ghost btn-sm',
                click: () => Modal.close()
            },
            {
                text: '确认修改',
                class: 'btn btn-primary btn-sm',
                click: (e) => submitEditNode(node.id, e.target)
            }
        ]);
    }

    // 删除节点确认弹窗
    function confirmDeleteNode(nodeId) {
        const node = allNodes.find(n => n.id === nodeId);
        if (!node) return;

        const isOnline = node.status === 'online';
        const warning = isOnline ?
            '<p style="margin-bottom:1rem;color:var(--ac-danger);">该节点当前<strong>在线</strong>，删除后其连接将被立即断开，节点客户端需要重新配置后才能注册。</p>' :
            '<p style="margin-bottom:1rem;">删除后该节点将从集群中移除，不可恢复。</p>';

        Modal.show('删除节点', `
            <p style="margin-bottom:.5rem;">确定要删除节点 <strong>${escapeHtml(node.name || '未命名节点')}</strong>（ID: ${node.id}）吗？</p>
            ${warning}
        `, [{
            text: '取消',
            class: 'btn btn-ghost btn-sm',
            click: () => Modal.close()
        }, {
            text: '确认删除',
            class: 'btn btn-danger btn-sm',
            click: (e) => deleteNode(nodeId, e.target)
        }]);
    }

    async function deleteNode(nodeId, btn) {
        if (btn) {
            btn.disabled = true;
            btn.textContent = '删除中…';
        }

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/nodes/${nodeId}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            if (result.success) {
                Modal.close();
                Notify.success('节点已删除');
                loadNodes();
            } else {
                Notify.error(result.message || '删除失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '确认删除';
            }
        }
    }

    async function submitEditNode(nodeId, btn) {
        const form = document.getElementById('form-edit-node');
        if (!form) return;

        const data = {
            name: form.name.value.trim(),
            addr: form.addr.value.trim() || undefined,
            capabilities: form.capabilities.value.trim() || "local",
        };

        // 仅填写了新 Token 才发送，避免误清空
        const newToken = form.token.value.trim();
        if (newToken) {
            data.token = newToken;
        }

        if (!data.name) {
            Notify.error('节点名称不能为空');
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.textContent = '修改中…';
        }

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/nodes/${nodeId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.success) {
                Modal.close();
                Notify.success('节点修改成功');
                loadNodes();
            } else {
                Notify.error(result.message || '修改失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '确认修改';
            }
        }
    }

    document.getElementById('btn-refresh-nodes').addEventListener('click', loadNodes);
    document.getElementById('btn-add-node').addEventListener('click', showAddNodeModal);

    // 页面加载时自动加载，将 Promise 存入全局变量供 layout.php 等待
    window.dashboardPageInit = function() {
        window.__pageLoadPromise = loadNodes();
    };
</script>