<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if ($isAjax) {
    // 如果是 AJAX 请求，只返回内容部分
    require_once ROOT_PATH . '/views/dashboard/overview.php';
    exit;
}

// 否则返回完整页面
require_once ROOT_PATH . '/views/dashboard/layout.php';
