<?php

/**
 * 入口文件
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

define('ROOT_PATH', dirname(__DIR__));

require_once ROOT_PATH . '/router.php';
require_once ROOT_PATH . '/config/config.php';
require_once ROOT_PATH . '/controllers/controller.php';

spl_autoload_register(function ($class) {
    $file = ROOT_PATH . '/controllers/' . $class . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

// 路由
$router = new Router();

// 注册路由
$router->get('/', 'home_controller@index');
$router->get('/about', 'home_controller@about');
$router->get('/contact', 'home_controller@contact');
$router->get('/upload', 'home_controller@upload');

// 仪表盘路由
$router->get('/dashboard', 'dashboard_controller@index');
$router->get('/dashboard/nodes', 'dashboard_controller@nodes');
$router->get('/dashboard/apikeys', 'dashboard_controller@apikeys');
$router->get('/dashboard/history', 'dashboard_controller@history');
$router->get('/dashboard/settings', 'dashboard_controller@settings');

// 用户路由
// $router->get('/users', 'user_controller@index');
// $router->get('/user/{id}', 'user_controller@show');
// $router->post('/user/create', 'user_controller@create');

// 执行路由分发
$router->dispatch();

// switch ($_SERVER['REQUEST_URI']) {
//     case '/':
//     case '/home':
//         $title = '首页';
//         require '../views/index.php';
//         break;
//     case '/upload':
//         $title = '上传图片';
//         require '../views/upload.php';
//         break;
//     case '/contact':
//         $title = '联系我们';
//         require '../views/contact.php';
//         break;
//     case '/about':
//         $title = '关于我们';
//         require '../views/about.php';
//         break;
//     default:
//         http_response_code(404);
//         break;
// }