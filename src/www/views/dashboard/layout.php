<?php
// 仪表盘布局：包含全局 layout + 二级导航 + SPA 内容容器
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    /* ===== 二级导航 ===== */
    .dashboard-subnav {
        padding-top: 1.4rem;
    }

    .dash-nav-desktop {
        display: flex;
        gap: .35rem;
        flex-wrap: wrap;
    }

    .dash-nav-desktop a {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .5rem 1.05rem;
        border-radius: var(--ac-radius-pill);
        color: var(--ac-ink-700);
        font-weight: 600;
        font-size: .93rem;
        transition: background var(--ac-dur-fast) var(--ac-ease-out),
            color var(--ac-dur-fast) var(--ac-ease-out);
    }

    .dash-nav-desktop a i {
        font-size: 1.1rem;
    }

    .dash-nav-desktop a:hover {
        background: var(--ac-pink-50);
        color: var(--ac-pink-600);
    }

    .dash-nav-desktop a.active {
        background: var(--ac-pink-100);
        color: var(--ac-pink-700);
    }

    /* 移动端二级导航 */
    .dash-nav-mobile {
        display: none;
        position: relative;
    }

    .dash-nav-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: .65rem 1.1rem;
        border-radius: var(--ac-radius-input);
        background: var(--ac-surface);
        border: 1.5px solid var(--ac-ink-100);
        font-weight: 700;
        font-size: .95rem;
        color: var(--ac-ink-900);
    }

    .dash-nav-toggle .left {
        display: inline-flex;
        align-items: center;
        gap: .5rem;
    }

    .dash-nav-toggle .arrow {
        font-size: .8rem;
        color: var(--ac-ink-500);
        transition: transform var(--ac-dur-fast) var(--ac-ease-out);
    }

    .dash-nav-toggle.open .arrow {
        transform: rotate(180deg);
    }

    .dash-nav-dropdown {
        display: none;
        position: absolute;
        top: calc(100% + 8px);
        left: 0;
        right: 0;
        background: var(--ac-surface);
        border-radius: var(--ac-radius-input);
        box-shadow: var(--ac-shadow-float);
        padding: .45rem;
        z-index: var(--ac-z-dropdown);
    }

    .dash-nav-dropdown.show {
        display: block;
        animation: page-in .2s var(--ac-ease-out);
    }

    .dash-nav-dropdown a {
        display: flex;
        align-items: center;
        gap: .55rem;
        padding: .6rem .8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: .93rem;
        color: var(--ac-ink-700);
    }

    .dash-nav-dropdown a:hover {
        background: var(--ac-pink-50);
        color: var(--ac-pink-600);
    }

    .dash-nav-dropdown a.active {
        background: var(--ac-pink-100);
        color: var(--ac-pink-700);
    }

    /* 内容容器 */
    .dashboard-main {
        padding: 1.6rem 0 3rem;
    }

    #dashboard-content {
        min-height: 400px;
        transition: opacity var(--ac-dur-fast) var(--ac-ease-out);
    }

    .dashboard-loading {
        display: none;
        justify-content: center;
        padding: 3rem;
    }

    .dashboard-loading[aria-busy="true"] {
        display: flex;
    }

    @media (max-width: 768px) {
        .dash-nav-desktop {
            display: none;
        }

        .dash-nav-mobile {
            display: block;
        }
    }
</style>

<div class="dashboard-subnav ac-container">
    <nav class="dash-nav-desktop" aria-label="仪表盘导航">
        <a href="/dashboard" data-page="overview" class="active"><i class="ph ph-gauge"></i>总览</a>
        <a href="/dashboard/nodes" data-page="nodes"><i class="ph ph-share-network"></i>节点管理</a>
        <a href="/dashboard/apikeys" data-page="apikeys"><i class="ph ph-key"></i>API 密钥</a>
        <a href="/dashboard/history" data-page="history"><i class="ph ph-clock-counter-clockwise"></i>使用记录</a>
        <a href="/dashboard/settings" data-page="settings"><i class="ph ph-gear"></i>设置</a>
    </nav>

    <div class="dash-nav-mobile">
        <button class="dash-nav-toggle" id="dashboardNavToggle" type="button" aria-expanded="false">
            <span class="left">
                <span id="currentNavIcon"><i class="ph ph-gauge"></i></span>
                <span id="currentNavText">总览</span>
            </span>
            <span class="arrow"><i class="ph ph-caret-down"></i></span>
        </button>
        <div class="dash-nav-dropdown" id="dashboardNavDropdown">
            <a href="/dashboard" data-page="overview" class="active"><i class="ph ph-gauge"></i>总览</a>
            <a href="/dashboard/nodes" data-page="nodes"><i class="ph ph-share-network"></i>节点管理</a>
            <a href="/dashboard/apikeys" data-page="apikeys"><i class="ph ph-key"></i>API 密钥</a>
            <a href="/dashboard/history" data-page="history"><i class="ph ph-clock-counter-clockwise"></i>使用记录</a>
            <a href="/dashboard/settings" data-page="settings"><i class="ph ph-gear"></i>设置</a>
        </div>
    </div>
</div>

<div class="dashboard-main ac-container">
    <div class="dashboard-loading" id="dashboard-loading" aria-busy="false">
        <span class="skeleton" style="width: 200px; height: 20px;"></span>
    </div>
    <div id="dashboard-content"></div>
</div>

<script>
    // 图标 HTML（Phosphor），供子页面 JS 拼接使用
    var WARN_ICON_SVG = '<i class="ph-bold ph-warning"></i>';
    var HISTORY_ICON_SVG = '<i class="ph ph-clock-counter-clockwise"></i>';
    var USER_ICON_SVG = '<i class="ph ph-user"></i>';
    var APIKEYS_ICON_SVG = '<i class="ph ph-key"></i>';
    var NODES_ICON_SVG = '<i class="ph ph-share-network"></i>';
    var ADD_ICON_SVG = '<i class="ph-bold ph-plus"></i>';
    var LOCK_ICON_SVG = '<i class="ph ph-lock"></i>';
    var REFRESH_ICON_SVG = '<i class="ph ph-arrows-clockwise"></i>';
    var SAVE_ICON_SVG = '<i class="ph ph-floppy-disk"></i>';
    var SETTINGS_ICON_SVG = '<i class="ph ph-gear"></i>';
    var FILTER_ICON_SVG = '<i class="ph ph-funnel"></i>';
    var INFORM_ICON_SVG = '<i class="ph ph-bell"></i>';
    var HEARTBEAT_ICON_SVG = '<i class="ph ph-heartbeat"></i>';
    var START_ICON_SVG = '<i class="ph ph-rocket"></i>';
    var UPLOAD_ICON_SVG = '<i class="ph ph-cloud-arrow-up"></i>';
    var ARTICLE_ICON_SVG = '<i class="ph ph-file-text"></i>';
    var UNLOCK_ICON_SVG = '<i class="ph ph-lock-open"></i>';
    var OVERVIEW_ICON_SVG = '<i class="ph ph-gauge"></i>';

    // 仪表盘异步导航系统
    (function() {
        const contentContainer = document.getElementById('dashboard-content');
        const loadingIndicator = document.getElementById('dashboard-loading');
        const navToggle = document.getElementById('dashboardNavToggle');
        const navDropdown = document.getElementById('dashboardNavDropdown');
        const currentNavIcon = document.getElementById('currentNavIcon');
        const currentNavText = document.getElementById('currentNavText');
        const allNavLinks = document.querySelectorAll('.dash-nav-desktop a, .dash-nav-dropdown a');

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

        const pageInfo = {
            'overview': {
                icon: '<i class="ph ph-gauge"></i>',
                text: '总览',
                title: '仪表盘'
            },
            'nodes': {
                icon: '<i class="ph ph-share-network"></i>',
                text: '节点管理',
                title: '节点管理'
            },
            'apikeys': {
                icon: '<i class="ph ph-key"></i>',
                text: 'API 密钥',
                title: 'API 密钥'
            },
            'history': {
                icon: '<i class="ph ph-clock-counter-clockwise"></i>',
                text: '使用记录',
                title: '使用记录'
            },
            'settings': {
                icon: '<i class="ph ph-gear"></i>',
                text: '设置',
                title: '设置'
            }
        };

        navToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const open = navDropdown.classList.toggle('show');
            navToggle.classList.toggle('open', open);
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        document.addEventListener('click', function(e) {
            if (!navDropdown.contains(e.target) && !navToggle.contains(e.target)) {
                navDropdown.classList.remove('show');
                navToggle.classList.remove('open');
            }
        });

        function init() {
            const page = getPageFromPath(window.location.pathname);
            loadPage(page, false);
        }

        function getPageFromPath(path) {
            if (path === '/dashboard' || path === '/dashboard/') {
                return 'overview';
            }
            const match = path.match(/\/dashboard\/(.+)/);
            return match ? match[1] : 'overview';
        }

        async function loadPage(page, addToHistory = true) {
            updateNavActive(page);

            if (pageInfo[page]) {
                document.title = pageInfo[page].title + ' - 37AC';
                currentNavIcon.innerHTML = pageInfo[page].icon;
                currentNavText.textContent = pageInfo[page].text;
            }

            navDropdown.classList.remove('show');
            navToggle.classList.remove('open');

            const pageHtml = pageTemplates[page];
            if (!pageHtml) {
                contentContainer.innerHTML = `
                    <div class="card empty">
                        <div class="empty-icon"><i class="ph ph-warning"></i></div>
                        <p>无法加载页面：${escapeHtml(page)}</p>
                    </div>`;
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
            // 使用 Auth.fetch 自动携带 Bearer token，并支持 401 自动刷新重试
            return Auth.fetch(url, {
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
                        document.getElementById('stats-accuracy').textContent =
                            stats.accuracy != null ? `${Number(stats.accuracy).toFixed(2)}%` : '—';

                        document.getElementById('system-cpu').textContent = `${system.cpu ?? '—'}%`;
                        document.getElementById('system-memory').textContent = `${system.memory ?? '—'}%`;
                        document.getElementById('system-disk').textContent = `${system.disk ?? '—'}%`;
                        const network = system.network || {};
                        document.getElementById('system-network').textContent =
                            `${(network.upload_speed ?? 0).toFixed(1)} KB/s`;
                        document.getElementById('network-upload-speed').textContent = (network.upload_speed ?? 0).toFixed(1);
                        document.getElementById('network-download-speed').textContent = (network.download_speed ?? 0).toFixed(1);
                        setBar('system-cpu-bar', system.cpu ?? 0);
                        setBar('system-memory-bar', system.memory ?? 0);
                        setBar('system-disk-bar', system.disk ?? 0);

                        const activityList = document.getElementById('recent-activity');
                        if (!activity.length) {
                            activityList.innerHTML = '<li class="activity-empty">暂无最近活动</li>';
                        } else {
                            activityList.innerHTML = activity.map((item) => {
                                const iconHtml = item.type === 'upload' ? UPLOAD_ICON_SVG :
                                    item.type === 'user' ? USER_ICON_SVG :
                                    item.type === 'system' ? SETTINGS_ICON_SVG :
                                    UPLOAD_ICON_SVG;
                                return `
                                    <li class="activity-item">
                                        <div class="activity-icon">${iconHtml}</div>
                                        <div class="activity-content">
                                            <div class="activity-title">${escapeHtml(item.title)}</div>
                                            <div class="activity-desc">${escapeHtml(item.description)}</div>
                                        </div>
                                        <small>${escapeHtml(item.time)}</small>
                                    </li>`;
                            }).join('');
                        }

                        const recordBody = document.getElementById('recent-records');
                        if (!records.length) {
                            recordBody.innerHTML = '<tr><td colspan="6" style="text-align:center;">暂无上传记录</td></tr>';
                        } else {
                            recordBody.innerHTML = records.map((record) => {
                                const conf = Number(record.confidence) || 0;
                                return `
                                    <tr>
                                        <td>${escapeHtml(record.id)}</td>
                                        <td>${escapeHtml(record.filename)}</td>
                                        <td><span class="badge badge-pink">${escapeHtml(record.result)}</span></td>
                                        <td>
                                            <span class="prob-bar"><i style="width:${Math.min(100, conf)}%"></i></span>
                                            <small>${conf}%</small>
                                        </td>
                                        <td>${escapeHtml(record.timestamp)}</td>
                                        <td><a href="/dashboard/history">查看</a></td>
                                    </tr>`;
                            }).join('');
                        }
                    })
                    .catch((error) => {
                        console.error(error);
                    });
            }

            // 其余页面由各自 <script> 内的 load 函数负责渲染
            return window.__pageLoadPromise || Promise.resolve();
        }

        function setBar(id, value) {
            const el = document.getElementById(id);
            if (el) el.style.width = Math.min(100, Number(value) || 0) + '%';
        }

        function updateNavActive(page) {
            allNavLinks.forEach(link => {
                link.classList.toggle('active', link.getAttribute('data-page') === page);
            });
        }

        allNavLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                loadPage(link.getAttribute('data-page'), true);
            });
        });

        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) {
                loadPage(e.state.page, false);
            } else {
                loadPage(getPageFromPath(window.location.pathname), false);
            }
        });

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