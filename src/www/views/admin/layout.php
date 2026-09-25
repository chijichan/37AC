<?php
// 后台管理布局：独立于用户仪表盘，仅管理员可访问
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .admin-badge {
        display: inline-block;
        padding: .15rem .5rem;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-pink-100);
        color: var(--ac-pink-700);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .04em;
        vertical-align: middle;
    }

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

    .admin-head-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
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
    <div class="admin-head-row" style="margin-bottom:.6rem;">
        <h2 style="margin:0;font-size:1.15rem;">后台管理 <span class="admin-badge">ADMIN</span></h2>
        <small style="color:var(--ac-ink-500);">37AC 管理控制台</small>
    </div>

    <nav class="dash-nav-desktop" aria-label="后台管理导航">
        <a href="/admin" data-page="overview" class="active"><i class="ph ph-gauge"></i>系统概况</a>
        <a href="/admin/users" data-page="users"><i class="ph ph-user"></i>用户管理</a>
        <a href="/admin/nodes" data-page="nodes"><i class="ph ph-share-network"></i>节点管理</a>
        <a href="/admin/tasks" data-page="tasks"><i class="ph ph-clock-counter-clockwise"></i>任务记录</a>
        <a href="/admin/settings" data-page="settings"><i class="ph ph-gear"></i>系统设置</a>
    </nav>

    <div class="dash-nav-mobile">
        <button class="dash-nav-toggle" id="dashboardNavToggle" type="button" aria-expanded="false">
            <span class="left">
                <span id="currentNavIcon"><i class="ph ph-gauge"></i></span>
                <span id="currentNavText">系统概况</span>
            </span>
            <span class="arrow"><i class="ph ph-caret-down"></i></span>
        </button>
        <div class="dash-nav-dropdown" id="dashboardNavDropdown">
            <a href="/admin" data-page="overview" class="active"><i class="ph ph-gauge"></i>系统概况</a>
            <a href="/admin/users" data-page="users"><i class="ph ph-user"></i>用户管理</a>
            <a href="/admin/nodes" data-page="nodes"><i class="ph ph-share-network"></i>节点管理</a>
            <a href="/admin/tasks" data-page="tasks"><i class="ph ph-clock-counter-clockwise"></i>任务记录</a>
            <a href="/admin/settings" data-page="settings"><i class="ph ph-gear"></i>系统设置</a>
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
    // 子页面 JS 用到的图标
    var WARN_ICON_SVG = '<i class="ph-bold ph-warning"></i>';
    var USER_ICON_SVG = '<i class="ph ph-user"></i>';
    var HISTORY_ICON_SVG = '<i class="ph ph-clock-counter-clockwise"></i>';
    var NODES_ICON_SVG = '<i class="ph ph-share-network"></i>';
    var ADD_ICON_SVG = '<i class="ph-bold ph-plus"></i>';
    var REFRESH_ICON_SVG = '<i class="ph ph-arrows-clockwise"></i>';
    var SAVE_ICON_SVG = '<i class="ph ph-floppy-disk"></i>';
    var SETTINGS_ICON_SVG = '<i class="ph ph-gear"></i>';
    var UPLOAD_ICON_SVG = '<i class="ph ph-cloud-arrow-up"></i>';
    var LOCK_ICON_SVG = '<i class="ph ph-lock"></i>';
    var UNLOCK_ICON_SVG = '<i class="ph ph-lock-open"></i>';
    var OVERVIEW_ICON_SVG = '<i class="ph ph-gauge"></i>';
    var FILTER_ICON_SVG = '<i class="ph ph-funnel"></i>';
    var HEARTBEAT_ICON_SVG = '<i class="ph ph-heartbeat"></i>';
    var START_ICON_SVG = '<i class="ph ph-rocket"></i>';
    var ARTICLE_ICON_SVG = '<i class="ph ph-file-text"></i>';

    (function() {
        const contentContainer = document.getElementById('dashboard-content');
        const loadingIndicator = document.getElementById('dashboard-loading');
        const navToggle = document.getElementById('dashboardNavToggle');
        const navDropdown = document.getElementById('dashboardNavDropdown');
        const currentNavIcon = document.getElementById('currentNavIcon');
        const currentNavText = document.getElementById('currentNavText');
        const allNavLinks = document.querySelectorAll('.dash-nav-desktop a, .dash-nav-dropdown a');

        function setLoading(active) {
            if (!loadingIndicator) return;
            loadingIndicator.setAttribute('aria-busy', active ? 'true' : 'false');
            contentContainer.style.opacity = active ? '0.5' : '1';
        }

        <?php
        function capture_admin_fragment(string $path)
        {
            $backupGet = $_GET;
            $_GET['ajax'] = '1';
            ob_start();
            require $path;
            $content = ob_get_clean();
            $_GET = $backupGet;
            return $content;
        }

        $adminTemplates = [
            'overview' => capture_admin_fragment(ROOT_PATH . '/views/admin/overview.php'),
            'users' => capture_admin_fragment(ROOT_PATH . '/views/admin/users.php'),
            'nodes' => capture_admin_fragment(ROOT_PATH . '/views/admin/nodes.php'),
            'tasks' => capture_admin_fragment(ROOT_PATH . '/views/admin/tasks.php'),
            'settings' => capture_admin_fragment(ROOT_PATH . '/views/admin/settings.php'),
        ];
        ?>

        const pageTemplates = {
            'overview': <?php echo json_encode($adminTemplates['overview']); ?>,
            'users': <?php echo json_encode($adminTemplates['users']); ?>,
            'nodes': <?php echo json_encode($adminTemplates['nodes']); ?>,
            'tasks': <?php echo json_encode($adminTemplates['tasks']); ?>,
            'settings': <?php echo json_encode($adminTemplates['settings']); ?>,
        };

        const pageInfo = {
            'overview': { icon: '<i class="ph ph-gauge"></i>', text: '系统概况', title: '系统概况' },
            'users': { icon: '<i class="ph ph-user"></i>', text: '用户管理', title: '用户管理' },
            'nodes': { icon: '<i class="ph ph-share-network"></i>', text: '节点管理', title: '节点管理' },
            'tasks': { icon: '<i class="ph ph-clock-counter-clockwise"></i>', text: '任务记录', title: '任务记录' },
            'settings': { icon: '<i class="ph ph-gear"></i>', text: '系统设置', title: '系统设置' }
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

        function getPageFromPath(path) {
            const match = path.match(/\/admin\/([^/?#]+)/);
            return match ? match[1] : 'overview';
        }

        function init() {
            loadPage(getPageFromPath(window.location.pathname), false);
        }

        async function loadPage(page, addToHistory = true) {
            updateNavActive(page);
            if (pageInfo[page]) {
                document.title = pageInfo[page].title + ' - 37AC 后台';
                currentNavIcon.innerHTML = pageInfo[page].icon;
                currentNavText.textContent = pageInfo[page].text;
            }
            navDropdown.classList.remove('show');
            navToggle.classList.remove('open');

            const pageHtml = pageTemplates[page];
            if (!pageHtml) {
                contentContainer.innerHTML = '<div class="card empty"><p>无法加载页面：' + escapeHtml(page) + '</p></div>';
                return;
            }
            setLoading(true);
            contentContainer.innerHTML = pageHtml;
            executePageScripts(contentContainer);
            initializeDashboardPage();
            try {
                await renderPageData(page);
            } finally {
                setLoading(false);
            }
            if (addToHistory) {
                history.pushState({ page }, '', page === 'overview' ? '/admin' : '/admin/' + page);
            }
        }

        function executePageScripts(container) {
            const scripts = Array.from(container.querySelectorAll('script'));
            scripts.forEach((script) => {
                const newScript = document.createElement('script');
                Array.from(script.attributes).forEach((attr) => newScript.setAttribute(attr.name, attr.value));
                if (script.src) {
                    newScript.src = script.src;
                    newScript.async = false;
                } else {
                    newScript.textContent = script.textContent;
                }
                script.parentNode.replaceChild(newScript, script);
            });
        }

        function initializeDashboardPage() {
            if (typeof window.dashboardPageInit === 'function') {
                try {
                    window.dashboardPageInit('admin');
                } finally {
                    window.dashboardPageInit = null;
                }
            }
        }

        function fetchJson(url) {
            return Auth.fetch(url, { headers: { Accept: 'application/json' } }).then((response) => {
                if (!response.ok) throw new Error('接口请求失败');
                return response.json();
            });
        }

        function setBar(id, value) {
            const el = document.getElementById(id);
            if (el) el.style.width = Math.min(100, Number(value) || 0) + '%';
        }

        function renderPageData(page) {
            if (page !== 'overview') return window.__pageLoadPromise || Promise.resolve();

            // 「用户总数」由 overview 片段自己取（GET /admin/users 的 total）。
            // /dashboard/summary 的 stats 里没有 total_users，之前这里也写同一个元素，
            // 两个请求并发谁后返回谁生效 → 表现为「— → 2 → —」的闪烁，所以这里不再碰它。
            const ownPromise = window.__pageLoadPromise || Promise.resolve();
            const summaryPromise = fetchJson(`${window.API_BASE_URL}/dashboard/summary`).then((payload) => {
                const data = payload.data || {};
                const stats = data.stats || {};
                const system = data.system || {};
                document.getElementById('stats-total-uploads') && (document.getElementById('stats-total-uploads').textContent = stats.total_uploads ?? '—');
                document.getElementById('stats-total-nodes') && (document.getElementById('stats-total-nodes').textContent = stats.online_nodes ?? '—');
                document.getElementById('stats-accuracy') && (document.getElementById('stats-accuracy').textContent = stats.accuracy != null ? Number(stats.accuracy).toFixed(2) + '%' : '—');
                document.getElementById('system-cpu') && (document.getElementById('system-cpu').textContent = (system.cpu ?? '—') + '%');
                document.getElementById('system-memory') && (document.getElementById('system-memory').textContent = (system.memory ?? '—') + '%');
                document.getElementById('system-disk') && (document.getElementById('system-disk').textContent = (system.disk ?? '—') + '%');
                setBar('system-cpu-bar', system.cpu ?? 0);
                setBar('system-memory-bar', system.memory ?? 0);
                setBar('system-disk-bar', system.disk ?? 0);
            }).catch((e) => console.error(e));

            // 等两个请求都结束再收加载态，避免加载条提前消失/数值二次跳动
            return Promise.all([ownPromise, summaryPromise]);
        }

        function updateNavActive(page) {
            allNavLinks.forEach(link => link.classList.toggle('active', link.getAttribute('data-page') === page));
        }

        allNavLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // 只接管带 data-page 的 SPA 链接，其余（外链/无 data-page）走浏览器默认跳转
                const page = link.getAttribute('data-page');
                if (!page) return;
                e.preventDefault();
                loadPage(page, true);
            });
        });

        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) loadPage(e.state.page, false);
            else loadPage(getPageFromPath(window.location.pathname), false);
        });

        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
        else init();
    })();
</script>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>
