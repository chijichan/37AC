<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $title; ?> - 37AC</title>
    <!-- <link rel="stylesheet" type="text/css" href="/static/content/bootstrap.min.css" /> -->
    <link rel="stylesheet" type="text/css" href="/static/css/pico.min.css" />
    <link rel="stylesheet" type="text/css"
        href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css" />
    <!-- <link rel="stylesheet" type="text/css" href="/static/css/site.css" /> -->
    <style>
        /* 强制显示垂直滚动条,避免不同页面宽度不一致 */
        html {
            overflow-y: scroll;
        }

        /* 全屏白屏遮罩层 */
        ._loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s ease-out;
            /* 遮罩层淡出动画 */
        }

        /* 加载动画容器 */
        ._loading-spinner {
            text-align: center;
        }

        /* 旋转圆圈动画 */
        ._spinner-border {
            width: 80px;
            height: 80px;
            /* animation: spin 1s linear infinite; */
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        ._loading-text {
            color: transparent;
            /* 文字透明，显示背景渐变 */
            background-image: linear-gradient(90deg,
                    #000 25%,
                    /* 黑色起始 */
                    rgba(90, 0, 127, 0.6) 40%,
                    /* 暗紫色（透明度0.6，增强层次） */
                    rgba(0, 10, 80, 0.6) 60%,
                    /* 墨蓝色（过渡色，平衡紫黑调性） */
                    #000 75%
                    /* 黑色结束 */
                );
            background-size: 400% 400%;
            /* 放大背景尺寸，为动画预留移动空间 */
            animation: gradient-flow 1.5s ease-in-out infinite;
            /* 应用循环动画 */
            -webkit-background-clip: text;
            /* 兼容WebKit内核浏览器（如Chrome、Safari） */
            background-clip: text;
            /* 背景裁剪到文字形状内 */
            font-size: 18px;
        }

        @keyframes gradient-flow {
            0% {
                background-position: -100% 0;
            }

            /* 渐变起始位置在文字左侧外（-100%） */
            100% {
                background-position: 200% 0;
            }

            /* 渐变结束位置在文字右侧外（200%） */
        }

        /* 内容容器初始状态（隐藏） */
        ._content {
            opacity: 0;
            transform: scale(0.95);
            transition: opacity 0.3s ease-in, transform 0.1s ease-in;
            /* 缓慢恢复动画 */
        }

        /* 内容显示状态 */
        ._content.show {
            opacity: 1;
            transform: scale(1);
        }
    </style>
    <link rel="icon" href="https://static.322337.xyz/view.php/3c2d0a0c603703e2a99ce22f85eb3087.ico" type="image/x-icon" />
    <script src="/static/scripts/modernizr-2.6.2.js"></script>
</head>

<body>
    <!-- 全屏白屏遮罩层 -->
    <div id="_loading-overlay" class="_loading-overlay">
        <div class="_loading-spinner">
            <!-- 加载动画：旋转圆圈 -->
            <div class="_spinner-border">
                <img src="https://static.322337.xyz/view.php/2b41dcf3c57aabd59adb77f0c90c6eba.gif" />
            </div>
            <p class="_loading-text">页面加载中...</p>
        </div>
    </div>

    <div class="container" style="transition: top 0.3s ease-in-out;">
        <nav class="container-nav">
            <ul>
                <li>
                    <a href="/"><img style="width: 100px;"
                            src="https://static.322337.xyz/view.php/2ca3f3e71b981414c517e39fd9dae033.png" /></a>
                </li>
            </ul>
            <ul>
                <li><a href="/">首页</a></li>
                <li><a href="/upload">上传</a></li>
                <li><a href="/dashboard">控制台</a></li>
            </ul>
        </nav>
    </div>

    <div id="_content" class="_content">