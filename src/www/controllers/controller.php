<?php
/**
 * 控制器基类
 */

class Controller
{
    /**
     * 渲染视图
     */
    protected function view($viewName, $data = [])
    {
        extract($data);
        $viewPath = ROOT_PATH . '/views/' . $viewName . '.php';
        
        if (!file_exists($viewPath)) {
            throw new Exception("View {$viewName} not found");
        }

        require_once $viewPath;
    }

    /**
     * 返回 JSON 响应
     */
    protected function json($data, $statusCode = 200)
    {
        http_response_code($statusCode);
        header('Content-Type: application/json');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }

    /**
     * 重定向
     */
    protected function redirect($url)
    {
        header("Location: {$url}");
        exit;
    }

    /**
     * 获取 POST 数据
     */
    protected function post($key = null, $default = null)
    {
        if ($key === null) {
            return $_POST;
        }
        return $_POST[$key] ?? $default;
    }

    /**
     * 获取 GET 数据
     */
    protected function get($key = null, $default = null)
    {
        if ($key === null) {
            return $_GET;
        }
        return $_GET[$key] ?? $default;
    }
}
