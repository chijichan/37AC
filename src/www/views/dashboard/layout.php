<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    /* 仪表盘二级导航 */
    .dashboard-subnav {
        background: var(--pico-card-background-color);
        border-bottom: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        margin-bottom: 2rem;
        padding: 1rem 0;
    }

    /* 桌面导航 */
    .dashboard-nav-desktop {
        display: flex;
        gap: 0.75rem;
        padding-inline: 20px;
        flex-wrap: wrap;
    }

    .dashboard-nav-desktop a {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.25rem;
        text-decoration: none;
        color: var(--pico-color);
        border-radius: var(--pico-border-radius);
        transition: all var(--pico-transition);
        background: var(--pico-card-background-color);
        border: 1px solid var(--pico-muted-border-color);
        box-shadow: var(--pico-box-shadow);
        font-size: 0.95rem;
        font-weight: 500;
    }

    .dashboard-nav-desktop a:hover {
        background: var(--pico-card-sectioning-background-color);
        border-color: var(--pico-primary-hover);
        transform: translateY(-2px);
        box-shadow: var(--pico-box-shadow);
    }

    .dashboard-nav-desktop a.active {
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        border-color: transparent;
        font-weight: 600;
        box-shadow: var(--pico-box-shadow);
    }

    .dashboard-nav-desktop a span {
        font-size: 1.1em;
    }

    /* 移动端下拉菜单 */
    .dashboard-nav-mobile {
        padding-inline: 20px;
        display: none;
        position: relative;
    }

    .dashboard-nav-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.75rem 1rem;
        background: var(--pico-card-background-color);
        border: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        cursor: pointer;
        font-size: 1rem;
        font-weight: 600;
        color: var(--pico-mark-color);
        box-shadow: var(--pico-box-shadow);
        transition: all var(--pico-transition);
    }

    .dashboard-nav-toggle:hover {
        border-color: var(--pico-primary-hover);
        box-shadow: var(--pico-box-shadow);
    }

    .dashboard-nav-toggle .icon {
        display: inline-flex;
        align-items: center;
        margin-right: 0.5rem;
        vertical-align: middle;
    }

    .dashboard-nav-toggle .icon svg {
        width: 1.2em;
        height: 1.2em;
        vertical-align: middle;
    }

    /* image versions of the same icons */
    .dashboard-nav-toggle img.icon {
        width: 1.2em;
        height: 1.2em;
        margin-right: 0.5rem;
    }

    .dashboard-nav-desktop a .icon,
    .dashboard-nav-dropdown a .icon,
    .dashboard-nav-link-mobile .icon {
        width: 1.2em;
        height: auto;
        margin-right: 0.5rem;
        vertical-align: middle;
    }

    .dashboard-nav-toggle .arrow {
        font-size: 0.8em;
        transition: transform 0.3s ease;
    }

    .dashboard-nav-toggle.open .arrow {
        transform: rotate(180deg);
    }

    .dashboard-nav-dropdown {
        display: none;
        position: absolute;
        top: calc(100% + 0.5rem);
        left: 0;
        right: 0;
        background: var(--pico-background-color);
        border: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
        z-index: 1000;
        animation: slideDown 0.3s ease;
    }

    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }

        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .dashboard-nav-dropdown.show {
        display: block;
    }

    .dashboard-nav-dropdown a {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.875rem 1.25rem;
        text-decoration: none;
        color: var(--pico-color);
        transition: all var(--pico-transition);
        border-bottom: 1px solid var(--pico-muted-border-color);
        font-weight: 500;
    }

    .dashboard-nav-dropdown a:last-child {
        border-bottom: none;
    }

    .dashboard-nav-dropdown a:hover {
        background: var(--pico-card-sectioning-background-color);
        padding-left: 1.5rem;
    }

    .dashboard-nav-dropdown a.active {
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        font-weight: 600;
        border-left: 3px solid var(--pico-primary);
    }

    .dashboard-nav-dropdown a span {
        font-size: 1.2em;
    }

    /* 响应式设计 */
    @media (max-width: 768px) {
        .dashboard-nav-desktop {
            display: none;
        }

        .dashboard-nav-mobile {
            display: block;
        }
    }

    /* 仪表盘内容容器 */
    #dashboard-content {
        min-height: 400px;
        transition: opacity 0.3s ease;
    }

    /* 加载指示器，使用 PicoCSS aria-busy 特性 */
    .dashboard-loading {
        display: none;
        text-align: center;
        padding: 3rem;
    }

    /* 当 aria-busy 为 true 时显示指示器 */
    .dashboard-loading[aria-busy="true"] {
        display: block;
    }

    /* 保留简洁样式，如有自定义内容可以在 HTML 内添加 */

    /* danger-outline buttons */
    button.outline.danger {
        color: var(--pico-del-color);
        border-color: var(--pico-del-color);
        /* hover/active */
        --pico-button-hover-box-shadow: 0 0 0 var(--pico-outline-width) var(--pico-del-color);
        --pico-box-shadow: 0 0 0 var(--pico-outline-width) var(--pico-del-color);
    }

    button.outline.danger:focus {
        /* focus */
        --pico-box-shadow: 0 0 0 var(--pico-outline-width) var(--pico-del-color);
    }
</style>

<!-- 仪表盘二级导航 -->
<div class="dashboard-subnav container">
    <div class="container">
        <!-- 桌面端导航 -->
        <nav class="dashboard-nav-desktop">
            <a href="/dashboard" data-page="overview" class="dashboard-nav-link active">
                <?php require ROOT_PATH . '/views/components/icons/overview.php'; ?>
                总览
            </a>
            <a href="/dashboard/nodes" data-page="nodes" class="dashboard-nav-link">
                <?php require ROOT_PATH . '/views/components/icons/nodes.php'; ?>节点管理
            </a>
            <a href="/dashboard/apikeys" data-page="apikeys" class="dashboard-nav-link">
                <?php require ROOT_PATH . '/views/components/icons/apikeys.php'; ?>API密钥
            </a>
            <a href="/dashboard/history" data-page="history" class="dashboard-nav-link">
                <?php require ROOT_PATH . '/views/components/icons/history.php'; ?>使用记录
            </a>
            <a href="/dashboard/settings" data-page="settings" class="dashboard-nav-link">
                <?php require ROOT_PATH . '/views/components/icons/settings.php'; ?>设置
            </a>
        </nav>

        <!-- 移动端下拉导航 -->
        <div class="dashboard-nav-mobile">
            <button class="dashboard-nav-toggle" id="dashboardNavToggle" type="button">
                <span>
                    <span class="icon" id="currentNavIcon">
                        <?php require ROOT_PATH . '/views/components/icons/overview.php'; ?>
                    </span>
                    <span id="currentNavText">总览</span>
                </span>
                <span class="arrow">▼</span>
            </button>
            <div class="dashboard-nav-dropdown" id="dashboardNavDropdown">
                <a href="/dashboard" data-page="overview" class="dashboard-nav-link-mobile active">
                    <?php require ROOT_PATH . '/views/components/icons/overview.php'; ?>
                    总览
                </a>
                <a href="/dashboard/nodes" data-page="nodes" class="dashboard-nav-link-mobile">
                    <?php require ROOT_PATH . '/views/components/icons/nodes.php'; ?>节点管理
                </a>
                <a href="/dashboard/apikeys" data-page="apikeys" class="dashboard-nav-link-mobile">
                    <?php require ROOT_PATH . '/views/components/icons/apikeys.php'; ?>API密钥
                </a>
                <a href="/dashboard/history" data-page="history" class="dashboard-nav-link-mobile">
                    <?php require ROOT_PATH . '/views/components/icons/history.php'; ?>使用记录
                </a>
                <a href="/dashboard/settings" data-page="settings" class="dashboard-nav-link-mobile">
                    <?php require ROOT_PATH . '/views/components/icons/settings.php'; ?>设置
                </a>
            </div>
        </div>
    </div>
</div>

<!-- 仪表盘内容区域 -->
<main class="container">
    <!-- 加载指示器（PicoCSS aria-busy） -->
    <div class="dashboard-loading" id="dashboard-loading" aria-busy="false"></div>

    <!-- 动态内容容器 -->
    <div id="dashboard-content">
        <!-- 页面内容将通过 AJAX 加载到这里 -->
    </div>
</main>

<script>
    // 全局 SVG 图标变量（供子页面 JS 使用，必须在 IIFE 外部定义）
    var WARN_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/warn.php')); ?>;
    var HISTORY_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/history.php')); ?>;
    var USER_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/user.php')); ?>;
    var APIKEYS_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/apikeys.php')); ?>;
    var NODES_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/nodes.php')); ?>;
    var ADD_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/add.php')); ?>;
    var LOCK_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/lock.php')); ?>;
    var REFRESH_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/refresh.php')); ?>;
    var SAVE_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/save.php')); ?>;
    var SETTINGS_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/settings.php')); ?>;
    var FILTER_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/filter.php')); ?>;
    var INFORM_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/inform.php')); ?>;
    var HEARTBEAT_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/heartbeat.php')); ?>;
    var START_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/start.php')); ?>;
    var UPLOAD_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/upload.php')); ?>;
    var ARTICLE_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/article.php')); ?>;
    var UNLOCK_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/unlock.php')); ?>;
    var OVERVIEW_ICON_SVG = <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/overview.php')); ?>;

    // 仪表盘异步导航系统
    (function() {
        const contentContainer = document.getElementById('dashboard-content');
        const loadingIndicator = document.getElementById('dashboard-loading');
        const navLinksDesktop = document.querySelectorAll('.dashboard-nav-link');
        const navLinksMobile = document.querySelectorAll('.dashboard-nav-link-mobile');
        const navToggle = document.getElementById('dashboardNavToggle');
        const navDropdown = document.getElementById('dashboardNavDropdown');
        const currentNavIcon = document.getElementById('currentNavIcon');
        const currentNavText = document.getElementById('currentNavText');

        // 当前激活的页面
        let currentPage = 'overview';

        function setLoading(active) {
            if (!loadingIndicator) return;
            loadingIndicator.setAttribute('aria-busy', active ? 'true' : 'false');
            contentContainer.style.opacity = active ? '0.5' : '1';
        }

        <?php
        function capture_dashboard_fragment(string $path)
        {
            $backupGet = $_GET;
            $_GET['ajax'] = '1';
            ob_start();
            require $path;
            $content = ob_get_clean();
            $_GET = $backupGet;
            return $content;
        }

        $dashboardTemplates = [
            'overview' => capture_dashboard_fragment(ROOT_PATH . '/views/dashboard/overview.php'),
            'nodes' => capture_dashboard_fragment(ROOT_PATH . '/views/dashboard/nodes.php'),
            'apikeys' => capture_dashboard_fragment(ROOT_PATH . '/views/dashboard/apikeys.php'),
            'history' => capture_dashboard_fragment(ROOT_PATH . '/views/dashboard/history.php'),
            'settings' => capture_dashboard_fragment(ROOT_PATH . '/views/dashboard/settings.php'),
        ];
        ?>

        const pageTemplates = {
            'overview': <?php echo json_encode($dashboardTemplates['overview']); ?>,
            'nodes': <?php echo json_encode($dashboardTemplates['nodes']); ?>,
            'apikeys': <?php echo json_encode($dashboardTemplates['apikeys']); ?>,
            'history': <?php echo json_encode($dashboardTemplates['history']); ?>,
            'settings': <?php echo json_encode($dashboardTemplates['settings']); ?>,
        };

        // 页面信息映射
        const warnIconSvg = WARN_ICON_SVG;

        const pageInfo = {
            'overview': {
                icon: <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/overview.php')); ?>,
                text: '总览',
                title: '仪表盘'
            },
            'nodes': {
                icon: <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/nodes.php')); ?>,
                text: '节点管理',
                title: '节点管理'
            },
            'apikeys': {
                icon: <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/apikeys.php')); ?>,
                text: 'API密钥',
                title: 'API密钥'
            },
            'history': {
                icon: <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/history.php')); ?>,
                text: '使用记录',
                title: '使用记录'
            },
            'settings': {
                icon: <?php echo json_encode(file_get_contents(ROOT_PATH . '/views/components/icons/settings.php')); ?>,
                text: '设置',
                title: '设置'
            }
        };

        // 移动端下拉菜单切换
        navToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            navDropdown.classList.toggle('show');
            navToggle.classList.toggle('open');
        });

        // 点击页面其他地方关闭下拉菜单
        document.addEventListener('click', function(e) {
            if (!navDropdown.contains(e.target) && !navToggle.contains(e.target)) {
                navDropdown.classList.remove('show');
                navToggle.classList.remove('open');
            }
        });

        // 初始化：加载当前页面
        function init() {
            const path = window.location.pathname;
            const page = getPageFromPath(path);
            loadPage(page, false);
        }

        // 从路径获取页面名称
        function getPageFromPath(path) {
            if (path === '/dashboard' || path === '/dashboard/') {
                return 'overview';
            }
            const match = path.match(/\/dashboard\/(.+)/);
            return match ? match[1] : 'overview';
        }

        // 加载页面内容
        async function loadPage(page, addToHistory = true) {
            // 更新导航激活状态
            updateNavActive(page);

            // 更新网页标题
            if (pageInfo[page]) {
                document.title = pageInfo[page].title + ' - 37AC';
            }

            // 更新移动端下拉按钮显示
            updateMobileNav(page);

            // 关闭移动端下拉菜单
            navDropdown.classList.remove('show');
            navToggle.classList.remove('open');

            // 加载本地模板
            const pageHtml = pageTemplates[page];
            if (!pageHtml) {
                contentContainer.innerHTML = `
                    <article style="text-align: center; padding: 3rem;">
                        <h2>${warnIconSvg} 页面未找到</h2>
                        <p>无法加载页面：${page}</p>
                    </article>
                `;
                return;
            }

            setLoading(true);
            contentContainer.innerHTML = pageHtml;
            executePageScripts(contentContainer);
            initializeDashboardPage(page);
            currentPage = page;

            try {
                await renderPageData(page);
            } finally {
                setLoading(false);
            }

            if (addToHistory) {
                const url = page === 'overview' ? '/dashboard' : `/dashboard/${page}`;
                history.pushState({
                    page
                }, '', url);
            }
        }

        function executePageScripts(container) {
            const scripts = Array.from(container.querySelectorAll('script'));
            scripts.forEach((script) => {
                const newScript = document.createElement('script');
                Array.from(script.attributes).forEach((attr) => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                if (script.src) {
                    newScript.src = script.src;
                    newScript.async = false;
                } else {
                    newScript.textContent = script.textContent;
                }
                script.parentNode.replaceChild(newScript, script);
            });
        }

        function initializeDashboardPage(page) {
            if (typeof window.dashboardPageInit === 'function') {
                try {
                    window.dashboardPageInit(page);
                } finally {
                    window.dashboardPageInit = null;
                }
            }
        }

        function fetchJson(url) {
            return fetch(url, {
                headers: {
                    Accept: 'application/json'
                }
            }).then((response) => {
                if (!response.ok) {
                    throw new Error('接口请求失败');
                }
                return response.json();
            });
        }

        function renderPageData(page) {
            if (page === 'overview') {
                return fetchJson(`${window.API_BASE_URL}/dashboard/summary`)
                    .then((payload) => {
                        const data = payload.data || {};
                        const stats = data.stats || {};
                        const system = data.system || {};
                        const activity = data.recent_activity || [];
                        const records = data.recent_records || [];

                        document.getElementById('stats-total-visits').textContent = stats.total_visits ?? '—';
                        document.getElementById('stats-total-uploads').textContent = stats.total_uploads ?? '—';
                        document.getElementById('stats-active-users').textContent = stats.active_users ?? '—';
                        document.getElementById('stats-accuracy').textContent = `${stats.accuracy.toFixed(2) ?? '—'}%`;

                        document.getElementById('system-cpu').textContent = `${system.cpu ?? '—'}%`;
                        document.getElementById('system-memory').textContent = `${system.memory ?? '—'}%`;
                        document.getElementById('system-disk').textContent = `${system.disk ?? '—'}%`;
                        const network = system.network || {};
                        document.getElementById('system-network').textContent = `${(network.upload_speed ?? 0).toFixed(1)} KB/s`;
                        document.getElementById('network-upload-speed').textContent = (network.upload_speed ?? 0).toFixed(1);
                        document.getElementById('network-download-speed').textContent = (network.download_speed ?? 0).toFixed(1);
                        document.getElementById('system-cpu-progress').value = system.cpu ?? 0;
                        document.getElementById('system-memory-progress').value = system.memory ?? 0;
                        document.getElementById('system-disk-progress').value = system.disk ?? 0;

                        const activityList = document.getElementById('recent-activity');
                        activityList.innerHTML = activity
                            .map((item) => {
                                const iconSvg = item.type === 'upload' ? UPLOAD_ICON_SVG :
                                    item.type === 'user' ? USER_ICON_SVG :
                                    item.type === 'system' ? SETTINGS_ICON_SVG :
                                    UPLOAD_ICON_SVG;
                                return `
                                    <li class="activity-item">
                                        <div class="activity-icon ${item.type || 'upload'}">${iconSvg}</div>
                                        <div class="activity-content">
                                            <div class="activity-title">${item.title}</div>
                                            <div class="activity-time">${item.description}</div>
                                        </div>
                                        <small>${item.time}</small>
                                    </li>`;
                            })
                            .join('');

                        const recordBody = document.getElementById('recent-records');
                        recordBody.innerHTML = records
                            .map(
                                (record) => `
                                    <tr>
                                        <td>${record.id}</td>
                                        <td>${record.filename}</td>
                                        <td><mark>${record.result}</mark></td>
                                        <td>
                                            <progress value="${record.confidence}" max="100"></progress>
                                            <small>${record.confidence}%</small>
                                        </td>
                                        <td>${record.timestamp}</td>
                                        <td><a href="#" class="secondary outline">查看</a></td>
                                    </tr>`
                            )
                            .join('');
                    })
                    .catch((error) => {
                        console.error(error);
                    });
            } else if (page === 'nodes') {
                // nodes.php 自己的 <script> 标签负责渲染
                return Promise.resolve();
            } else if (page === 'history') {
                // history.php 自己的 loadHistory() 负责渲染
                return Promise.resolve();
            }

            return Promise.resolve();
        }

        function copyToClipboard(btn) {
            const keyText = btn.closest('.key-display').querySelector('.key-text').textContent;
            navigator.clipboard.writeText(keyText).then(() => {
                const originalText = btn.innerHTML;
                btn.innerHTML = '已复制';
                setTimeout(() => {
                    btn.innerHTML = originalText;
                }, 2000);
            });
        }

        // 更新导航激活状态（桌面端）
        function updateNavActive(page) {
            // 更新桌面端导航
            navLinksDesktop.forEach(link => {
                const linkPage = link.getAttribute('data-page');
                if (linkPage === page) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });

            // 更新移动端导航
            navLinksMobile.forEach(link => {
                const linkPage = link.getAttribute('data-page');
                if (linkPage === page) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });
        }

        // 更新移动端下拉按钮显示
        function updateMobileNav(page) {
            if (pageInfo[page]) {
                currentNavIcon.innerHTML = pageInfo[page].icon;
                currentNavText.textContent = pageInfo[page].text;
            }
        }

        // 绑定桌面端导航点击事件
        navLinksDesktop.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                loadPage(page, true);
            });
        });

        // 绑定移动端导航点击事件
        navLinksMobile.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                loadPage(page, true);
            });
        });

        // 处理浏览器前进/后退
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) {
                loadPage(e.state.page, false);
            } else {
                const page = getPageFromPath(window.location.pathname);
                loadPage(page, false);
            }
        });

        // 页面加载完成后初始化
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    })();
</script>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>