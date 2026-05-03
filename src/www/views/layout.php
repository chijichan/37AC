<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $title ?? ''; ?> - 37AC</title>
    <!-- <link rel="stylesheet" type="text/css" href="/static/content/bootstrap.min.css" /> -->
    <link rel="stylesheet" type="text/css" href="/static/css/pico.min.css" />
    <link rel="stylesheet" type="text/css"
        href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css" />
    <!-- <link rel="stylesheet" type="text/css" href="/static/css/site.css" /> -->
    <style>
        /* 强制显示垂直滚动条,避免不同页面宽度不一致 */
        html {
            overflow-y: scroll;
        }

        /* 覆盖 PicoCSS 的滚动条宽度设置，让滚动条正常显示 */
        :root {
            --pico-scrollbar-width: auto !important;
        }

        /* 全屏白屏遮罩层 */
        ._loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s ease-out;
            /* 遮罩层淡出动画 */
        }

        /* 加载动画容器 */
        ._loading-spinner {
            text-align: center;
        }

        /* 旋转圆圈动画 */
        ._spinner-border {
            width: 80px;
            height: 80px;
            /* animation: spin 1s linear infinite; */
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        ._loading-text {
            color: transparent;
            /* 文字透明，显示背景渐变 */
            background-image: linear-gradient(90deg,
                    #000 25%,
                    /* 黑色起始 */
                    rgba(90, 0, 127, 0.6) 40%,
                    /* 暗紫色（透明度0.6，增强层次） */
                    rgba(0, 10, 80, 0.6) 60%,
                    /* 墨蓝色（过渡色，平衡紫黑调性） */
                    #000 75%
                    /* 黑色结束 */
                );
            background-size: 400% 400%;
            /* 放大背景尺寸，为动画预留移动空间 */
            animation: gradient-flow 1.5s ease-in-out infinite;
            /* 应用循环动画 */
            -webkit-background-clip: text;
            /* 兼容WebKit内核浏览器（如Chrome、Safari） */
            background-clip: text;
            /* 背景裁剪到文字形状内 */
            font-size: 18px;
        }

        @keyframes gradient-flow {
            0% {
                background-position: -100% 0;
            }

            /* 渐变起始位置在文字左侧外（-100%） */
            100% {
                background-position: 200% 0;
            }

            /* 渐变结束位置在文字右侧外（200%） */
        }

        /* 内容容器初始状态（隐藏） */
        ._content {
            opacity: 0;
            transform: scale(0.95);
            transition: opacity 0.3s ease-in, transform 0.1s ease-in;
            /* 缓慢恢复动画 */
        }

        /* 内容显示状态 */
        ._content.show {
            opacity: 1;
            transform: scale(1);
        }
    </style>
    <link rel="icon" href="https://static.322337.xyz/view.php/3c2d0a0c603703e2a99ce22f85eb3087.ico" type="image/x-icon" />
    <script src="/static/scripts/modernizr-2.6.2.js"></script>
    <script src="/static/scripts/auth.js"></script>
</head>

<body>
    <!-- 全屏白屏遮罩层 -->
    <div id="_loading-overlay" class="_loading-overlay">
        <div class="_loading-spinner">
            <!-- 加载动画：旋转圆圈 -->
            <div class="_spinner-border">
                <img src="https://static.322337.xyz/view.php/2b41dcf3c57aabd59adb77f0c90c6eba.gif" />
            </div>
            <p class="_loading-text">页面加载中...</p>
        </div>
    </div>

    <style>
        /* PicoCSS 模态框通知样式 */
        .modal-notification {
            --pico-modal-overlay-backdrop-filter: none;
        }

        .modal-notification article {
            max-width: 420px;
            margin: 0 auto;
        }

        .modal-notification article header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .modal-notification article header .notification-icon {
            font-size: 1.5rem;
        }

        .modal-notification article header p {
            margin: 0;
            flex: 1;
        }

        .modal-notification article footer {
            display: flex;
            justify-content: flex-end;
        }

        .modal-notification.success article header p strong {
            color: var(--pico-ins-color);
        }

        .modal-notification.error article header p strong {
            color: var(--pico-del-color);
        }

        .modal-notification.info article header p strong {
            color: var(--pico-primary);
        }
    </style>

    <script>
        // 全局通知管理 - 使用 PicoCSS v2.1.1 <dialog> 模态框
        window.Notify = {
            /**
             * 显示一个通知模态框
             * @param {string} message - 通知消息
             * @param {'success'|'error'|'info'} type - 通知类型
             * @param {number} duration - 自动关闭时间（毫秒），0 表示不自动关闭
             */
            show(message, type = 'info', duration = 3000) {
                const titles = {
                    success: '操作成功',
                    error: '操作失败',
                    info: '提示'
                };

                const dialog = document.createElement('dialog');
                dialog.className = `modal-notification ${type}`;
                dialog.innerHTML = `
                    <article>
                        <header>
                            <p><strong>${titles[type]}</strong></p>
                            <button aria-label="Close" rel="prev" onclick="this.closest('dialog').close()"></button>
                        </header>
                        <p>${message}</p>
                    </article>
                `;

                document.body.appendChild(dialog);
                dialog.showModal();

                // 添加打开动画类
                document.documentElement.classList.add('modal-is-opening', 'modal-is-open');
                setTimeout(() => {
                    document.documentElement.classList.remove('modal-is-opening');
                }, 300);

                // 自动关闭
                if (duration > 0) {
                    setTimeout(() => {
                        if (dialog.open) {
                            dialog.close();
                        }
                    }, duration);
                }

                // 监听关闭事件，清理 DOM
                dialog.addEventListener('close', () => {
                    document.documentElement.classList.add('modal-is-closing');
                    setTimeout(() => {
                        document.documentElement.classList.remove('modal-is-open', 'modal-is-closing');
                        if (dialog.parentNode) {
                            dialog.parentNode.removeChild(dialog);
                        }
                    }, 300);
                });
            },

            success(message, duration = 3000) {
                this.show(message, 'success', duration);
            },

            error(message, duration = 4000) {
                this.show(message, 'error', duration);
            },

            info(message, duration = 3000) {
                this.show(message, 'info', duration);
            }
        };

        // 全局弹窗管理 - 使用 PicoCSS v2.1.1 <dialog> 模态框
        window.Modal = {
            _dialog: null,

            /**
             * 显示一个弹窗
             * @param {string} title - 弹窗标题
             * @param {string} bodyHtml - 弹窗内容 HTML
             * @param {Array<{text: string, class?: string, click: function}>} buttons - 底部按钮
             */
            show(title, bodyHtml, buttons = []) {
                // 关闭已有弹窗
                if (this._dialog && this._dialog.open) {
                    this._dialog.close();
                }

                const btnHtml = buttons.map((btn, i) => {
                    const cls = btn.class || '';
                    return `<button type="button" class="${cls}" data-modal-btn-index="${i}">${btn.text}</button>`;
                }).join('');

                const dialog = document.createElement('dialog');
                dialog.innerHTML = `
                    <article>
                        <header>
                            <button aria-label="Close" rel="prev" onclick="Modal.close()"></button>
                            <h3>${title}</h3>
                        </header>
                        <div>${bodyHtml}</div>
                        ${buttons.length ? `<footer style="display: flex; gap: 0.75rem;">${btnHtml}</footer>` : ''}
                    </article>
                `;

                document.body.appendChild(dialog);
                this._dialog = dialog;

                // 绑定按钮事件
                buttons.forEach((btn, i) => {
                    const el = dialog.querySelector(`[data-modal-btn-index="${i}"]`);
                    if (el) {
                        el.addEventListener('click', (e) => {
                            btn.click(e);
                        });
                    }
                });

                dialog.showModal();

                // 添加打开动画类
                document.documentElement.classList.add('modal-is-opening', 'modal-is-open');
                setTimeout(() => {
                    document.documentElement.classList.remove('modal-is-opening');
                }, 300);

                // 点击遮罩关闭
                dialog.addEventListener('click', (e) => {
                    if (e.target === dialog) this.close();
                });

                // 监听关闭事件，清理 DOM
                dialog.addEventListener('close', () => {
                    document.documentElement.classList.add('modal-is-closing');
                    setTimeout(() => {
                        document.documentElement.classList.remove('modal-is-open', 'modal-is-closing');
                        if (dialog.parentNode) {
                            dialog.parentNode.removeChild(dialog);
                        }
                        if (this._dialog === dialog) {
                            this._dialog = null;
                        }
                    }, 300);
                });
            },

            close() {
                if (this._dialog && this._dialog.open) {
                    this._dialog.close();
                }
            }
        };
    </script>

    <div class="container" style="transition: top 0.3s ease-in-out;">
        <nav class="container-nav">
            <ul>
                <li>
                    <a href="/"><img style="width: 100px;"
                            src="https://static.322337.xyz/view.php/2ca3f3e71b981414c517e39fd9dae033.png" /></a>
                </li>
            </ul>
            <ul>
                <li><a href="/upload">上传</a></li>
                <li><a href="/dashboard">控制台</a></li>
            </ul>
        </nav>
    </div>

    <!-- 用户信息栏（仅在 /dashboard 下显示） -->
    <div id="user-info-bar" class="container" style="display: none;">
        <div style="
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 0.5rem 1rem;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            position: relative;
        ">
            <span id="user-info-username" style="
                cursor: pointer;
                font-weight: 600;
                padding: 0.25rem 0.75rem;
                border-radius: var(--pico-border-radius);
                user-select: none;
            ">未登录</span>

            <!-- 悬浮框 -->
            <div id="user-info-dropdown" style="
                display: none;
                position: absolute;
                top: calc(100% + 0.25rem);
                right: 0;
                min-width: 200px;
                background: var(--pico-card-background-color);
                border: 1px solid var(--pico-muted-border-color);
                border-radius: var(--pico-border-radius);
                box-shadow: var(--pico-box-shadow);
                z-index: 1000;
                padding: 0.5rem 0;
            ">
                <div id="dropdown-user-info" style="
                    padding: 0.75rem 1rem;
                    border-bottom: 1px solid var(--pico-muted-border-color);
                    margin-bottom: 0.25rem;
                ">
                    <div id="dropdown-username" style="font-weight: 600; font-size: 0.95rem; color: var(--pico-color);"></div>
                    <div id="dropdown-role" style="font-size: 0.8rem; color: var(--pico-muted-color); margin-top: 0.2rem;"></div>
                </div>
                <a href="/dashboard" id="dropdown-dashboard" class="dropdown-item">控制台</a>
                <a href="/dashboard/settings" id="dropdown-settings" class="dropdown-item">账号设置</a>
                <div id="dropdown-divider" class="dropdown-divider"></div>
                <a href="/auth/login" id="dropdown-login" class="dropdown-item dropdown-item-primary">登录</a>
                <a href="#" id="dropdown-logout" class="dropdown-item dropdown-item-danger" style="display: none;">退出登录</a>
            </div>
        </div>
    </div>

    <style>
        #user-info-username:hover {
            background: var(--pico-card-sectioning-background-color);
        }

        .dropdown-item {
            display: block;
            padding: 0.625rem 1rem;
            text-decoration: none;
            color: var(--pico-color);
            font-size: 0.875rem;
            transition: background var(--pico-transition);
        }

        .dropdown-item:hover {
            background: var(--pico-card-sectioning-background-color);
            color: var(--pico-color);
        }

        .dropdown-item-primary {
            color: var(--pico-primary);
        }

        .dropdown-item-primary:hover {
            color: var(--pico-primary-hover);
        }

        .dropdown-item-danger {
            color: var(--pico-del-color);
        }

        .dropdown-item-danger:hover {
            color: var(--pico-del-color);
        }

        .dropdown-divider {
            height: 1px;
            background: var(--pico-muted-border-color);
        }
    </style>

    <script>
        // 用户信息栏逻辑
        document.addEventListener('DOMContentLoaded', function() {
            const userInfoBar = document.getElementById('user-info-bar');
            const usernameEl = document.getElementById('user-info-username');
            const dropdown = document.getElementById('user-info-dropdown');
            const dropdownUsername = document.getElementById('dropdown-username');
            const dropdownRole = document.getElementById('dropdown-role');
            const dropdownLogin = document.getElementById('dropdown-login');
            const dropdownLogout = document.getElementById('dropdown-logout');
            const dropdownDashboard = document.getElementById('dropdown-dashboard');
            const dropdownSettings = document.getElementById('dropdown-settings');
            const dropdownDivider = document.getElementById('dropdown-divider');

            // 只在 /dashboard 路径下显示
            if (window.location.pathname.startsWith('/dashboard')) {
                userInfoBar.style.display = '';

                const user = Auth.getUser();
                const token = Auth.getToken();

                if (token && user) {
                    usernameEl.textContent = user.username;
                    dropdownUsername.textContent = user.username;
                    dropdownRole.textContent = user.role === 'admin' ? '管理员' : '普通用户';
                    dropdownLogin.style.display = 'none';
                    dropdownLogout.style.display = '';
                    dropdownDashboard.style.display = '';
                    dropdownSettings.style.display = '';
                    dropdownDivider.style.display = '';
                } else {
                    usernameEl.textContent = '未登录';
                    dropdownUsername.textContent = '未登录';
                    dropdownRole.textContent = '访客';
                    dropdownLogin.style.display = '';
                    dropdownLogout.style.display = 'none';
                    dropdownDashboard.style.display = 'none';
                    dropdownSettings.style.display = 'none';
                    dropdownDivider.style.display = 'none';
                }
            }

            // 点击用户名切换悬浮框
            usernameEl.addEventListener('click', function(e) {
                e.stopPropagation();
                dropdown.style.display = dropdown.style.display === 'none' ? '' : 'none';
            });

            // 点击悬浮框内部不关闭
            dropdown.addEventListener('click', function(e) {
                e.stopPropagation();
            });

            // 点击页面其他地方关闭悬浮框
            document.addEventListener('click', function() {
                dropdown.style.display = 'none';
            });

            // 退出登录（使用 Auth 模块）
            dropdownLogout.addEventListener('click', function(e) {
                e.preventDefault();
                Auth.logout();
            });
        });
    </script>

    <div id="_content" class="_content">
</body>

</html>