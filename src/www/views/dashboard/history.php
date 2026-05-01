<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<style>
    .history-status.success {
        color: var(--pico-ins-color);
        font-weight: 600;
    }

    .history-status.failure {
        color: var(--pico-del-color);
        font-weight: 600;
    }

    .history-status.pending {
        color: var(--pico-muted-color);
        font-weight: 600;
    }

    .api-key-tag {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: var(--pico-border-radius);
        font-size: 0.75rem;
        background: var(--pico-card-sectioning-background-color);
        color: var(--pico-muted-color);
        font-family: monospace;
    }

    .stat-card {
        text-align: center;
        padding: 1.5rem;
        background: var(--pico-card-background-color);
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .stat-card h2 {
        margin: 0;
        font-size: 2rem;
    }

    .stat-card small {
        color: var(--pico-muted-color);
        display: block;
        margin-top: 0.25rem;
    }

    /* 筛选器卡片样式 */
    .filter-card {
        background: var(--pico-card-background-color);
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        padding: 1.5rem;
        margin-bottom: 2rem;
    }

    .filter-card .filter-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        align-items: end;
    }

    .filter-card .filter-grid label {
        margin-bottom: 0;
    }

    .filter-card .filter-actions {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
        padding-top: 0.25rem;
    }

    .filter-card .filter-actions button {
        flex: 1;
        min-width: 0;
    }

    @media (max-width: 768px) {
        .filter-card .filter-grid {
            grid-template-columns: 1fr;
        }

        .filter-card .filter-actions {
            flex-direction: column;
        }

        .filter-card .filter-actions button {
            width: 100%;
        }
    }

    /* 表格行悬停效果 */
    #history-table-body tr {
        transition: background-color 0.15s ease;
    }

    #history-table-body tr:hover {
        background-color: var(--pico-card-sectioning-background-color);
    }

    /* 分页容器 */
    .pagination-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-top: 1.5rem;
        padding: 1rem;
        background: var(--pico-card-background-color);
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
    }

    .pagination-bar span {
        padding: 0.5rem 1rem;
        font-weight: 500;
        color: var(--pico-muted-color);
    }

    /* 空状态 */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: var(--pico-muted-color);
    }

    .empty-state h3 {
        margin-bottom: 0.5rem;
    }

    /* 详情模态框中的预格式化文本 */
    pre.detail-json {
        background: var(--pico-card-sectioning-background-color);
        padding: 1rem;
        border-radius: var(--pico-border-radius);
        overflow-x: auto;
        font-size: 0.8rem;
        max-height: 300px;
        white-space: pre-wrap;
        word-break: break-all;
    }

    /* 详情网格 */
    .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .detail-grid p {
        margin: 0;
    }

    .detail-grid p strong {
        display: block;
        font-size: 0.8rem;
        color: var(--pico-muted-color);
        margin-bottom: 0.25rem;
    }

    @media (max-width: 600px) {
        .detail-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <hgroup>
        <h1><?php require ROOT_PATH . '/views/components/icons/history.php'; ?> 使用记录</h1>
        <p>查看 API 使用历史和图片识别记录</p>
    </hgroup>
</header>

<!-- 统计概览 -->
<div class="grid" style="margin-bottom: 2rem;">
    <article class="stat-card">
        <h2 id="history-total-requests" style="color: var(--pico-primary);">--</h2>
        <small>总请求数</small>
    </article>
    <article class="stat-card">
        <h2 id="history-success-count" style="color: var(--pico-ins-color);">--</h2>
        <small>成功</small>
    </article>
    <article class="stat-card">
        <h2 id="history-failure-count" style="color: var(--pico-del-color);">--</h2>
        <small>失败</small>
    </article>
    <article class="stat-card">
        <h2 id="history-success-rate" style="color: var(--pico-primary);">--%</h2>
        <small>成功率</small>
    </article>
</div>

<!-- 筛选器（卡片式设计） -->
<section class="filter-card">
    <form id="filter-form">
        <div class="filter-grid">
            <label>
                时间范围
                <select name="time_range">
                    <option value="7">最近7天</option>
                    <option value="30" selected>最近30天</option>
                    <option value="90">最近90天</option>
                    <option value="365">最近一年</option>
                </select>
            </label>
            <label>
                状态
                <select name="status">
                    <option value="">全部</option>
                    <option value="success">成功</option>
                    <option value="failure">失败</option>
                    <option value="pending">处理中</option>
                </select>
            </label>
            <label>
                每页显示
                <select name="limit">
                    <option value="10">10 条</option>
                    <option value="15" selected>15 条</option>
                    <option value="30">30 条</option>
                    <option value="50">50 条</option>
                </select>
            </label>
            <div class="filter-actions">
                <button type="submit"><?php require ROOT_PATH . '/views/components/icons/filter.php'; ?> 筛选</button>
                <button type="button" class="outline secondary" onclick="refreshHistory()"><?php require ROOT_PATH . '/views/components/icons/refresh.php'; ?> 刷新</button>
            </div>
        </div>
    </form>
</section>

<!-- 历史记录表格 -->
<section class="overflow-auto">
    <table role="grid">
        <thead>
            <tr>
                <th>任务ID</th>
                <th>时间</th>
                <th>操作</th>
                <th>文件名</th>
                <th>识别结果</th>
                <th>置信度</th>
                <th>API密钥</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody id="history-table-body">
            <tr>
                <td colspan="9" style="text-align:center; padding: 2rem;">
                    <span aria-busy="true"></span> 加载中…
                </td>
            </tr>
        </tbody>
    </table>
</section>

<!-- 分页 -->
<nav class="pagination-bar" aria-label="分页导航">
    <button class="outline secondary" id="btn-prev-page" disabled>← 上一页</button>
    <span id="page-info">第 1 页 / 共 1 页</span>
    <button class="outline secondary" id="btn-next-page" disabled>下一页 →</button>
</nav>

<?php $historyIconSvg = file_get_contents(ROOT_PATH . '/views/components/icons/history.php'); ?>
<script>
    var currentPage = 1;
    var HISTORY_ICON_SVG = <?php echo json_encode($historyIconSvg); ?>;
    var totalPages = 1;
    var allTasks = [];

    async function loadHistory(page = 1) {
        const body = document.getElementById('history-table-body');
        body.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 2rem;"><span aria-busy="true"></span> 加载中…</td></tr>';

        try {
            const form = document.getElementById('filter-form');
            const formData = new FormData(form);
            const params = new URLSearchParams({
                page: page,
                limit: formData.get('limit') || '15',
                time_range: formData.get('time_range') || '30',
                status: formData.get('status') || '',
            });

            const response = await Auth.fetch(`${window.API_BASE_URL}/dashboard/tasks?${params}`);
            const payload = await response.json();
            const tasks = payload.data || [];
            allTasks = tasks;

            // 更新统计
            const total = tasks.length;
            const successCount = tasks.filter(t => t.status === 'success').length;
            const failureCount = tasks.filter(t => t.status === 'failure').length;
            const pendingCount = tasks.filter(t => t.status === 'pending').length;
            const successRate = total > 0 ? Math.round((successCount / total) * 1000) / 10 : 0;

            document.getElementById('history-total-requests').textContent = total;
            document.getElementById('history-success-count').textContent = successCount;
            document.getElementById('history-failure-count').textContent = failureCount;
            document.getElementById('history-success-rate').textContent = `${successRate}%`;

            // 更新分页
            totalPages = payload.total_pages || 1;
            currentPage = payload.page || page;
            document.getElementById('page-info').textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
            document.getElementById('btn-prev-page').disabled = currentPage <= 1;
            document.getElementById('btn-next-page').disabled = currentPage >= totalPages;

            if (!tasks.length) {
                body.innerHTML = '<tr><td colspan="9"><div class="empty-state"><h3>📭 暂无记录</h3><p>当前筛选条件下没有找到历史记录</p></div></td></tr>';
                return;
            }

            body.innerHTML = tasks.map(task => {
                const statusMap = {
                    success: '<span class="history-status success">✓ 成功</span>',
                    failure: '<span class="history-status failure">✗ 失败</span>',
                    pending: '<span class="history-status pending">⏳ 处理中</span>',
                };
                const statusHtml = statusMap[task.status] || task.status;
                const apiKeyInfo = task.api_key_name ?
                    `<span class="api-key-tag">${task.api_key_name}</span>` :
                    '<span class="api-key-tag" style="color:var(--pico-muted-color);">--</span>';

                const confidence = task.confidence;
                const confidenceStr = confidence != null ?
                    (typeof confidence === 'number' ? `${confidence.toFixed(1)}%` : `${confidence}%`) :
                    '--';

                const taskIdShort = task.task_id ?
                    (task.task_id.length > 8 ? task.task_id.slice(0, 8) + '…' : task.task_id) :
                    '--';

                const filename = task.filename || (task.task_id ? `image_${task.task_id.slice(0, 8)}.jpg` : '--');

                return `
                    <tr>
                        <td><small title="${task.task_id || ''}">${taskIdShort}</small></td>
                        <td><small>${task.created_at || '--'}</small></td>
                        <td>图片识别</td>
                        <td><small>${filename}</small></td>
                        <td><strong>${task.label || '--'}</strong></td>
                        <td>${confidenceStr}</td>
                        <td>${apiKeyInfo}</td>
                        <td>${statusHtml}</td>
                        <td>
                            <button class="outline secondary" style="padding: 0.2rem 0.5rem; font-size: 0.75rem;"
                                    onclick="showDetail('${task.task_id || ''}')">详情</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            body.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--pico-del-color); padding: 2rem;">加载失败，请检查服务器连接</td></tr>';
        }
    }

    function showDetail(taskId) {
        const task = allTasks.find(t => t.task_id === taskId);
        if (!task) return;

        const resultJson = task.result ?
            (typeof task.result === 'object' ? JSON.stringify(task.result, null, 2) : task.result) :
            '无';

        const bodyHtml = `
            <div class="detail-grid">
                <div>
                    <p><strong>任务ID</strong><small>${task.task_id || '--'}</small></p>
                    <p><strong>时间</strong><small>${task.created_at || '--'}</small></p>
                    <p><strong>状态</strong><small>${task.status === 'success' ? '✓ 成功' : task.status === 'failure' ? '✗ 失败' : '⏳ 处理中'}</small></p>
                </div>
                <div>
                    <p><strong>识别结果</strong><small>${task.label || '--'}</small></p>
                    <p><strong>置信度</strong><small>${task.confidence != null ? task.confidence + '%' : '--'}</small></p>
                    <p><strong>API密钥</strong><small>${task.api_key_name || '--'}</small></p>
                </div>
            </div>
            <hr>
            <p><strong>原始返回数据</strong></p>
            <pre class="detail-json">${resultJson}</pre>
        `;

        Modal.show(HISTORY_ICON_SVG + ' 任务详情', bodyHtml, [{
            text: '关闭',
            class: 'secondary',
            click: () => Modal.close()
        }]);
    }

    function refreshHistory() {
        loadHistory(currentPage);
    }

    // 筛选表单提交
    document.getElementById('filter-form').addEventListener('submit', (e) => {
        e.preventDefault();
        loadHistory(1);
    });

    // 分页
    document.getElementById('btn-prev-page').addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage > 1) loadHistory(currentPage - 1);
    });
    document.getElementById('btn-next-page').addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage < totalPages) loadHistory(currentPage + 1);
    });

    // 页面加载时自动加载
    window.dashboardPageInit = () => loadHistory(1);
</script>