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
    function initUserMenu() {
        const menu = document.getElementById('user-menu');
        const trigger = document.getElementById('user-trigger');
        if (!menu || !trigger) return;

        const triggerName = document.getElementById('user-trigger-name');
        const udName = document.getElementById('ud-name');
        const udRole = document.getElementById('ud-role');
        const logoutBtn = document.getElementById('ud-logout');

        const user = window.Auth ? Auth.getUser() : null;
        const loggedIn = !!(window.Auth && Auth.getToken() && user);

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
        /**
         * @param {string} message 通知文本（按纯文本渲染，防 XSS）
         * @param {'success'|'error'|'info'} type
         * @param {number} duration 自动关闭毫秒数，0 表示常驻
         */
        show(message, type = 'info', duration = 3000) {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.setAttribute('role', 'status');
            toast.textContent = message; // textContent 渲染，天然防 XSS
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
        info(message, duration = 3000) { this.show(message, 'info', duration); },
    };

    /* ---------- Modal（确认弹窗） ---------- */
    window.Modal = {
        _dialog: null,

        /**
         * @param {string} title 标题（纯文本）
         * @param {string} bodyHtml 内容 HTML（调用方负责转义动态数据）
         * @param {Array<{text: string, class?: string, click: function}>} buttons
         */
        show(title, bodyHtml, buttons = []) {
            this.close();

            const dialog = document.createElement('dialog');
            dialog.className = 'ac-modal';

            const titleEl = document.createElement('div');
            titleEl.className = 'modal-title';
            titleEl.textContent = title;

            const bodyEl = document.createElement('div');
            bodyEl.className = 'modal-body';
            bodyEl.innerHTML = bodyHtml;

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
            this._dialog = dialog;
            dialog.showModal();

            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) this.close();
            });
            dialog.addEventListener('close', () => {
                dialog.remove();
                if (this._dialog === dialog) this._dialog = null;
            });
        },

        close() {
            if (this._dialog && this._dialog.open) this._dialog.close();
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
