<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<style>
    .node-card {
        background: var(--pico-card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .node-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .node-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .node-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 5rem;
        font-size: 0.8rem;
        font-weight: 600;
        flex-shrink: 0;
    }

    .node-status.online {
        background: var(--pico-ins-color);
        color: #fff;
    }

    .node-status.offline {
        background: var(--pico-del-color);
        color: #fff;
    }

    .node-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
    }

    .node-meta-item {
        text-align: center;
        padding: 0.75rem;
        background: var(--pico-card-sectioning-background-color);
        border-radius: var(--pico-border-radius);
    }

    .node-meta-value {
        font-size: 1.4rem;
        font-weight: bold;
        color: var(--pico-primary);
    }

    .node-meta-label {
        font-size: 0.75rem;
        color: var(--pico-muted-color);
        margin-top: 0.25rem;
    }

    .node-detail-row {
        display: flex;
        justify-content: space-between;
        padding: 0.4rem 0;
        font-size: 0.875rem;
        border-bottom: 1px solid var(--pico-muted-border-color);
    }

    .node-detail-row:last-child {
        border-bottom: none;
    }

    .node-detail-label {
        color: var(--pico-muted-color);
    }

    .node-detail-value {
        font-weight: 500;
        font-family: monospace;
        font-size: 0.8rem;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
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

    .action-bar {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
    }

    .node-token {
        font-family: monospace;
        font-size: 0.8rem;
        background: var(--pico-card-sectioning-background-color);
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        cursor: pointer;
        user-select: all;
    }

    .node-token:hover {
        background: var(--pico-primary-background);
    }

    .card-footer {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--pico-muted-border-color);
    }

    @media (max-width: 600px) {
        .node-header {
            flex-direction: column;
        }

        .node-meta {
            grid-template-columns: 1fr 1fr;
        }
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>🖥️ 节点管理</h1>
    <p>管理和监控推理节点的运行状态</p>
</header>

<!-- 统计概览 -->
<div class="stat-summary" id="node-stats">
    <article>
        <h3 id="stat-total">--</h3><small>总节点数</small>
    </article>
    <article>
        <h3 id="stat-online" style="color: var(--pico-ins-color);">--</h3><small>在线</small>
    </article>
    <article>
        <h3 id="stat-offline" style="color: var(--pico-del-color);">--</h3><small>离线</small>
    </article>
    <article>
        <h3 id="stat-active">--</h3><small>已启用</small>
    </article>
</div>

<!-- 操作按钮 -->
<div class="action-bar">
    <button id="btn-add-node">➕ 添加新节点</button>
    <button class="secondary outline" id="btn-refresh-nodes">🔄 刷新状态</button>
</div>

<!-- 节点列表 -->
<section>
    <div id="nodes-list">
        <article class="node-card">
            <p style="text-align:center;"><span aria-busy="true"></span> 加载中…</p>
        </article>
    </div>
</section>

<?php $warnIconSvg = file_get_contents(ROOT_PATH . '/views/components/icons/warn.php'); ?>
<script>
    var allNodes = [];
    var WARN_ICON_SVG = <?php echo json_encode($warnIconSvg); ?>;

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
        container.innerHTML = '<article class="node-card"><p style="text-align:center;"><span aria-busy="true"></span> 加载中…</p></article>';

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/dashboard/nodes`);
            const payload = await response.json();
            if (!response.ok || payload.error) {
                const message = payload.error || '无法获取节点数据';
                Notify.error(message);
                allNodes = [];
                container.innerHTML = `
                    <article class="node-card empty-state">
                        <h3>${WARN_ICON_SVG} 节点加载失败</h3>
                        <p>${message}</p>
                    </article>
                `;
                return;
            }

            const nodes = payload.data || [];
            allNodes = nodes;

            // 更新统计
            const total = nodes.length;
            const onlineCount = nodes.filter(n => n.status === 'online').length;
            const offlineCount = nodes.filter(n => n.status === 'offline').length;
            const activeCount = nodes.filter(n => n.is_active).length;
            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-online').textContent = onlineCount;
            document.getElementById('stat-offline').textContent = offlineCount;
            document.getElementById('stat-active').textContent = activeCount;

            if (!nodes.length) {
                container.innerHTML = `
                    <article class="node-card empty-state">
                        <h3>🖥️ 暂无节点</h3>
                        <p>点击上方"添加新节点"创建你的第一个推理节点。</p>
                    </article>
                `;
                return;
            }

            container.innerHTML = nodes.map(node => {
                const statusClass = node.status === 'online' ? 'online' : 'offline';
                const statusText = node.status === 'online' ? '● 在线' : '● 离线';
                const ownerInfo = node.username ? `👤 ${node.username}` : '👤 未分配';
                const isActive = node.is_active;
                const activeBadge = isActive ?
                    '<span style="color: var(--pico-ins-color); font-size: 0.8rem;">✓ 已启用</span>' :
                    '<span style="color: var(--pico-del-color); font-size: 0.8rem;">✗ 已禁用</span>';

                return `
                    <article class="node-card" data-node-id="${node.id}">
                        <div class="node-header">
                            <div>
                                <h3 style="margin: 0;">${node.name || '未命名节点'}</h3>
                                <small style="color: var(--pico-muted-color);">
                                    ${node.addr || '地址未知'} · ${activeBadge}
                                </small>
                            </div>
                            <span class="node-status ${statusClass}">${statusText}</span>
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
                                <div class="node-meta-value" style="font-size: 1rem;">${node.updated_at ? new Date(node.updated_at).toLocaleTimeString() : '--'}</div>
                                <div class="node-meta-label">最后更新</div>
                            </div>
                        </div>

                        <div style="font-size: 0.85rem; color: var(--pico-muted-color);">
                            ${ownerInfo}
                            · Token: <span class="node-token" onclick="copyText('${node.token}', 'Token 已复制')" title="点击复制 Token">${node.token ? node.token.slice(0, 12) + '…' : '--'}</span>
                            · ID: ${node.id}
                        </div>

                        <div class="card-footer">
                            <button class="secondary outline" onclick="showNodeDetail(${node.id})">📋 详情</button>
                            <button class="outline" onclick="copyText('${node.token}', 'Token 已复制')">🔑 复制 Token</button>
                        </div>
                    </article>
                `;
            }).join('');
        } catch (e) {
            container.innerHTML = '<article class="node-card"><p style="text-align:center;color:var(--pico-del-color);">加载失败，请检查网络连接。</p></article>';
        }
    }

    // 显示节点详情（使用 PicoCSS 模态框）
    function showNodeDetail(nodeId) {
        const node = allNodes.find(n => n.id === nodeId);
        if (!node) return;

        const statusText = node.status === 'online' ? '✓ 在线' : '✗ 离线';
        const activeText = node.is_active ? '✓ 已启用' : '✗ 已禁用';

        const bodyHtml = `
            <div class="node-detail-row">
                <span class="node-detail-label">节点 ID</span>
                <span class="node-detail-value">${node.id}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">名称</span>
                <span class="node-detail-value">${node.name || '--'}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">状态</span>
                <span style="font-weight: 600; color: ${node.status === 'online' ? 'var(--pico-ins-color)' : 'var(--pico-del-color)'};">${statusText}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">启用状态</span>
                <span>${activeText}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">地址</span>
                <span class="node-detail-value">${node.addr || '--'}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">Token</span>
                <span class="node-detail-value" style="cursor: pointer;" onclick="copyText('${node.token}', 'Token 已复制')" title="点击复制">${node.token || '--'}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">所属用户</span>
                <span>${node.username || '未分配'}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">负载</span>
                <span>${node.load_percentage ?? 0}%</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">当前任务</span>
                <span>${node.current_tasks ?? 0}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">最大任务</span>
                <span>${node.max_tasks ?? 0}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">创建时间</span>
                <span>${node.created_at || '--'}</span>
            </div>
            <div class="node-detail-row">
                <span class="node-detail-label">最后更新</span>
                <span>${node.updated_at || '--'}</span>
            </div>
        `;

        Modal.show(`📋 ${node.name || '未命名节点'}`, bodyHtml, [{
            text: '关闭',
            class: 'secondary',
            click: () => Modal.close()
        }]);
    }

    // 添加节点弹窗（使用 PicoCSS 模态框）
    function showAddNodeModal() {
        const bodyHtml = `
            <p>添加一个推理节点到集群中。节点需要运行客户端程序并配置正确的 Token。</p>
            <form id="form-add-node">
                <label>
                    节点名称
                    <input type="text" name="name" placeholder="例如：推理节点-01" required maxlength="50" />
                </label>
                <label>
                    节点 Token
                    <input type="text" name="token" placeholder="节点通信密钥" required />
                    <small>节点客户端配置的通信密钥</small>
                </label>
                <label>
                    节点地址
                    <input type="text" name="addr" placeholder="例如：192.168.1.100:13137" />
                    <small>可选，节点 IP 和端口</small>
                </label>
            </form>
        `;

        Modal.show('➕ 添加新节点', bodyHtml, [{
                text: '取消',
                class: 'secondary',
                click: () => Modal.close()
            },
            {
                text: '确认添加',
                click: () => submitAddNode()
            }
        ]);
    }

    async function submitAddNode() {
        const form = document.getElementById('form-add-node');
        if (!form) return;

        const data = {
            name: form.name.value.trim(),
            token: form.token.value.trim(),
            addr: form.addr.value.trim() || undefined,
        };

        if (!data.name) {
            Notify.error('请输入节点名称');
            return;
        }
        if (!data.token) {
            Notify.error('请输入节点 Token');
            return;
        }

        const modalContent = Modal._dialog ? Modal._dialog.querySelector('article') : null;
        const btn = modalContent ? modalContent.querySelector('footer button:last-child') : null;
        if (btn) btn.setAttribute('aria-busy', 'true');

        try {
            const response = await Auth.fetch(`${window.API_BASE_URL}/nodes`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.success) {
                Modal.close();
                Notify.success('节点添加成功！');
                loadNodes();
            } else {
                Notify.error(result.message || '添加失败');
            }
        } catch (e) {
            Notify.error('网络错误，请检查服务器连接');
        } finally {
            if (btn) btn.removeAttribute('aria-busy');
        }
    }

    // 刷新按钮
    document.getElementById('btn-refresh-nodes').addEventListener('click', loadNodes);

    // 添加节点按钮
    document.getElementById('btn-add-node').addEventListener('click', showAddNodeModal);

    // 页面加载时自动加载
    window.dashboardPageInit = loadNodes;
</script>