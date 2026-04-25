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
            'title' => '登录'
        ];

        $this->view('auth/login', $data);
    }

    // 注册页面
    public function register()
    {
        $data = [
            'title' => '注册'
        ];

        $this->view('auth/register', $data);
    }

    // 忘记密码页面
    public function forgot_password()
    {
        $data = [
            'title' => '忘记密码'
        ];

        $this->view('auth/forgot_password', $data);
    }
}
