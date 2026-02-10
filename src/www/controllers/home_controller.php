<?php
/**
 * 首页控制器
 */

class Home_Controller extends Controller
{
    // 首页
    public function index()
    {
        $data = [
            'title' => '首页'
        ];
        
        $this->view('home/index', $data);
    }

    // 关于我们
    public function about()
    {
        $data = [
            'title' => '关于我们'
        ];
        
        $this->view('home/about', $data);
    }

    // 联系我们
    public function contact()
    {
        $data = [
            'title' => '联系我们'
        ];
        
        $this->view('home/contact', $data);
    }

    // 上传图片
    public function upload()
    {
        $data = [
            'title' => '上传图片'
        ];        
        
        $this->view('home/upload', $data);
    }
}
