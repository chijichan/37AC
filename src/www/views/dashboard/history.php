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

    .filter-card {
        background: var(--ac-surface);
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.6rem;
    }

    .filter-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 0 1rem;
        align-items: end;
    }

    .filter-grid .field {
        margin-bottom: 0;
    }

    .filter-actions {
        display: flex;
        gap: .5rem;
    }

    .filter-actions .btn {
        flex: 1;
    }

    .api-key-tag {
        display: inline-block;
        padding: .15rem .6rem;
        border-radius: var(--ac-radius-pill);
        font-size: .75rem;
        background: var(--ac-bg);
        color: var(--ac-ink-500);
        font-family: var(--ac-font-mono);
    }

    .pagination-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-top: 1.4rem;
    }

    .pagination-bar .page-info {
        font-size: .9rem;
        color: var(--ac-ink-500);
        font-family: var(--ac-font-mono);
    }

    .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: .8rem 1.2rem;
        margin-bottom: 1rem;
    }

    .detail-grid .detail-item strong {
        display: block;
        font-size: .78rem;
        color: var(--ac-ink-500);
        margin-bottom: .2rem;
        font-weight: 600;
    }

    .detail-grid .detail-item span {
        font-family: var(--ac-font-mono);
        font-size: .85rem;
        word-break: break-all;
    }

    pre.detail-json {
        background: var(--ac-bg);
        padding: .9rem 1rem;
        border-radius: var(--ac-radius-input);
        overflow-x: auto;
        font-size: .8rem;
        max-height: 300px;
        white-space: pre-wrap;
        word-break: break-all;
        margin: 0;
    }

    @media (max-width: 768px) {
        .filter-grid {
            grid-template-columns: 1fr;
            gap: 0;
        }

        .filter-grid .field {
            margin-bottom: .9rem;
        }

        .detail-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<header class="dash-page-head">
    <h2>使用记录</h2>
    <p>查看 API 使用历史和图片识别记录。</p>
</header>

<div class="stat-summary">
    <div class="stat"><span class="stat-value" id="history-total-requests">--</span><span class="stat-label">总请求数</span></div>
    <div class="stat"><span class="stat-value" id="history-success-count" style="color:var(--ac-success)">--</span><span class="stat-label">已完成</span></div>
    <div class="stat"><span class="stat-value" id="history-failure-count" style="color:var(--ac-danger)">--</span><span class="stat-label">未完成</span></div>
    <div class="stat"><span class="stat-value" id="history-success-rate">--%</span><span class="stat-label">完成率</span></div>
</div>

<section class="filter-card">
    <form id="filter-form">
        <div class="filter-grid">
            <div class="field">
                <label>时间范围</label>
                <select name="time_range" class="select">
                    <option value="7">最近 7 天</option>
                    <option value="30" selected>最近 30 天</option>
                    <option value="90">最近 90 天</option>
                    <option value="365">最近一年</option>
                </select>
            </div>
            <div class="field">
                <label>状态</label>
                <select name="status" class="select">
                    <option value="">全部</option>
                    <option value="completed">完成</option>
                    <option value="pending">处理中</option>
                </select>
            </div>
            <div class="field">
                <label>每页显示</label>
                <select name="limit" class="select">
                    <option value="10">10 条</option>
                    <option value="15" selected>15 条</option>
                    <option value="30">30 条</option>
                    <option value="50">50 条</option>
                </select>
            </div>
            <div class="filter-actions">
                <button type="submit" class="btn btn-primary"><i class="ph ph-funnel"></i> 筛选</button>
                <button type="button" class="btn btn-ghost" onclick="refreshHistory()"><i class="ph ph-arrows-clockwise"></i></button>
            </div>
        </div>
    </form>
</section>

<div class="table-wrap">
    <table class="table">
        <thead>
            <tr>
                <th>任务 ID</th>
                <th>时间</th>
                <th>文件名</th>
                <th>识别结果</th>
                <th>置信度</th>
                <th>API 密钥</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody id="history-table-body">
            <tr>
                <td colspan="8" style="text-align:center; padding: 2rem;">加载中…</td>
            </tr>
        </tbody>
    </table>
</div>

<nav class="pagination-bar" id="pagination-bar" aria-label="分页导航" style="display:none;">
    <button class="btn btn-ghost btn-sm" id="btn-prev-page" disabled><i class="ph ph-caret-left"></i> 上一页</button>
    <span class="page-info" id="page-info">第 1 页 / 共 1 页</span>
    <button class="btn btn-ghost btn-sm" id="btn-next-page" disabled>下一页 <i class="ph ph-caret-right"></i></button>
</nav>

<script>
    var currentPage = 1;
    var totalPages = 1;
    var allTasks = [];

    async function loadHistory(page = 1) {
        const body = document.getElementById('history-table-body');
        body.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 2rem;">加载中…</td></tr>';

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

            // 使用服务器返回的全量统计，而非仅当前页
            const statsTotal = payload.total_count ?? tasks.length;
            const statsCompleted = payload.completed_count ?? tasks.filter(t => t.status === 'completed').length;
            const statsPending = payload.pending_count ?? tasks.filter(t => t.status === 'pending').length;
            const completionRate = statsTotal > 0 ? Math.round((statsCompleted / statsTotal) * 1000) / 10 : 0;

            document.getElementById('history-total-requests').textContent = statsTotal;
            document.getElementById('history-success-count').textContent = statsCompleted;
            document.getElementById('history-failure-count').textContent = statsPending;
            document.getElementById('history-success-rate').textContent = `${completionRate}%`;

            // 分页（仅多页时显示分页栏）
            totalPages = payload.total_pages || 1;
            currentPage = payload.page || page;
            document.getElementById('pagination-bar').style.display = totalPages > 1 ? '' : 'none';
            document.getElementById('page-info').textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
            document.getElementById('btn-prev-page').disabled = currentPage <= 1;
            document.getElementById('btn-next-page').disabled = currentPage >= totalPages;

            if (!tasks.length) {
                body.innerHTML = '<tr><td colspan="8"><div class="empty"><div class="empty-icon"><i class="ph ph-clock-counter-clockwise"></i></div><h3>暂无记录</h3><p>当前筛选条件下没有找到历史记录。</p></div></td></tr>';
                return;
            }

            body.innerHTML = tasks.map((task, index) => {
                const statusMap = {
                    completed: '<span class="badge badge-success">已完成</span>',
                    pending: '<span class="badge badge-warning">处理中</span>',
                };
                const statusHtml = statusMap[task.status] || `<span class="badge badge-neutral">${escapeHtml(task.status)}</span>`;
                const apiKeyInfo = task.api_key_name ?
                    `<span class="api-key-tag">${escapeHtml(task.api_key_name)}</span>` :
                    '<span class="api-key-tag">--</span>';

                const confidence = task.confidence;
                const confidenceStr = confidence != null ?
                    (typeof confidence === 'number' ? `${confidence.toFixed(1)}%` : `${escapeHtml(confidence)}%`) :
                    '--';

                const taskIdShort = task.task_id ?
                    (task.task_id.length > 8 ? escapeHtml(task.task_id.slice(0, 8)) + '…' : escapeHtml(task.task_id)) :
                    '--';

                const filename = task.filename || (task.task_id ? `image_${task.task_id.slice(0, 8)}.jpg` : '--');

                return `
                    <tr>
                        <td><small class="mono" title="${escapeHtml(task.task_id || '')}">${taskIdShort}</small></td>
                        <td><small>${escapeHtml(task.created_at || '--')}</small></td>
                        <td><small>${escapeHtml(filename)}</small></td>
                        <td><strong>${escapeHtml(task.label || '--')}</strong></td>
                        <td class="mono">${confidenceStr}</td>
                        <td>${apiKeyInfo}</td>
                        <td>${statusHtml}</td>
                        <td>
                            <button class="btn btn-ghost btn-sm" onclick="showDetail(${index})">详情</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            body.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 2rem; color: var(--ac-danger);">加载失败，请检查服务器连接</td></tr>';
            document.getElementById('pagination-bar').style.display = 'none';
        }
    }

    function showDetail(index) {
        const task = allTasks[index];
        if (!task) return;

        const resultJson = task.result ?
            (typeof task.result === 'object' ? JSON.stringify(task.result, null, 2) : String(task.result)) :
            '无';

        const bodyHtml = `
            <div class="detail-grid">
                <div class="detail-item"><strong>任务 ID</strong><span>${escapeHtml(task.task_id || '--')}</span></div>
                <div class="detail-item"><strong>时间</strong><span>${escapeHtml(task.created_at || '--')}</span></div>
                <div class="detail-item"><strong>状态</strong><span>${task.status === 'completed' ? '已完成' : '处理中'}</span></div>
                <div class="detail-item"><strong>识别结果</strong><span>${escapeHtml(task.label || '--')}</span></div>
                <div class="detail-item"><strong>置信度</strong><span>${task.confidence != null ? escapeHtml(String(task.confidence)) + '%' : '--'}</span></div>
                <div class="detail-item"><strong>API 密钥</strong><span>${escapeHtml(task.api_key_name || '--')}</span></div>
            </div>
            <strong style="display:block; font-size:.78rem; color:var(--ac-ink-500); margin-bottom:.3rem;">原始返回数据</strong>
            <pre class="detail-json">${escapeHtml(resultJson)}</pre>
        `;

        Modal.show('任务详情', bodyHtml, [{
            text: '关闭',
            class: 'btn btn-ghost btn-sm',
            click: () => Modal.close()
        }]);
    }

    function refreshHistory() {
        loadHistory(currentPage);
    }

    document.getElementById('filter-form').addEventListener('submit', (e) => {
        e.preventDefault();
        loadHistory(1);
    });

    document.getElementById('btn-prev-page').addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage > 1) loadHistory(currentPage - 1);
    });
    document.getElementById('btn-next-page').addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage < totalPages) loadHistory(currentPage + 1);
    });

    // 页面加载时自动加载，将 Promise 存入全局变量供 layout.php 等待
    window.dashboardPageInit = () => {
        window.__pageLoadPromise = loadHistory(1);
    };
</script>
