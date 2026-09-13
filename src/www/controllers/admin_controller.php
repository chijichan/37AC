<?php

/**
 * 后台管理控制器（仅管理员）
 *
 * /admin 及其子路由共用同一个 SPA 壳，页面切换由前端 JS 完成。
 */
class Admin_Controller extends Controller
{
    public function index()
    {
        $data = [
            'title' => '后台管理',
            'description' => '37AC 后台管理系统：用户、节点、任务、模型与系统设置。',
            'keywords' => '37AC后台管理,admin',
            'canonical_url' => '/admin',
            'robots' => 'noindex,nofollow',
        ];

        $this->view('admin/layout', $data);
    }
}
