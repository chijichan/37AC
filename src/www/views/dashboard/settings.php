<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/dashboard/layout.php';
    exit;
}
?>

<!-- 页面标题 -->
<header style="margin-bottom: 2rem;">
    <h1>⚙️ 设置</h1>
    <p>管理你的账户和偏好设置</p>
</header>

<!-- 个人信息 -->
<section>
    <article>
        <h2>👤 个人信息</h2>
        <form>
            <div class="grid">
                <label>
                    用户名
                    <input type="text" value="user123" disabled />
                </label>
                <label>
                    邮箱
                    <input type="email" value="user@example.com" />
                </label>
            </div>
            <label>
                显示名称
                <input type="text" value="张三" />
            </label>
            <label>
                个人简介
                <textarea rows="3">一名热心的节点运营者</textarea>
            </label>
            <button type="submit">💾 保存更改</button>
        </form>
    </article>
</section>

<!-- 安全设置 -->
<section style="margin-top: 2rem;">
    <article>
        <h2>🔒 安全设置</h2>
        <form>
            <label>
                当前密码
                <input type="password" placeholder="输入当前密码" />
            </label>
            <div class="grid">
                <label>
                    新密码
                    <input type="password" placeholder="输入新密码" />
                </label>
                <label>
                    确认密码
                    <input type="password" placeholder="再次输入新密码" />
                </label>
            </div>
            <button type="submit" class="secondary">🔑 更改密码</button>
        </form>

        <hr />

        <h3>两步验证</h3>
        <p>增强账户安全性，启用两步验证。</p>
        <label>
            <input type="checkbox" role="switch" />
            启用两步验证
        </label>
    </article>
</section>

<!-- 通知设置 -->
<section style="margin-top: 2rem;">
    <article>
        <h2>🔔 通知设置</h2>
        <p>选择你希望接收的通知类型。</p>

        <label>
            <input type="checkbox" role="switch" checked />
            节点状态变更通知
        </label>
        <label>
            <input type="checkbox" role="switch" checked />
            API配额预警
        </label>
        <label>
            <input type="checkbox" role="switch" />
            系统维护通知
        </label>
        <label>
            <input type="checkbox" role="switch" />
            新功能和更新
        </label>

        <button type="submit" style="margin-top: 1rem;">💾 保存通知设置</button>
    </article>
</section>

<!-- 危险区域 -->
<section style="margin-top: 2rem;">
    <article style="border: 2px solid var(--pico-del-color);">
        <h2 style="color: var(--pico-del-color);">⚠️ 危险区域</h2>
        <p>这些操作不可逆，请谨慎操作。</p>

        <hr />

        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
                <strong>撤销所有API密钥</strong>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--pico-muted-color);">
                    立即禁用所有现有的API密钥
                </p>
            </div>
            <button class="outline danger">撤销全部</button>
        </div>

        <hr />

        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>删除账户</strong>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--pico-muted-color);">
                    永久删除你的账户和所有数据
                </p>
            </div>
            <button class="outline danger">删除账户</button>
        </div>
    </article>
</section>