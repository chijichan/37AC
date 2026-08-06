<?php

/**
 * 入口文件
 */

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

// 上传接口的站级 API Key（仅存服务端，经 /api/* 代理注入，勿下发前端）
$uploadApiKey = getenv('UPLOAD_API_KEY');
if (empty($uploadApiKey) && isset($_ENV['UPLOAD_API_KEY'])) {
    $uploadApiKey = $_ENV['UPLOAD_API_KEY'];
}
define('UPLOAD_API_KEY', $uploadApiKey ?: '');

// 调试模式：仅在 .env 显式开启时显示错误（生产环境必须为 false）
$appDebug = getenv('APP_DEBUG');
if ($appDebug === false && isset($_ENV['APP_DEBUG'])) {
    $appDebug = $_ENV['APP_DEBUG'];
}
$isDebug = filter_var($appDebug, FILTER_VALIDATE_BOOLEAN);
error_reporting($isDebug ? E_ALL : 0);
ini_set('display_errors', $isDebug ? '1' : '0');

spl_autoload_register(function ($class) {
    $file = ROOT_PATH . '/controllers/' . $class . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

/**
 * 通过后端 API 验证 JWT 令牌
 */
function verify_jwt_token($token)
{
    $ctx = stream_context_create([
        'http' => [
            'method' => 'GET',
            'timeout' => 5,
            'header' => "Authorization: Bearer $token\r\nContent-Type: application/json\r\n",
            'ignore_errors' => true,
        ],
    ]);
    $response = @file_get_contents(API_BASE_URL . '/auth/verify', false, $ctx);

    if ($response === false) {
        return null;
    }

    // 从响应头提取 HTTP 状态码
    $status_line = $http_response_header[0] ?? '';
    if (!preg_match('#\d{3}#', $status_line, $m) || $m[0] !== '200') {
        return null;
    }

    $data = json_decode($response, true);
    return $data['success'] ? $data['data'] : null;
}

/**
 * 获取当前请求中的 access_token
 */
function get_access_token()
{
    // 优先从 Authorization header 获取
    $auth_header = '';
    if (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
        $auth_header = $_SERVER['HTTP_AUTHORIZATION'];
    } elseif (!empty($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
        $auth_header = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
    }

    if (!empty($auth_header) && preg_match('/Bearer\s+(.+)/', $auth_header, $matches)) {
        return $matches[1];
    }

    // 从 Cookie 获取
    if (!empty($_COOKIE['access_token'])) {
        return $_COOKIE['access_token'];
    }

    return null;
}

/**
 * 认证检查中间件
 * 检查 JWT 令牌是否有效，未登录则重定向到登录页
 */
function require_auth()
{
    session_start();

    // Session 优先
    if (!empty($_SESSION['user_id'])) {
        return;
    }

    $token = get_access_token();
    if ($token) {
        $userData = verify_jwt_token($token);
        if ($userData && !empty($userData['user_id'])) {
            $_SESSION['user_id'] = $userData['user_id'];
            $_SESSION['role'] = $userData['role'] ?? 'user';
            return;
        }
    }

    // 未登录处理
    if (
        !empty($_SERVER['HTTP_X_REQUESTED_WITH']) &&
        strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) == 'xmlhttprequest'
    ) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'message' => '未登录，请先登录']);
        exit;
    }

    header('Location: /auth/login');
    exit;
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
$router->get('/auth/logout', 'auth_controller@logout');

// API 代理路由（X-API-Key 由服务端注入，前端零密钥）
$router->post('/api/upload', 'api_controller@upload');
$router->get('/api/tasks/{task_id}/stream', 'api_controller@task_stream');
$router->get('/api/tasks/{task_id}', 'api_controller@task_result');

// 执行路由分发
$router->dispatch();
