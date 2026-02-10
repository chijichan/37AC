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
            'description' => '仪表盘主页',
        ];
        
        $this->view('dashboard/index', $data);
    }

    public function nodes()
    {
        $data = [
            'title' => '节点管理',
        ];
        
        $this->view('dashboard/nodes', $data);
    }

    public function apikeys()
    {
        $data = [
            'title' => 'API密钥',
        ];
        
        $this->view('dashboard/apikeys', $data);
    }

    public function history()
    {
        $data = [
            'title' => '使用记录',
        ];
        
        $this->view('dashboard/history', $data);
    }

    public function settings()
    {
        $data = [
            'title' => '设置',
        ];
        
        $this->view('dashboard/settings', $data);
    }
}
?>