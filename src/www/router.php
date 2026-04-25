<?php

/**
 * 路由类
 */

class Router
{
    private $routes = [];
    private $params = [];

    /**
     * 添加 GET 路由
     */
    public function get($path, $handler)
    {
        $this->addRoute('GET', $path, $handler);
    }

    /**
     * 添加 POST 路由
     */
    public function post($path, $handler)
    {
        $this->addRoute('POST', $path, $handler);
    }

    /**
     * 添加路由
     */
    private function addRoute($method, $path, $handler)
    {
        $this->routes[] = [
            'method' => $method,
            'path' => $path,
            'handler' => $handler,
        ];
    }

    /**
     * 分发请求
     */
    public function dispatch()
    {
        $requestMethod = $_SERVER['REQUEST_METHOD'];
        $requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

        foreach ($this->routes as $route) {
            if ($route['method'] !== $requestMethod) {
                continue;
            }

            $pattern = $this->convertPathToRegex($route['path']);

            if (preg_match($pattern, $requestUri, $matches)) {
                array_shift($matches); // 移除完整匹配
                $this->params = $matches;
                return $this->callHandler($route['handler']);
            }
        }

        // 404 处理
        http_response_code(404);
        echo $this->render404();
    }

    /**
     * 将路径转换为正则表达式
     */
    private function convertPathToRegex($path)
    {
        $path = preg_replace('/\{(\w+)\}/', '([^/]+)', $path);
        return '#^' . $path . '$#';
    }

    /**
     * 调用处理器
     */
    private function callHandler($handler)
    {
        // 支持闭包函数
        if ($handler instanceof Closure) {
            return call_user_func_array($handler, $this->params);
        }

        // 支持 "controller@method" 字符串
        list($controller, $method) = explode('@', $handler);

        if (!class_exists($controller)) {
            throw new Exception("Controller {$controller} not found");
        }

        $instance = new $controller();

        if (!method_exists($instance, $method)) {
            throw new Exception("Method {$method} not found in {$controller}");
        }

        return call_user_func_array([$instance, $method], $this->params);
    }

    /**
     * 渲染 404 页面
     */
    private function render404()
    {
        return '
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>404 - Page Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #e74c3c; }
            </style>
        </head>
        <body>
            <h1>404 - Page Not Found</h1>
            <p>The page you are looking for does not exist.</p>
        </body>
        </html>
        ';
    }
}
