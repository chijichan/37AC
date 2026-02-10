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
        background: var(--card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--card-box-shadow);
        margin-bottom: 1.5rem;
    }

    .key-display {
        display: flex;
        gap: 1rem;
        align-items: center;
        background: var(--card-sectionning-background-color);
        padding: 1rem;
        border-radius: var(--pico-border-radius);
        font-family: monospace;
        margin: 1rem 0;
    }

    .key-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .key-actions {
        display: flex;
        gap: 0.5rem;
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>🔑 API密钥管理</h1>
    <p>生成和管理你的API访问密钥</p>
</header>

<!-- 生成新密钥 -->
<section style="margin-bottom: 2rem;">
    <article class="api-key-card">
        <h3>生成新密钥</h3>
        <p>为你的节点生成新的API密钥。每个密钥都有独立的使用配额和权限。</p>
        <form>
            <label>
                密钥名称
                <input type="text" name="key_name" placeholder="例如：生产环境节点" required />
            </label>
            <label>
                权限级别
                <select name="permission">
                    <option value="read">只读</option>
                    <option value="write">读写</option>
                    <option value="admin">管理员</option>
                </select>
            </label>
            <button type="submit">🔐 生成密钥</button>
        </form>
    </article>
</section>

<!-- 现有密钥列表 -->
<section>
    <h2>现有密钥</h2>
    
    <article class="api-key-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <h4 style="margin-top: 0;">生产环境节点</h4>
                <small style="color: var(--muted-color);">创建于 2026-01-15</small>
            </div>
            <span style="padding: 0.25rem 0.75rem; background: #d4edda; color: #155724; border-radius: 5rem; font-size: 0.875rem;">
                ✓ 活跃
            </span>
        </div>

        <div class="key-display">
            <code class="key-text">37ac_prod_k8j2h9g6f5d4s3a2w1q0p9o8i7u6y5t4</code>
            <div class="key-actions">
                <button class="secondary outline" onclick="copyToClipboard(this)" title="复制">📋</button>
                <button class="outline" title="查看">👁️</button>
            </div>
        </div>

        <div class="grid">
            <div>
                <strong>权限级别:</strong> 读写
            </div>
            <div>
                <strong>使用次数:</strong> 1,234 / 10,000
            </div>
            <div>
                <strong>最后使用:</strong> 2小时前
            </div>
        </div>

        <footer style="margin-top: 1rem; text-align: right;">
            <button class="secondary outline">编辑</button>
            <button class="outline" style="color: var(--del-color);">撤销</button>
        </footer>
    </article>

    <article class="api-key-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <h4 style="margin-top: 0;">测试环境</h4>
                <small style="color: var(--muted-color);">创建于 2026-01-20</small>
            </div>
            <span style="padding: 0.25rem 0.75rem; background: #fff3cd; color: #856404; border-radius: 5rem; font-size: 0.875rem;">
                ⏸ 暂停
            </span>
        </div>

        <div class="key-display">
            <code class="key-text">37ac_test_m5n4b3v2c1x0z9l8k7j6h5g4f3d2s1a0</code>
            <div class="key-actions">
                <button class="secondary outline" onclick="copyToClipboard(this)" title="复制">📋</button>
                <button class="outline" title="查看">👁️</button>
            </div>
        </div>

        <div class="grid">
            <div>
                <strong>权限级别:</strong> 只读
            </div>
            <div>
                <strong>使用次数:</strong> 45 / 1,000
            </div>
            <div>
                <strong>最后使用:</strong> 3天前
            </div>
        </div>

        <footer style="margin-top: 1rem; text-align: right;">
            <button class="secondary outline">编辑</button>
            <button class="outline" style="color: var(--del-color);">撤销</button>
        </footer>
    </article>
</section>

<script>
function copyToClipboard(btn) {
    const keyText = btn.closest('.key-display').querySelector('.key-text').textContent;
    navigator.clipboard.writeText(keyText).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓';
        setTimeout(() => {
            btn.innerHTML = originalText;
        }, 2000);
    });
}
</script>
