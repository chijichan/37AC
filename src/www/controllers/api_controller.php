<?php

/**
 * API 代理控制器
 * 将上传相关请求代理到 Flask 后端，X-API-Key 在服务端注入，不下发到前端。
 *
 * 注意：SSE 流式代理为长连接。PHP 内置开发服务器（php -S）为单线程，
 * 流式传输期间会阻塞其他请求；生产环境请使用 Apache / Nginx + PHP-FPM。
 */
class api_controller extends controller
{
    /**
     * POST /api/upload
     * 代理上传识别请求。X-Stream-Response: true 时以 SSE 流式回传。
     */
    public function upload()
    {
        $this->requireApiKey();

        $wantStream = (($_SERVER['HTTP_X_STREAM_RESPONSE'] ?? '') === 'true');

        $ch = $this->buildBaseCurl(API_BASE_URL . '/upload');
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => [
                'X-API-Key: ' . UPLOAD_API_KEY,
                'X-Requested-With: XMLHttpRequest',
                'X-Stream-Response: ' . ($wantStream ? 'true' : 'false'),
            ],
        ]);

        // 重建 multipart/form-data 请求体。
        // 注意：不能用 php://input 原样转发——PHP 在解析 multipart 请求时
        // 已消费原始输入流（用于填充 $_POST / $_FILES），此时 php://input 为空，
        // 会导致后端收不到文件。必须基于 $_POST / $_FILES 重建。
        // CURLOPT_POSTFIELDS 传数组时 cURL 会自动生成 multipart 边界与 Content-Type。
        $postfields = $_POST;
        foreach ($_FILES as $field => $file) {
            if (is_array($file['tmp_name'])) {
                // 多文件字段
                foreach ($file['tmp_name'] as $i => $tmp) {
                    if ($tmp === '' || $file['error'][$i] !== UPLOAD_ERR_OK) {
                        continue;
                    }
                    $postfields[$field][] = new CURLFile($tmp, $file['type'][$i], $file['name'][$i]);
                }
            } elseif ($file['tmp_name'] !== '' && $file['error'] === UPLOAD_ERR_OK) {
                // 单文件字段
                $postfields[$field] = new CURLFile($file['tmp_name'], $file['type'], $file['name']);
            }
        }
        curl_setopt($ch, CURLOPT_POSTFIELDS, $postfields);

        if ($wantStream) {
            $this->passthroughStream($ch);
        } else {
            $this->passthroughJson($ch);
        }
    }

    /**
     * GET /api/tasks/{task_id}/stream
     * 代理任务结果 SSE 流。
     */
    public function task_stream($task_id)
    {
        $this->requireApiKey();

        $ch = $this->buildBaseCurl(API_BASE_URL . '/tasks/' . rawurlencode($task_id) . '/stream');
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Accept: text/event-stream']);
        $this->passthroughStream($ch);
    }

    /**
     * GET /api/tasks/{task_id}
     * 代理任务结果 JSON 查询。
     */
    public function task_result($task_id)
    {
        $this->requireApiKey();

        $ch = $this->buildBaseCurl(API_BASE_URL . '/tasks/' . rawurlencode($task_id));
        $this->passthroughJson($ch);
    }

    /* ==================== 内部方法 ==================== */

    private function requireApiKey()
    {
        if (!defined('UPLOAD_API_KEY') || !UPLOAD_API_KEY) {
            http_response_code(500);
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['success' => false, 'message' => '服务端未配置 UPLOAD_API_KEY']);
            exit;
        }
    }

    private function buildBaseCurl($url)
    {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 300,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);
        return $ch;
    }

    /**
     * 普通 JSON 代理：等待完整响应后转发状态码与内容。
     */
    private function passthroughJson($ch)
    {
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HEADER, true);
        $response = curl_exec($ch);

        if ($response === false) {
            $errno = curl_errno($ch);
            curl_close($ch);
            http_response_code(502);
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['success' => false, 'message' => '后端服务不可用 (curl ' . $errno . ')']);
            return;
        }

        $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE) ?: 200;
        $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $body = substr($response, $headerSize);
        curl_close($ch);

        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        echo $body;
    }

    /**
     * SSE 流式代理：边收边吐，状态行与 Content-Type 透传。
     */
    private function passthroughStream($ch)
    {
        // 关闭所有 PHP 输出缓冲，保证实时性
        while (ob_get_level()) {
            ob_end_clean();
        }

        curl_setopt($ch, CURLOPT_HEADERFUNCTION, function ($ch, $line) {
            $len = strlen($line);
            $trimmed = trim($line);
            if ($trimmed === '') {
                return $len;
            }
            if (stripos($trimmed, 'HTTP/') === 0) {
                if (preg_match('#\d{3}#', $trimmed, $m)) {
                    http_response_code((int) $m[0]);
                }
                return $len;
            }
            $parts = explode(':', $trimmed, 2);
            if (count($parts) === 2 && strcasecmp(trim($parts[0]), 'Content-Type') === 0) {
                header('Content-Type: ' . trim($parts[1]));
            }
            return $len;
        });

        curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($ch, $data) {
            echo $data;
            flush();
            return strlen($data);
        });

        // 告知反向代理（如有）不要缓冲
        header('X-Accel-Buffering: no');
        header('Cache-Control: no-cache');

        curl_exec($ch);
        curl_close($ch);
        exit;
    }
}
