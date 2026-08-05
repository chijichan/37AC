<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .contact-hero {
        padding: 3rem 0 1.5rem;
    }

    .contact-hero p {
        margin-top: .5rem;
        font-size: 1.05rem;
    }

    .contact-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2.5rem;
        align-items: center;
        padding-bottom: 3rem;
    }

    .contact-methods {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .contact-method {
        display: flex;
        align-items: flex-start;
        gap: .9rem;
        padding: 1.2rem 1.3rem;
    }

    .contact-method .icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        flex-shrink: 0;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-pink-100);
        color: var(--ac-pink-600);
        font-size: 1.35rem;
    }

    .contact-method .info {
        flex: 1;
        min-width: 0;
    }

    .contact-method .info strong {
        display: block;
        margin-bottom: .15rem;
    }

    .contact-method .info a {
        word-break: break-all;
        font-weight: 600;
    }

    .contact-method .info span {
        display: block;
        margin-top: .2rem;
        font-size: .85rem;
        color: var(--ac-ink-500);
    }

    .contact-image img {
        width: 100%;
        max-height: 520px;
        object-fit: cover;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-float);
    }

    @media (max-width: 860px) {
        .contact-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<section class="contact-hero ac-container">
    <h2>联系我们</h2>
    <p>部署接入、合作建议或只是想聊聊，都欢迎来信。</p>
</section>

<section class="contact-grid ac-container">
    <div class="contact-methods">
        <div class="card contact-method reveal">
            <div class="icon"><i class="ph ph-envelope-simple"></i></div>
            <div class="info">
                <strong>技术支持</strong>
                <a href="mailto:gongjuren686@yeah.net">gongjuren686@yeah.net</a>
                <span>服务端部署、API 接入、节点配置相关问题</span>
            </div>
        </div>
        <div class="card contact-method reveal">
            <div class="icon"><i class="ph ph-cat"></i></div>
            <div class="info">
                <strong>站长</strong>
                <a href="mailto:qijijiang@126.com">qijijiang@126.com</a>
                <span>项目合作、功能建议、问题反馈</span>
            </div>
        </div>
        <div class="card contact-method reveal">
            <div class="icon"><i class="ph ph-github-logo"></i></div>
            <div class="info">
                <strong>GitHub</strong>
                <a href="https://github.com/chijichan/37AC" target="_blank" rel="nofollow">github.com/chijichan/37AC</a>
                <span>项目源码、Issue 提交</span>
            </div>
        </div>
    </div>
    <div class="contact-image reveal">
        <img src="https://upload-bbs.miyoushe.com/upload/2025/02/07/313131301/ddf67f7b51d2c90ace429c0cd250f394_4886388257026393631.png"
            alt="37AC 展示插画" loading="lazy" />
    </div>
</section>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>
