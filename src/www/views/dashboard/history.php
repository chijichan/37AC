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
    }

    .history-status.failure {
        color: var(--pico-del-color);
    }
</style>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>📜 使用记录</h1>
    <p>查看你的API使用历史和识别记录</p>
</header>

<!-- 筛选器 -->
<section style="margin-bottom: 2rem;">
    <form class="grid">
        <label>
            时间范围
            <select>
                <option>最近7天</option>
                <option>最近30天</option>
                <option>最近90天</option>
                <option>自定义</option>
            </select>
        </label>
        <label>
            节点
            <select>
                <option>所有节点</option>
                <option>节点 #1</option>
                <option>节点 #2</option>
            </select>
        </label>
        <label>
            状态
            <select>
                <option>全部</option>
                <option>成功</option>
                <option>失败</option>
            </select>
        </label>
        <div style="display: flex; align-items: flex-end;">
            <button type="submit">🔍 筛选</button>
        </div>
    </form>
</section>

<!-- 统计概览 -->
<div class="grid" style="margin-bottom: 2rem;">
    <article style="text-align: center; padding: 1.5rem;">
        <h2 style="margin: 0; color: var(--pico-primary);">2,345</h2>
        <small>总请求数</small>
    </article>
    <article style="text-align: center; padding: 1.5rem;">
        <h2 style="margin: 0; color: var(--pico-ins-color);">2,289</h2>
        <small>成功</small>
    </article>
    <article style="text-align: center; padding: 1.5rem;">
        <h2 style="margin: 0; color: var(--pico-del-color);">56</h2>
        <small>失败</small>
    </article>
    <article style="text-align: center; padding: 1.5rem;">
        <h2 style="margin: 0; color: var(--pico-primary);">97.6%</h2>
        <small>成功率</small>
    </article>
</div>

<!-- 历史记录表格 -->
<section>
    <h2>详细记录</h2>
    <figure>
        <table role="grid">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>节点</th>
                    <th>操作</th>
                    <th>文件名</th>
                    <th>结果</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>2026-01-31 14:23:15</td>
                    <td>节点 #1</td>
                    <td>图片识别</td>
                    <td>image_001.jpg</td>
                    <td>初音未来 (95%)</td>
                    <td><span class="history-status success">✓ 成功</span></td>
                </tr>
                <tr>
                    <td>2026-01-31 14:22:48</td>
                    <td>节点 #1</td>
                    <td>图片上传</td>
                    <td>character_002.png</td>
                    <td>雷电将军 (88%)</td>
                    <td><span class="history-status success">✓ 成功</span></td>
                </tr>
                <tr>
                    <td>2026-01-31 14:20:31</td>
                    <td>节点 #2</td>
                    <td>图片识别</td>
                    <td>anime_003.jpg</td>
                    <td>--</td>
                    <td><span class="history-status failure">✗ 失败</span></td>
                </tr>
                <tr>
                    <td>2026-01-31 14:18:05</td>
                    <td>节点 #1</td>
                    <td>批量上传</td>
                    <td>batch_001.zip</td>
                    <td>156个文件</td>
                    <td><span class="history-status success">✓ 成功</span></td>
                </tr>
                <tr>
                    <td>2026-01-31 14:15:22</td>
                    <td>节点 #1</td>
                    <td>图片识别</td>
                    <td>test_005.png</td>
                    <td>纳西妲 (92%)</td>
                    <td><span style="color: #28a745;">✓ 成功</span></td>
                </tr>
            </tbody>
        </table>
    </figure>

    <!-- 分页 -->
    <nav aria-label="分页导航" style="text-align: center; margin-top: 1rem;">
        <ul style="list-style: none; padding: 0; display: inline-flex; gap: 0.5rem;">
            <li><a href="#" role="button" class="outline secondary">上一页</a></li>
            <li><a href="#" role="button" class="secondary">1</a></li>
            <li><a href="#" role="button" class="outline">2</a></li>
            <li><a href="#" role="button" class="outline">3</a></li>
            <li><a href="#" role="button" class="outline secondary">下一页</a></li>
        </ul>
    </nav>
</section>