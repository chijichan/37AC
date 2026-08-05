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

    .dash-banner {
        background: linear-gradient(135deg, var(--ac-pink-50), var(--ac-pink-100));
        border-radius: var(--ac-radius-card);
        padding: 1.6rem 1.8rem;
        margin-bottom: 1.6rem;
    }

    .dash-banner h2 {
        margin-bottom: .2rem;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.1rem;
        margin-bottom: 1.6rem;
    }

    .dash-section-title {
        font-size: 1.1rem;
        margin: 1.8rem 0 .9rem;
        display: flex;
        align-items: center;
        gap: .45rem;
    }

    .dash-section-title i {
        color: var(--ac-pink-500);
    }

    .quick-actions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
    }

    .action-button {
        display: flex;
        align-items: center;
        gap: .8rem;
        padding: 1.1rem 1.2rem;
        background: var(--ac-surface);
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
        color: var(--ac-ink-900);
        font-weight: 700;
        transition: transform var(--ac-dur) var(--ac-ease-spring),
            box-shadow var(--ac-dur) var(--ac-ease-out);
    }

    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: var(--ac-shadow-float);
        color: var(--ac-pink-600);
    }

    .action-button .action-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 42px;
        height: 42px;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-pink-100);
        color: var(--ac-pink-600);
        font-size: 1.3rem;
        flex-shrink: 0;
    }

    .dash-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.1rem;
    }

    .progress-container {
        margin-bottom: 1rem;
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        margin-bottom: .45rem;
        font-size: .88rem;
    }

    .progress-label strong {
        font-family: var(--ac-font-mono);
        font-size: .85rem;
    }

    .activity-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .activity-item {
        display: flex;
        align-items: center;
        gap: .9rem;
        padding: .8rem 0;
        border-bottom: 1px solid var(--ac-surface-2);
    }

    .activity-item:last-child {
        border-bottom: none;
    }

    .activity-item .activity-icon {
        width: 38px;
        height: 38px;
        flex-shrink: 0;
        border-radius: var(--ac-radius-pill);
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--ac-pink-100);
        color: var(--ac-pink-600);
        font-size: 1.1rem;
    }

    .activity-item .activity-content {
        flex: 1;
        min-width: 0;
    }

    .activity-item .activity-title {
        font-weight: 600;
        font-size: .92rem;
        color: var(--ac-ink-900);
    }

    .activity-item .activity-desc {
        font-size: .82rem;
        color: var(--ac-ink-500);
    }

    .activity-empty {
        padding: 1.5rem 0;
        text-align: center;
        color: var(--ac-ink-500);
        font-size: .92rem;
    }

    .network-row {
        display: flex;
        justify-content: space-between;
        font-size: .85rem;
        color: var(--ac-ink-500);
    }

    .network-row strong {
        font-family: var(--ac-font-mono);
        color: var(--ac-ink-700);
    }

    @media (max-width: 860px) {
        .dash-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<div class="dash-banner">
    <h2>仪表盘总览</h2>
    <p>欢迎回来，这里是系统运行状态的实时快照。</p>
</div>

<!-- 统计卡片 -->
<div class="stats-grid">
    <div class="stat">
        <span class="stat-label">总访问量</span>
        <span class="stat-value" id="stats-total-visits">--</span>
    </div>
    <div class="stat">
        <span class="stat-label">图片上传</span>
        <span class="stat-value" id="stats-total-uploads">--</span>
    </div>
    <div class="stat">
        <span class="stat-label">活跃用户</span>
        <span class="stat-value" id="stats-active-users">--</span>
    </div>
    <div class="stat">
        <span class="stat-label">识别准确率</span>
        <span class="stat-value" id="stats-accuracy">--%</span>
    </div>
</div>

<!-- 快速操作 -->
<h3 class="dash-section-title"><i class="ph ph-rocket"></i>快速操作</h3>
<div class="quick-actions">
    <a href="/upload" class="action-button">
        <span class="action-icon"><i class="ph ph-cloud-arrow-up"></i></span>
        上传图片
    </a>
    <a href="/dashboard/nodes" class="action-button">
        <span class="action-icon"><i class="ph ph-share-network"></i></span>
        节点管理
    </a>
    <a href="/dashboard/settings" class="action-button">
        <span class="action-icon"><i class="ph ph-gear"></i></span>
        系统设置
    </a>
    <a href="/dashboard/history" class="action-button">
        <span class="action-icon"><i class="ph ph-clock-counter-clockwise"></i></span>
        使用记录
    </a>
</div>

<!-- 两栏：系统状态 + 最近活动 -->
<h3 class="dash-section-title"><i class="ph ph-heartbeat"></i>系统状态</h3>
<div class="dash-grid">
    <div class="card">
        <div class="progress-container">
            <div class="progress-label">
                <span>CPU 使用率</span>
                <strong id="system-cpu">--%</strong>
            </div>
            <span class="prob-bar"><i id="system-cpu-bar" style="width:0%"></i></span>
        </div>
        <div class="progress-container">
            <div class="progress-label">
                <span>内存使用</span>
                <strong id="system-memory">--%</strong>
            </div>
            <span class="prob-bar"><i id="system-memory-bar" style="width:0%"></i></span>
        </div>
        <div class="progress-container">
            <div class="progress-label">
                <span>磁盘空间</span>
                <strong id="system-disk">--%</strong>
            </div>
            <span class="prob-bar"><i id="system-disk-bar" style="width:0%"></i></span>
        </div>
        <div class="progress-container" style="margin-bottom:0;">
            <div class="progress-label">
                <span>网络带宽</span>
                <strong id="system-network">-- KB/s</strong>
            </div>
            <div class="network-row">
                <span>上传 <strong id="network-upload-speed">--</strong> KB/s</span>
                <span>下载 <strong id="network-download-speed">--</strong> KB/s</span>
            </div>
        </div>
    </div>

    <div class="card">
        <ul id="recent-activity" class="activity-list">
            <li class="activity-empty">正在加载最近活动</li>
        </ul>
    </div>
</div>

<!-- 最近上传记录 -->
<h3 class="dash-section-title"><i class="ph ph-clock-counter-clockwise"></i>最近上传记录</h3>
<div class="table-wrap">
    <table class="table">
        <thead>
            <tr>
                <th>ID</th>
                <th>文件名</th>
                <th>识别结果</th>
                <th>置信度</th>
                <th>上传时间</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody id="recent-records">
            <tr>
                <td colspan="6" style="text-align:center;">正在加载最近上传记录</td>
            </tr>
        </tbody>
    </table>
</div>
