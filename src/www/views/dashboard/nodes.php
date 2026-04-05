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
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .node-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--pico-box-shadow);
    }

    .node-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .node-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 5rem;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--pico-background-color);
    }

    .node-status.online {
        background: var(--pico-ins-color);
        color: var(--pico-background-color);
    }

    .node-status.offline {
        background: var(--pico-del-color);
        color: var(--pico-background-color);
    }

    .node-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }

    .node-info-item {
        text-align: center;
    }

    .node-info-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: var(--pico-primary);
    }

    .node-info-label {
        font-size: 0.875rem;
        color: var(--pico-muted-color);
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>🖥️ 节点管理</h1>
    <p>管理和监控你的节点状态</p>
</header>

<!-- 操作按钮 -->
<section style="margin-bottom: 2rem;">
    <button>➕ 添加新节点</button>
    <button class="secondary">🔄 刷新状态</button>
</section>

<!-- 节点列表 -->
<section>
    <div id="nodes-list">
        <article class="node-card">
            <div class="node-header">
                <div>
                    <h3 style="margin: 0;">正在加载节点数据…</h3>
                    <small>请稍候</small>
                </div>
            </div>
        </article>
    </div>
</section>