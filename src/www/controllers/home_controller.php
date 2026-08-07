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
            'title' => '欢迎来到二次元角色识别小屋',
            'description' => '37AC 是一款面向二次元爱好者的 AI 角色识别平台，支持上传图片快速识别动漫与游戏角色。',
            'keywords' => '37AC,动漫角色识别,二次元识别,AI识别,角色识别',
            'canonical_url' => '/'
        ];

        $this->view('home/index', $data);
    }

    // 关于我们
    public function about()
    {
        $data = [
            'title' => '关于我们',
            'description' => '了解 37AC 的定位、识别能力与服务目标，帮助你更好地使用角色识别功能。',
            'keywords' => '关于37AC,动漫角色识别介绍,AI识别平台',
            'canonical_url' => '/about'
        ];

        $this->view('home/about', $data);
    }

    // 联系我们
    public function contact()
    {
        $data = [
            'title' => '联系我们',
            'description' => '通过页面联系方式与 37AC 团队取得联系，获取更多关于角色识别服务的信息。',
            'keywords' => '联系37AC,客服,技术支持',
            'canonical_url' => '/contact'
        ];

        $this->view('home/contact', $data);
    }

    // 上传图片
    public function upload()
    {
        $data = [
            'title' => '上传图片识别',
            'description' => '上传动漫或游戏角色图片，体验 37AC 的 AI 角色识别服务。',
            'keywords' => '上传图片,动漫识别,角色识别,AI识别',
            'canonical_url' => '/upload'
        ];

        $this->view('home/upload', $data);
    }
}
