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
        font-size: 1.2em;
        margin-right: 0.5rem;
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

<div style="
    display: flex;
    color: #ffffff;
    background: orange;
    justify-content: center;
">Demo
</div>

<!-- 仪表盘二级导航 -->
<div class="dashboard-subnav container">
    <div class="container">
        <!-- 桌面端导航 -->
        <nav class="dashboard-nav-desktop">
            <a href="/dashboard" data-page="overview" class="dashboard-nav-link active">
                <img src="https://static.322337.xyz/assets/img/overview.svg" alt="总览" class="icon" />总览
            </a>
            <a href="/dashboard/nodes" data-page="nodes" class="dashboard-nav-link">
                <img src="https://static.322337.xyz/assets/img/nodes.svg" alt="节点管理" class="icon" />节点管理
            </a>
            <a href="/dashboard/apikeys" data-page="apikeys" class="dashboard-nav-link">
                <img src="https://static.322337.xyz/assets/img/apikeys.svg" alt="API密钥" class="icon" />API密钥
            </a>
            <a href="/dashboard/history" data-page="history" class="dashboard-nav-link">
                <img src="https://static.322337.xyz/assets/img/history.svg" alt="使用记录" class="icon" />使用记录
            </a>
            <a href="/dashboard/settings" data-page="settings" class="dashboard-nav-link">
                <img src="https://static.322337.xyz/assets/img/settings.svg" alt="设置" class="icon" />设置
            </a>
        </nav>

        <!-- 移动端下拉导航 -->
        <div class="dashboard-nav-mobile">
            <button class="dashboard-nav-toggle" id="dashboardNavToggle" type="button">
                <span>
                    <span class="icon" id="currentNavIcon">
                        <img src="https://static.322337.xyz/assets/img/overview.svg" alt="总览" class="icon" />
                    </span>
                    <span id="currentNavText">总览</span>
                </span>
                <span class="arrow">▼</span>
            </button>
            <div class="dashboard-nav-dropdown" id="dashboardNavDropdown">
                <a href="/dashboard" data-page="overview" class="dashboard-nav-link-mobile active">
                    <img src="https://static.322337.xyz/assets/img/overview.svg" alt="总览" class="icon" />总览
                </a>
                <a href="/dashboard/nodes" data-page="nodes" class="dashboard-nav-link-mobile">
                    <img src="https://static.322337.xyz/assets/img/nodes.svg" alt="节点管理" class="icon" />节点管理
                </a>
                <a href="/dashboard/apikeys" data-page="apikeys" class="dashboard-nav-link-mobile">
                    <img src="https://static.322337.xyz/assets/img/apikeys.svg" alt="API密钥" class="icon" />API密钥
                </a>
                <a href="/dashboard/history" data-page="history" class="dashboard-nav-link-mobile">
                    <img src="https://static.322337.xyz/assets/img/history.svg" alt="使用记录" class="icon" />使用记录
                </a>
                <a href="/dashboard/settings" data-page="settings" class="dashboard-nav-link-mobile">
                    <img src="https://static.322337.xyz/assets/img/settings.svg" alt="设置" class="icon" />设置
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

        // 页面缓存
        const pageCache = {};

        // 页面信息映射
        const pageInfo = {
            'overview': {
                icon: '<img src="https://static.322337.xyz/assets/img/overview.svg" alt="总览" class="icon" />',
                text: '总览'
            },
            'nodes': {
                icon: '<img src="https://static.322337.xyz/assets/img/nodes.svg" alt="节点管理" class="icon" />',
                text: '节点管理'
            },
            'apikeys': {
                icon: '<img src="https://static.322337.xyz/assets/img/apikeys.svg" alt="API密钥" class="icon" />',
                text: 'API密钥'
            },
            'history': {
                icon: '<img src="https://static.322337.xyz/assets/img/history.svg" alt="使用记录" class="icon" />',
                text: '使用记录'
            },
            'settings': {
                icon: '<img src="https://static.322337.xyz/assets/img/settings.svg" alt="设置" class="icon" />',
                text: '设置'
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
        function loadPage(page, addToHistory = true) {
            // 防止重复加载
            if (page === currentPage && pageCache[page]) {
                return;
            }

            // 更新导航激活状态
            updateNavActive(page);

            // 更新移动端下拉按钮显示
            updateMobileNav(page);

            // 关闭移动端下拉菜单
            navDropdown.classList.remove('show');
            navToggle.classList.remove('open');

            // 如果断网且有缓存，直接使用
            if (!navigator.onLine && pageCache[page]) {
                contentContainer.innerHTML = pageCache[page];
                currentPage = page;
                return;
            }

            // 开始加载：启用 aria-busy 并加淡内容
            loadingIndicator.setAttribute('aria-busy', 'true');
            contentContainer.style.opacity = '0.5';

            // 构建请求URL
            const url = page === 'overview' ? '/dashboard?ajax=1' : `/dashboard/${page}?ajax=1`;

            // 发起 AJAX 请求
            fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('页面加载失败');
                    }
                    return response.text();
                })
                .then(html => {
                    // 缓存内容
                    pageCache[page] = html;

                    // 更新内容
                    contentContainer.innerHTML = html;
                    currentPage = page;

                    // 更新浏览器历史
                    if (addToHistory) {
                        const url = page === 'overview' ? '/dashboard' : `/dashboard/${page}`;
                        history.pushState({
                            page
                        }, '', url);
                    }
                })
                .catch(error => {
                    contentContainer.innerHTML = `
                        <article style="text-align: center; padding: 3rem;">
                            <h2>⚠️ 加载失败</h2>
                            <p>${error.message}</p>
                            <button onclick="location.reload()">刷新页面</button>
                        </article>
                    `;
                })
                .finally(() => {
                    // 结束加载：移除 aria-busy
                    loadingIndicator.setAttribute('aria-busy', 'false');
                    contentContainer.style.opacity = '1';
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