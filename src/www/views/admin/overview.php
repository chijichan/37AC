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

    .stat-summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1.1rem;
        margin-bottom: 1.6rem;
    }

    .stat {
        background: var(--ac-surface);
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        padding: 1.2rem 1.3rem;
    }

    .stat-value {
        display: block;
        font-family: var(--ac-font-display);
        font-size: 1.7rem;
        font-weight: 800;
        color: var(--ac-ink-900);
    }

    .stat-label {
        display: block;
        margin-top: .25rem;
        font-size: .82rem;
        color: var(--ac-ink-500);
    }

    .sys-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
    }

    .sys-item {
        padding: .9rem 1rem;
        border-radius: var(--ac-radius-input);
        background: var(--ac-bg);
    }

    .sys-item .label {
        display: flex;
        justify-content: space-between;
        font-size: .85rem;
        color: var(--ac-ink-600);
        margin-bottom: .5rem;
    }
</style>

<header class="dash-page-head">
    <h2>系统概况</h2>
    <p>全站用户、任务、节点与主机资源概况。</p>
</header>

<div class="stat-summary">
    <div class="stat"><span class="stat-value" id="stats-total-users">--</span><span class="stat-label">用户总数</span></div>
    <div class="stat"><span class="stat-value" id="stats-total-uploads">--</span><span class="stat-label">任务总数</span></div>
    <div class="stat"><span class="stat-value" id="stats-total-nodes" style="color:var(--ac-success)">--</span><span class="stat-label">在线节点</span></div>
    <div class="stat"><span class="stat-value" id="stats-accuracy">--</span><span class="stat-label">平均识别准确率</span></div>
</div>

<div class="card" style="padding:1.4rem 1.5rem;">
    <h3 style="margin-bottom:1rem;">主机资源</h3>
    <div class="sys-grid">
        <div class="sys-item">
            <div class="label"><span>CPU</span><span id="system-cpu">--</span></div>
            <span class="prob-bar"><i id="system-cpu-bar" style="width:0%"></i></span>
        </div>
        <div class="sys-item">
            <div class="label"><span>内存</span><span id="system-memory">--</span></div>
            <span class="prob-bar"><i id="system-memory-bar" style="width:0%"></i></span>
        </div>
        <div class="sys-item">
            <div class="label"><span>磁盘</span><span id="system-disk">--</span></div>
            <span class="prob-bar"><i id="system-disk-bar" style="width:0%"></i></span>
        </div>
    </div>
</div>

<script>
    // 用户总数单独取（/dashboard/summary 的 stats 不含 total_users）
    window.dashboardPageInit = function() {
        window.__pageLoadPromise = Auth.get(`${window.API_BASE_URL}/admin/users?page=1&per_page=1`)
            .then((result) => {
                const el = document.getElementById('stats-total-users');
                if (el) el.textContent = (result.data && result.data.total != null) ? result.data.total : '—';
            })
            .catch(() => {});
    };
</script>
