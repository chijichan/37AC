<?php

/**
 * 认证控制器
 */

class Auth_Controller extends Controller
{
    // 登录页面
    public function login()
    {
        $data = [
            'title' => '登录',
            'description' => '登录 37AC 账户，继续使用角色识别与个人中心功能。',
            'keywords' => '37AC登录,账号登录,角色识别登录',
            'canonical_url' => '/auth/login'
        ];

        $this->view('auth/login', $data);
    }

    // 注册页面
    public function register()
    {
        $data = [
            'title' => '注册',
            'description' => '注册 37AC 账户，开启动漫角色识别与个人收藏管理。',
            'keywords' => '37AC注册,创建账号,动漫识别注册',
            'canonical_url' => '/auth/register'
        ];

        $this->view('auth/register', $data);
    }

    // 忘记密码页面
    public function forgot_password()
    {
        $data = [
            'title' => '忘记密码',
            'description' => '通过邮件找回 37AC 账户密码，恢复登录权限。',
            'keywords' => '37AC忘记密码,找回密码,重置密码',
            'canonical_url' => '/auth/forgot-password',
            'api_base_url' => API_BASE_URL
        ];

        $this->view('auth/forgot_password', $data);
    }

    // 退出登录：销毁服务端 Session（含 PHPSESSID），防止登出后仍可访问受保护页面
    public function logout()
    {
        session_start();
        $_SESSION = [];
        if (ini_get('session.use_cookies')) {
            $params = session_get_cookie_params();
            setcookie(
                session_name(),
                '',
                time() - 42000,
                $params['path'],
                $params['domain'],
                $params['secure'],
                $params['httponly']
            );
        }
        session_destroy();

        // 清除业务 Cookie
        setcookie('access_token', '', time() - 42000, '/');
        setcookie('user_id', '', time() - 42000, '/');
        setcookie('username', '', time() - 42000, '/');
        setcookie('role', '', time() - 42000, '/');

        header('Location: /auth/login');
        exit;
    }

    // 重置密码页面
    public function reset_password()
    {

        // 从 URL 参数中获取 token
        $token = isset($_GET['token']) ? trim($_GET['token']) : '';

        $data = [
            'title' => '重置密码',
            'description' => '设置新的 37AC 账户密码，安全恢复登录。',
            'keywords' => '37AC重置密码,设置新密码',
            // canonical 不带 token，避免凭证进入 SEO 元数据
            'canonical_url' => '/auth/reset-password',
            'token' => $token,
            'api_base_url' => API_BASE_URL
        ];

        $this->view('auth/reset_password', $data);
    }
}
