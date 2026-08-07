<?php
// 页面 meta 变量（视图可在引用本文件前覆盖）
$site_name = '37AC';
$page_title = isset($title) && $title ? $title : $site_name;
$page_title_full = $page_title === $site_name ? $site_name : $site_name . ' - ' . $page_title;
$page_description = isset($description) && $description ? $description : '37AC 是一款面向二次元爱好者的 AI 角色识别与管理平台，支持上传图片识别动漫和游戏角色。';
$page_keywords = isset($keywords) && $keywords ? $keywords : '37AC,动漫角色识别,二次元识别,AI识别,角色识别';
$page_robots = isset($robots) && $robots ? $robots : 'index,follow,max-image-preview:large';
$page_og_type = isset($og_type) && $og_type ? $og_type : 'website';
$page_og_image = isset($og_image) && $og_image ? $og_image : 'https://static.322337.xyz/view.php/3c2d0a0c603703e2a99ce22f85eb3087.ico';
$_scheme = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
$_host = $_SERVER['HTTP_HOST'] ?? '127.0.0.1';
$page_canonical = isset($canonical_url) && $canonical_url ? $canonical_url : $_scheme . '://' . $_host . ($_SERVER['REQUEST_URI'] ?? '/');
if (strpos($page_canonical, 'http') !== 0) {
    $page_canonical = $_scheme . '://' . $_host . $page_canonical;
}
?>
<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="<?php echo htmlspecialchars($page_description, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta name="keywords" content="<?php echo htmlspecialchars($page_keywords, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta name="robots" content="<?php echo htmlspecialchars($page_robots, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta name="author" content="37AC Team" />
    <meta name="theme-color" content="#FDF9FB" />
    <meta property="og:title" content="<?php echo htmlspecialchars($page_title_full, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta property="og:description" content="<?php echo htmlspecialchars($page_description, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta property="og:type" content="<?php echo htmlspecialchars($page_og_type, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta property="og:url" content="<?php echo htmlspecialchars($page_canonical, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta property="og:image" content="<?php echo htmlspecialchars($page_og_image, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta property="og:site_name" content="37AC" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="<?php echo htmlspecialchars($page_title_full, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta name="twitter:description" content="<?php echo htmlspecialchars($page_description, ENT_QUOTES, 'UTF-8'); ?>" />
    <meta name="twitter:image" content="<?php echo htmlspecialchars($page_og_image, ENT_QUOTES, 'UTF-8'); ?>" />
    <link rel="canonical" href="<?php echo htmlspecialchars($page_canonical, ENT_QUOTES, 'UTF-8'); ?>" />
    <link rel="sitemap" type="application/xml" title="Sitemap" href="/sitemap.xml" />
    <title><?php echo htmlspecialchars($page_title_full, ENT_QUOTES, 'UTF-8'); ?></title>
    <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "37AC",
            "url": "<?php echo htmlspecialchars($_scheme . '://' . $_host, ENT_QUOTES, 'UTF-8'); ?>",
            "description": "<?php echo htmlspecialchars($page_description, ENT_QUOTES, 'UTF-8'); ?>",
            "potentialAction": {
                "@type": "SearchAction",
                "target": "<?php echo htmlspecialchars($_scheme . '://' . $_host . '/upload', ENT_QUOTES, 'UTF-8'); ?>",
                "query-input": "required name=search"
            }
        }
    </script>

    <link rel="icon" href="https://static.322337.xyz/view.php/3c2d0a0c603703e2a99ce22f85eb3087.ico" type="image/x-icon" />

    <!-- 字体预加载（自托管可变字体） -->
    <link rel="preload" href="/static/fonts/nunito-latin.woff2" as="font" type="font/woff2" crossorigin />
    <link rel="preload" href="/static/fonts/jetbrains-mono-latin.woff2" as="font" type="font/woff2" crossorigin />

    <!-- 设计系统 -->
    <link rel="stylesheet" href="/static/css/ac-tokens.css" />
    <link rel="stylesheet" href="/static/css/ac-components.css" />
    <!-- 图标（Phosphor Icons，已本地化） -->
    <link rel="stylesheet" href="/static/css/vendor/phosphor/regular/style.css" />
    <link rel="stylesheet" href="/static/css/vendor/phosphor/bold/style.css" />

    <?php
    // 页面级附加样式：视图在引用布局前设置 $extra_css = ['/static/css/pages/xxx.css']
    if (!empty($extra_css) && is_array($extra_css)) {
        foreach ($extra_css as $css) {
            echo '    <link rel="stylesheet" href="' . htmlspecialchars($css, ENT_QUOTES, 'UTF-8') . '" />' . "\n";
        }
    }
    ?>

    <!-- 后端 API 基础 URL，所有前端页面统一引用 -->
    <script>
        window.API_BASE_URL = '<?= API_BASE_URL ?>';
    </script>
    <script src="/static/scripts/auth.js" defer></script>
    <script src="/static/scripts/app.js" defer></script>
</head>

<body>
    <!-- 全屏加载遮罩 -->
    <div id="loading-overlay" class="loading-overlay">
        <img src="https://static.322337.xyz/view.php/2b41dcf3c57aabd59adb77f0c90c6eba.gif" alt="加载中" />
        <p class="loading-text">页面加载中</p>
    </div>

    <header class="site-nav">
        <div class="ac-container nav-inner">
            <a href="/" class="nav-logo">
                <img src="https://static.322337.xyz/view.php/2ca3f3e71b981414c517e39fd9dae033.png" alt="37AC" />
            </a>
            <nav>
                <ul class="nav-links">
                    <li><a href="/upload" data-nav="/upload">上传识别</a></li>
                    <li><a href="/dashboard" data-nav="/dashboard">控制台</a></li>
                    <li class="user-menu" id="user-menu">
                        <button type="button" class="user-trigger" id="user-trigger" aria-haspopup="true" aria-expanded="false">
                            <span id="user-trigger-name">未登录</span>
                        </button>
                        <div class="user-dropdown" id="user-dropdown" role="menu">
                            <div class="ud-header">
                                <div class="ud-name" id="ud-name">未登录</div>
                                <small id="ud-role">访客</small>
                            </div>
                            <a href="/dashboard" class="ud-item" data-auth="user" role="menuitem">控制台</a>
                            <a href="/dashboard/settings" class="ud-item" data-auth="user" role="menuitem">账号设置</a>
                            <a href="/auth/login" class="ud-item" data-auth="guest" role="menuitem">登录 / 注册</a>
                            <button type="button" class="ud-item danger" data-auth="user" id="ud-logout" role="menuitem">退出登录</button>
                        </div>
                    </li>
                </ul>
            </nav>
        </div>
    </header>

    <main class="ac-main page-content">
