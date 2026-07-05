<?php

/**
 * 入口文件
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

define('ROOT_PATH', dirname(__DIR__));

// 加载 .env 环境变量文件
$envFile = ROOT_PATH . '/.env';
if (file_exists($envFile)) {
    $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        // 跳过注释行
        if (strpos($line, '#') === 0) {
            continue;
        }
        if (strpos($line, '=') !== false) {
            list($key, $value) = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value);
            if (!empty($key)) {
                if (function_exists('putenv')) {
                    putenv("$key=$value");
                }
                $_ENV[$key] = $value;
                $_SERVER[$key] = $value;
            }
        }
    }
}

require_once ROOT_PATH . '/router.php';
require_once ROOT_PATH . '/controllers/controller.php';

// 后端 API 基础 URL（从环境变量读取，优先从 .env 加载）
$apiBaseUrl = getenv('API_BASE_URL');
if (empty($apiBaseUrl) && isset($_ENV['API_BASE_URL'])) {
    $apiBaseUrl = $_ENV['API_BASE_URL'];
}
if (empty($apiBaseUrl) && isset($_SERVER['API_BASE_URL'])) {
    $apiBaseUrl = $_SERVER['API_BASE_URL'];
}
define('API_BASE_URL', $apiBaseUrl ?: 'http://127.0.0.1:13138');

spl_autoload_register(function ($class) {
    $file = ROOT_PATH . '/controllers/' . $class . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

/**
 * 认证检查中间件
 * 检查用户是否已登录，未登录则重定向到登录页
 */
function require_auth()
{
    // 从 Cookie 或 Session 中检查登录状态
    session_start();
    $is_logged_in = isset($_SESSION['user_id']) ||
        (isset($_COOKIE['access_token']) && !empty($_COOKIE['access_token']));

    if (!$is_logged_in) {
        // 检查 Authorization header（用于 AJAX 请求）
        $auth_header = isset($_SERVER['HTTP_AUTHORIZATION']) ? $_SERVER['HTTP_AUTHORIZATION'] : '';
        if (empty($auth_header)) {
            // 也检查 REDIRECT_HTTP_AUTHORIZATION
            $auth_header = isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION']) ? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] : '';
        }

        if (!empty($auth_header) && preg_match('/Bearer\s+(.+)/', $auth_header, $matches)) {
            $is_logged_in = !empty($matches[1]);
        }
    }

    if (!$is_logged_in) {
        // AJAX 请求返回 401
        if (
            !empty($_SERVER['HTTP_X_REQUESTED_WITH']) &&
            strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) == 'xmlhttprequest'
        ) {
            http_response_code(401);
            header('Content-Type: application/json');
            echo json_encode(['success' => false, 'message' => '未登录，请先登录']);
            exit;
        }

        // 普通请求重定向到登录页
        header('Location: /auth/login');
        exit;
    }
}

// 路由
$router = new Router();

// 注册路由
$router->get('/', 'home_controller@index');
$router->get('/about', 'home_controller@about');
$router->get('/contact', 'home_controller@contact');
$router->get('/upload', 'home_controller@upload');

// 仪表盘路由（需要认证）
$router->get('/dashboard', function () {
    require_auth();
    $controller = new dashboard_controller();
    $controller->index();
});
$router->get('/dashboard/nodes', function () {
    require_auth();
    $controller = new dashboard_controller();
    $controller->nodes();
});
$router->get('/dashboard/apikeys', function () {
    require_auth();
    $controller = new dashboard_controller();
    $controller->apikeys();
});
$router->get('/dashboard/history', function () {
    require_auth();
    $controller = new dashboard_controller();
    $controller->history();
});
$router->get('/dashboard/settings', function () {
    require_auth();
    $controller = new dashboard_controller();
    $controller->settings();
});

// 认证路由
$router->get('/auth/login', 'auth_controller@login');
$router->get('/auth/register', 'auth_controller@register');
$router->get('/auth/forgot-password', 'auth_controller@forgot_password');
$router->get('/auth/reset-password', 'auth_controller@reset_password');

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
