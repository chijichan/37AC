/**
 * 37AC 全局前端模块
 * 加载遮罩、导航、用户菜单、Notify(toast)、Modal(确认框)、reveal 动效、HTML 转义
 * 依赖：auth.js（Auth 模块）
 */

(function () {
    'use strict';

    /* ---------- HTML 转义（所有渲染 API 返回文本前必须使用） ---------- */
    window.escapeHtml = function (value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    /* ---------- 加载遮罩 ---------- */
    function hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) return;
        overlay.classList.add('done');
        overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
        // 兜底：某些情况下 transitionend 不触发
        setTimeout(() => overlay.parentNode && overlay.remove(), 800);
    }

    if (document.readyState === 'complete') {
        hideLoadingOverlay();
    } else {
        window.addEventListener('load', hideLoadingOverlay);
        // 兜底：资源加载卡住时 3s 后也关闭
        setTimeout(hideLoadingOverlay, 3000);
    }

    /* ---------- 导航高亮 ---------- */
    function initNavHighlight() {
        const path = window.location.pathname;
        document.querySelectorAll('.nav-links a[data-nav]').forEach((a) => {
            const prefix = a.getAttribute('data-nav');
            if (path === prefix || (prefix !== '/' && path.startsWith(prefix))) {
                a.classList.add('active');
            }
        });
    }

    /* ---------- 用户菜单 ---------- */
    async function initUserMenu() {
        const menu = document.getElementById('user-menu');
        const trigger = document.getElementById('user-trigger');
        if (!menu || !trigger) return;

        const triggerName = document.getElementById('user-trigger-name');
        const udName = document.getElementById('ud-name');
        const udRole = document.getElementById('ud-role');
        const logoutBtn = document.getElementById('ud-logout');

        // 登录态以「能用的令牌」为准：令牌过期且刷新失败时按未登录渲染。
        // 只看 localStorage 里有没有 token 会导致会话失效后头部仍显示用户信息。
        const loggedIn = window.Auth ? await Auth.ensureValidSession() : false;
        const user = loggedIn && window.Auth ? Auth.getUser() : null;

        if (loggedIn) {
            triggerName.textContent = user.username;
            udName.textContent = user.username;
            udRole.textContent = user.role === 'admin' ? '管理员' : '普通用户';
        } else {
            triggerName.textContent = '未登录';
            udName.textContent = '未登录';
            udRole.textContent = '访客';
        }

        // 按登录状态切换菜单项可见性
        menu.querySelectorAll('[data-auth]').forEach((el) => {
            const need = el.getAttribute('data-auth');
            el.style.display = (need === 'user') === loggedIn ? '' : 'none';
        });

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const open = menu.classList.toggle('open');
            trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        menu.addEventListener('click', (e) => e.stopPropagation());
        document.addEventListener('click', () => {
            menu.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
        });

        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => Auth.logout());
        }
    }

    /* ---------- Notify（toast 通知） ---------- */
    let toastStack = null;
    function getToastStack() {
        if (!toastStack) {
            toastStack = document.createElement('div');
            toastStack.className = 'toast-stack';
            document.body.appendChild(toastStack);
        }
        return toastStack;
    }

    window.Notify = {
        // 语义由图标承载，不靠整块染色或色条
        _icons: {
            success: 'ph-check-circle',
            error: 'ph-warning-circle',
            warning: 'ph-warning-circle',
            info: 'ph-info',
        },

        /**
         * @param {string} message 通知文本（按纯文本渲染，防 XSS）
         * @param {'success'|'error'|'warning'|'info'} type
         * @param {number} duration 自动关闭毫秒数，0 表示常驻
         */
        show(message, type = 'info', duration = 3000) {
            const kind = this._icons[type] ? type : 'info';

            const toast = document.createElement('div');
            toast.className = `toast ${kind}`;
            // 错误需要立刻被读屏播报；普通提示用 status 排队播报即可
            toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');

            const icon = document.createElement('i');
            icon.className = `ph ${this._icons[kind]} toast-icon`;
            icon.setAttribute('aria-hidden', 'true');

            const text = document.createElement('span');
            text.className = 'toast-text';
            text.textContent = message; // textContent 渲染，天然防 XSS

            toast.appendChild(icon);
            toast.appendChild(text);
            getToastStack().appendChild(toast);

            const dismiss = () => {
                if (!toast.parentNode) return;
                toast.classList.add('leaving');
                toast.addEventListener('animationend', () => toast.remove(), { once: true });
            };

            toast.addEventListener('click', dismiss);
            if (duration > 0) setTimeout(dismiss, duration);
        },
        success(message, duration = 3000) { this.show(message, 'success', duration); },
        error(message, duration = 4000) { this.show(message, 'error', duration); },
        warning(message, duration = 4000) { this.show(message, 'warning', duration); },
        info(message, duration = 3000) { this.show(message, 'info', duration); },

        /**
         * 统一错误提示：用户只看人话，技术细节留在控制台。
         * 只有显式标记 err.userFacing 的文案才会原样展示，
         * 避免把 "Failed to fetch"、HTTP 状态码、curl 错误码这类内容丢给用户。
         */
        errorFrom(err, fallback) {
            console.warn('[error]', err);
            if (err && err.userFacing && err.message) {
                this.error(err.message);
                return;
            }
            this.error(fallback || '操作失败，请稍后重试');
        },
    };

    /* ---------- Btn（按钮 Loading 态：转圈 + 锁点击防重复提交） ---------- */
    window.Btn = {
        /**
         * 切换按钮加载态。加载期间按钮被禁用，避免重复提交。
         * @param {HTMLElement|null} btn
         * @param {boolean} [on=true]
         */
        loading(btn, on = true) {
            if (!btn) return;
            btn.classList.toggle('is-loading', on);
            btn.disabled = on;
            btn.setAttribute('aria-busy', on ? 'true' : 'false');
        },
    };

    /* ---------- Modal（弹窗 / 抽屉 / 确认框） ---------- */
    let activeDialog = null;

    /**
     * 判断点击是否落在遮罩上。
     * 只比较坐标而不比较 e.target：弹窗自身的内边距区域 e.target 也等于 dialog，
     * 仅凭 e.target 判断会导致「点在弹窗留白处就把弹窗关掉」。
     */
    function isBackdropClick(dialog, e) {
        const r = dialog.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right ||
            e.clientY < r.top || e.clientY > r.bottom;
    }

    /**
     * @param {{title: string, bodyHtml: string, buttons?: Array,
     *          kind?: 'modal'|'drawer', dismissible?: boolean}} opts
     */
    function openDialog(opts) {
        closeDialog();

        const kind = opts.kind === 'drawer' ? 'drawer' : 'modal';
        const buttons = opts.buttons || [];

        const dialog = document.createElement('dialog');
        // 抽屉复用弹窗的内部结构样式，仅追加布局修饰类
        dialog.className = kind === 'drawer' ? 'ac-modal ac-drawer' : 'ac-modal';

        const titleEl = document.createElement('div');
        titleEl.className = 'modal-title';
        titleEl.textContent = opts.title;

        const bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.innerHTML = opts.bodyHtml;

        dialog.appendChild(titleEl);
        dialog.appendChild(bodyEl);

        if (buttons.length) {
            const actions = document.createElement('div');
            actions.className = 'modal-actions';
            buttons.forEach((btn) => {
                const el = document.createElement('button');
                el.type = 'button';
                el.className = btn.class || 'btn btn-ghost btn-sm';
                el.textContent = btn.text;
                el.addEventListener('click', (e) => btn.click(e));
                actions.appendChild(el);
            });
            dialog.appendChild(actions);
        }

        document.body.appendChild(dialog);

        // 含表单控件的弹窗一律禁止遮罩 / Esc 关闭，防止录入内容丢失。
        // 这是结构性保证：不依赖调用方是否记得传 dismissible。
        const hasFields = !!dialog.querySelector('input, select, textarea');
        const dismissible = opts.dismissible === true && !hasFields;

        dialog.addEventListener('click', (e) => {
            if (dismissible && isBackdropClick(dialog, e)) closeDialog();
        });

        // 原生 Esc 会触发 cancel 事件并直接关闭，必须显式拦截
        dialog.addEventListener('cancel', (e) => {
            if (dismissible) return;
            e.preventDefault();
            if (hasFields) Notify.info('该弹窗需点击下方按钮关闭，已填写的内容不会丢失');
        });

        dialog.addEventListener('close', () => {
            dialog.remove();
            if (activeDialog === dialog) activeDialog = null;
        });

        activeDialog = dialog;
        dialog.showModal();
        return dialog;
    }

    function closeDialog() {
        if (activeDialog && activeDialog.open) activeDialog.close();
    }

    window.Modal = {
        /**
         * 通用弹窗。默认只能通过按钮关闭。
         * @param {string} title 标题（纯文本）
         * @param {string} bodyHtml 内容 HTML（调用方负责转义动态数据）
         * @param {Array<{text: string, class?: string, click: function}>} [buttons]
         * @param {{dismissible?: boolean}} [opts] dismissible：是否允许点遮罩 / Esc 关闭
         */
        show(title, bodyHtml, buttons = [], opts = {}) {
            return openDialog(Object.assign({ title, bodyHtml, buttons, kind: 'modal' }, opts));
        },

        /**
         * 侧边抽屉：查看详情时保留列表背景上下文，不阻断整页操作。
         */
        drawer(title, bodyHtml, buttons = [], opts = {}) {
            return openDialog(Object.assign(
                { title, bodyHtml, buttons, kind: 'drawer', dismissible: true }, opts
            ));
        },

        /**
         * 确认框：删除等不可逆操作的统一入口，避免各处手搓一遍。
         * @param {{title?: string, description?: string, confirmText?: string,
         *          cancelText?: string, danger?: boolean, onConfirm?: function}} opts
         */
        confirm(opts = {}) {
            const danger = opts.danger === true;
            return openDialog({
                title: opts.title || '确认操作',
                bodyHtml: opts.description || '',
                kind: 'modal',
                dismissible: true,
                buttons: [{
                    text: opts.cancelText || '取消',
                    class: 'btn btn-ghost btn-sm',
                    click: () => closeDialog(),
                }, {
                    text: opts.confirmText || '确认',
                    class: danger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm',
                    click: (e) => {
                        closeDialog();
                        if (typeof opts.onConfirm === 'function') opts.onConfirm(e);
                    },
                }],
            });
        },

        close() {
            closeDialog();
        },
    };

    /* ---------- reveal 进入视口动效 ---------- */
    function initReveal() {
        const els = document.querySelectorAll('.reveal');
        if (!els.length) return;

        if (!('IntersectionObserver' in window) ||
            window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            els.forEach((el) => el.classList.add('is-in'));
            return;
        }

        const io = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-in');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });

        els.forEach((el) => io.observe(el));
    }

    /* ---------- 启动 ---------- */
    function init() {
        initNavHighlight();
        initUserMenu();
        initReveal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
