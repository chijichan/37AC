<style>
    /* 仪表盘自定义样式，尽可能使用 Pico 变量 */
    .dashboard-header {
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        padding: 2rem;
        margin-bottom: 2rem;
        border-radius: var(--pico-border-radius);
        text-align: center;
    }

    .dashboard-header h1 {
        color: inherit;
        margin-bottom: 0.5rem;
    }

    .dashboard-header p {
        opacity: 0.9;
        margin: 0;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    .stat-card {
        background: var(--pico-card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--pico-box-shadow);
    }

    .stat-card h3 {
        margin-top: 0;
        font-size: 0.875rem;
        text-transform: uppercase;
        color: var(--pico-muted-color);
        font-weight: 600;
    }

    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
        color: var(--pico-primary);
    }

    .stat-change {
        font-size: 0.875rem;
        color: var(--pico-muted-color);
    }

    .stat-change.positive {
        color: var(--pico-ins-color);
    }

    .stat-change.negative {
        color: var(--pico-del-color);
    }

    .chart-container {
        background: var(--pico-card-background-color);
        padding: 1.5rem;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        margin-bottom: 2rem;
    }

    .activity-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .activity-item {
        display: flex;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid var(--pico-muted-border-color);
        transition: background-color 0.2s ease;
    }

    .activity-item:hover {
        background-color: var(--pico-card-sectioning-background-color);
    }

    .activity-item:last-child {
        border-bottom: none;
    }

    .activity-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 1rem;
        font-weight: bold;
        color: var(--pico-background-color);
    }

    .activity-icon.upload {
        background: var(--pico-primary-background);
    }

    .activity-icon.user {
        background: var(--pico-secondary-background);
    }

    .activity-icon.system {
        background: var(--pico-contrast-background);
    }

    .activity-content {
        flex: 1;
    }

    .activity-title {
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .activity-time {
        font-size: 0.875rem;
        color: var(--pico-muted-color);
    }

    .quick-actions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }

    .action-button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 1rem;
        text-decoration: none;
        border-radius: var(--pico-border-radius);
        transition: all 0.3s ease;
        background: var(--pico-card-background-color);
        box-shadow: var(--pico-box-shadow);
    }

    .action-button:hover {
        transform: translateY(-5px);
        box-shadow: var(--pico-box-shadow);
    }

    .action-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    .progress-container {
        margin-bottom: 1rem;
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
    }

    progress {
        width: 100%;
        height: 8px;
    }
</style>

<!-- 仪表盘头部 -->
<div class="dashboard-header">
    <h1>📊 仪表盘总览</h1>
    <p>欢迎回来!这是你的项目概览</p>
</div>

<!-- 统计卡片 -->
<div class="stats-grid">
    <article class="stat-card">
        <h3>总访问量</h3>
        <div class="stat-value">12,345</div>
        <div class="stat-change positive">
            ↑ 15.3% 较上月
        </div>
    </article>

    <article class="stat-card">
        <h3>图片上传</h3>
        <div class="stat-value">8,567</div>
        <div class="stat-change positive">
            ↑ 23.1% 较上月
        </div>
    </article>

    <article class="stat-card">
        <h3>活跃用户</h3>
        <div class="stat-value">1,234</div>
        <div class="stat-change positive">
            ↑ 8.2% 较上月
        </div>
    </article>

    <article class="stat-card">
        <h3>识别准确率</h3>
        <div class="stat-value">94.5%</div>
        <div class="stat-change negative">
            ↓ 1.2% 较上月
        </div>
    </article>
</div>

<!-- 快速操作 -->
<section>
    <h2>🚀 快速操作</h2>
    <div class="quick-actions">
        <a href="/upload" class="action-button">
            <div class="action-icon">📤</div>
            <strong>上传图片</strong>
        </a>
        <a href="/users" class="action-button">
            <div class="action-icon">👥</div>
            <strong>用户管理</strong>
        </a>
        <a href="/settings" class="action-button">
            <div class="action-icon">⚙️</div>
            <strong>系统设置</strong>
        </a>
        <a href="/reports" class="action-button">
            <div class="action-icon">📈</div>
            <strong>数据报表</strong>
        </a>
    </div>
</section>

<!-- 两栏布局 -->
<div class="grid">
    <!-- 左侧:系统状态 -->
    <section>
        <article class="chart-container">
            <h2>💻 系统状态</h2>

            <div class="progress-container">
                <div class="progress-label">
                    <span>CPU 使用率</span>
                    <strong>45%</strong>
                </div>
                <progress value="45" max="100"></progress>
            </div>

            <div class="progress-container">
                <div class="progress-label">
                    <span>内存使用</span>
                    <strong>68%</strong>
                </div>
                <progress value="68" max="100"></progress>
            </div>

            <div class="progress-container">
                <div class="progress-label">
                    <span>磁盘空间</span>
                    <strong>52%</strong>
                </div>
                <progress value="52" max="100"></progress>
            </div>

            <div class="progress-container">
                <div class="progress-label">
                    <span>网络带宽</span>
                    <strong>34%</strong>
                </div>
                <progress value="34" max="100"></progress>
            </div>

            <footer style="margin-top: 1.5rem;">
                <small>最后更新: <?php echo date('Y-m-d H:i:s'); ?></small>
            </footer>
        </article>
    </section>

    <!-- 右侧:最近活动 -->
    <section>
        <article class="chart-container">
            <h2>📋 最近活动</h2>
            <ul class="activity-list">
                <li class="activity-item">
                    <div class="activity-icon upload">📤</div>
                    <div class="activity-content">
                        <div class="activity-title">新图片上传</div>
                        <div class="activity-time">用户 张三 上传了 3 张图片</div>
                    </div>
                    <small>2分钟前</small>
                </li>
                <li class="activity-item">
                    <div class="activity-icon user">👤</div>
                    <div class="activity-content">
                        <div class="activity-title">新用户注册</div>
                        <div class="activity-time">李四 注册了新账户</div>
                    </div>
                    <small>15分钟前</small>
                </li>
                <li class="activity-item">
                    <div class="activity-icon system">⚙️</div>
                    <div class="activity-content">
                        <div class="activity-title">系统更新</div>
                        <div class="activity-time">AI 模型已更新到 v2.1</div>
                    </div>
                    <small>1小时前</small>
                </li>
                <li class="activity-item">
                    <div class="activity-icon upload">📤</div>
                    <div class="activity-content">
                        <div class="activity-title">批量识别完成</div>
                        <div class="activity-time">成功识别 156 张图片</div>
                    </div>
                    <small>2小时前</small>
                </li>
                <li class="activity-item">
                    <div class="activity-icon user">👤</div>
                    <div class="activity-content">
                        <div class="activity-title">权限变更</div>
                        <div class="activity-time">管理员修改了用户权限</div>
                    </div>
                    <small>3小时前</small>
                </li>
            </ul>
        </article>
    </section>
</div>

<!-- 数据表格示例 -->
<section class="overflow-auto">
    <h2>📊 最近上传记录</h2>
    <figure>
        <table role="grid">
            <thead>
                <tr>
                    <th scope="col">ID</th>
                    <th scope="col">文件名</th>
                    <th scope="col">识别结果</th>
                    <th scope="col">置信度</th>
                    <th scope="col">上传时间</th>
                    <th scope="col">操作</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>1001</td>
                    <td>anime_char_01.jpg</td>
                    <td><mark>初音未来</mark></td>
                    <td>
                        <progress value="95" max="100">95%</progress>
                        <small>95%</small>
                    </td>
                    <td>2026-01-31 10:24</td>
                    <td>
                        <a href="#" role="button" class="secondary outline">查看</a>
                    </td>
                </tr>
                <tr>
                    <td>1002</td>
                    <td>character_02.png</td>
                    <td><mark>雷电将军</mark></td>
                    <td>
                        <progress value="88" max="100">88%</progress>
                        <small>88%</small>
                    </td>
                    <td>2026-01-31 10:18</td>
                    <td>
                        <a href="#" role="button" class="secondary outline">查看</a>
                    </td>
                </tr>
                <tr>
                    <td>1003</td>
                    <td>image_03.jpg</td>
                    <td><mark>纳西妲</mark></td>
                    <td>
                        <progress value="92" max="100">92%</progress>
                        <small>92%</small>
                    </td>
                    <td>2026-01-31 10:05</td>
                    <td>
                        <a href="#" role="button" class="secondary outline">查看</a>
                    </td>
                </tr>
            </tbody>
        </table>
    </figure>
</section>

<!-- 警告和通知 -->
<section>
    <h2>🔔 系统通知</h2>
    <article>
        <header>
            <strong>✅ 系统运行正常</strong>
        </header>
        <p>所有服务正常运行,没有检测到异常情况。</p>
        <footer>
            <small>最后检查: <?php echo date('Y-m-d H:i:s'); ?></small>
        </footer>
    </article>

    <article style="margin-top: 1rem;">
        <header>
            <strong>⚠️ 注意事项</strong>
        </header>
        <p>您的存储空间使用率已达到 75%,建议及时清理旧文件。</p>
        <footer>
            <a href="#" role="button" class="outline">立即处理</a>
        </footer>
    </article>
</section>