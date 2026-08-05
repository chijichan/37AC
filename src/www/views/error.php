<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .error-page {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 4rem 1.25rem;
    }

    .error-code {
        font-family: var(--ac-font-display);
        font-size: clamp(4.5rem, 14vw, 7rem);
        font-weight: 800;
        line-height: 1;
        color: var(--ac-pink-500);
        margin-bottom: .8rem;
    }

    .error-page p {
        margin: 0 auto 1.8rem;
    }

    .error-actions {
        display: flex;
        gap: .8rem;
        justify-content: center;
        flex-wrap: wrap;
    }
</style>

<div class="error-page">
    <div class="error-code">404</div>
    <h2>页面走丢了</h2>
    <p><?= htmlspecialchars(isset($message) ? $message : '你访问的页面不存在，或者已经被移动。') ?></p>
    <div class="error-actions">
        <a href="/" class="btn btn-primary">返回首页</a>
        <a href="/upload" class="btn btn-ghost">去识别图片</a>
    </div>
</div>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>
