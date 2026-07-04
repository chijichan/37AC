/**
 * 37AC 前端认证模块
 * 提供统一的 token 管理、请求拦截、API 调用封装
 */

const AUTH_CONFIG = {
    TOKEN_REFRESH_MARGIN: 300, // token 过期前5分钟刷新
};

// 确保全局 API 基础 URL 已定义（由 layout.php 注入）
if (!window.API_BASE_URL) {
    window.API_BASE_URL = 'http://127.0.0.1:13138'; // 降级默认值
}

const Auth = {
    /**
     * 获取存储的 token
     */
    getToken() {
        return localStorage.getItem('access_token');
    },

    /**
     * 获取刷新 token
     */
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    /**
     * 获取当前用户信息
     */
    getUser() {
        const username = localStorage.getItem('username');
        const role = localStorage.getItem('role');
        const userId = localStorage.getItem('user_id');
        if (!username) return null;
        return { username, role, user_id: userId };
    },

    /**
     * 检查是否已登录
     */
    isLoggedIn() {
        return !!this.getToken();
    },

    /**
     * 检查是否为管理员
     */
    isAdmin() {
        return localStorage.getItem('role') === 'admin';
    },

    /**
     * 保存登录信息
     */
    setSession(data) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('username', data.username);
        localStorage.setItem('role', data.role);
    },

    /**
     * 清除登录信息
     */
    clearSession() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
    },

    /**
     * 刷新访问令牌
     */
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) return false;

        try {
            const response = await fetch(`${window.API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            const result = await response.json();
            if (result.success) {
                localStorage.setItem('access_token', result.data.access_token);
                return true;
            }
            return false;
        } catch (e) {
            console.error('Token refresh failed:', e);
            return false;
        }
    },

    /**
     * 带认证的 fetch 请求
     */
    async fetch(url, options = {}) {
        const token = this.getToken();
        const headers = options.headers || {};

        // 添加 Authorization 头
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // 自动设置 Content-Type
        if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        const config = { ...options, headers };

        try {
            const response = await fetch(url, config);

            // 401 未授权，尝试刷新 token
            if (response.status === 401 && token) {
                const refreshed = await this.refreshAccessToken();
                if (refreshed) {
                    // 重试请求
                    headers['Authorization'] = `Bearer ${this.getToken()}`;
                    const retryResponse = await fetch(url, { ...options, headers });
                    return retryResponse;
                } else {
                    // 刷新失败，跳转到登录页
                    this.clearSession();
                    // 不在 /auth/ 页面才跳转，避免死循环
                    if (!window.location.pathname.startsWith('/auth/')) {
                        window.location.href = '/auth/login';
                    }
                    return response;
                }
            }

            return response;
        } catch (e) {
            console.error('Auth fetch error:', e);
            throw e;
        }
    },

    /**
     * 便捷的 GET 请求
     */
    async get(url) {
        const response = await this.fetch(url);
        return response.json();
    },

    /**
     * 便捷的 POST 请求
     */
    async post(url, data) {
        const response = await this.fetch(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    /**
     * 便捷的 PUT 请求
     */
    async put(url, data) {
        const response = await this.fetch(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    /**
     * 便捷的 DELETE 请求
     */
    async del(url) {
        const response = await this.fetch(url, { method: 'DELETE' });
        return response.json();
    },

    /**
     * 登出
     */
    logout() {
        this.clearSession();
        // 清除 Cookie
        document.cookie = 'access_token=; path=/; max-age=0';
        document.cookie = 'user_id=; path=/; max-age=0';
        document.cookie = 'username=; path=/; max-age=0';
        document.cookie = 'role=; path=/; max-age=0';
        window.location.href = '/auth/login';
    }
};

// 自动刷新 token 检查（每60秒检查一次）
setInterval(async () => {
    const token = Auth.getToken();
    if (!token) return;

    try {
        // 解析 JWT 获取过期时间
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000;
        const now = Date.now();
        const margin = AUTH_CONFIG.TOKEN_REFRESH_MARGIN * 1000;

        if (exp - now < margin) {
            await Auth.refreshAccessToken();
        }
    } catch (e) {
        // 静默失败
    }
}, 60000);
