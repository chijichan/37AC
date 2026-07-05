<?php

/**
 * 仪表盘控制器
 */

class Dashboard_Controller extends Controller
{
    public function index()
    {
        $data = [
            'title' => '仪表盘',
            'description' => '查看 37AC 的使用概况、识别记录和账户状态。',
            'keywords' => '37AC仪表盘,识别记录,个人中心',
            'canonical_url' => '/dashboard'
        ];

        $this->view('dashboard/index', $data);
    }

    public function nodes()
    {
        $data = [
            'title' => '节点管理',
            'description' => '管理 37AC 的节点状态与服务接入信息。',
            'keywords' => '37AC节点管理,服务节点,API节点',
            'canonical_url' => '/dashboard/nodes'
        ];

        $this->view('dashboard/nodes', $data);
    }

    public function apikeys()
    {
        $data = [
            'title' => 'API密钥',
            'description' => '查看和管理 37AC 的 API 密钥，便于接入识别服务。',
            'keywords' => '37AC API密钥,密钥管理,接口访问',
            'canonical_url' => '/dashboard/apikeys'
        ];

        $this->view('dashboard/apikeys', $data);
    }

    public function history()
    {
        $data = [
            'title' => '使用记录',
            'description' => '查看 37AC 的识别历史记录与操作日志。',
            'keywords' => '37AC使用记录,识别历史,操作日志',
            'canonical_url' => '/dashboard/history'
        ];

        $this->view('dashboard/history', $data);
    }

    public function settings()
    {
        $data = [
            'title' => '设置',
            'description' => '配置 37AC 账户设置、通知和偏好选项。',
            'keywords' => '37AC设置,个人设置,偏好配置',
            'canonical_url' => '/dashboard/settings'
        ];

        $this->view('dashboard/settings', $data);
    }
}
