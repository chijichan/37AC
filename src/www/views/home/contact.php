<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .contact-section {
        margin-top: 2rem;
    }

    .contact-section hgroup {
        margin-bottom: 1.5rem;
    }

    .contact-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin: 2rem 0;
    }

    .contact-info {
        padding: 1.5rem;
        border: none;
        background: transparent;
    }

    .contact-info h3 {
        margin-bottom: 1rem;
    }

    .contact-info address {
        font-style: normal;
        line-height: 2;
    }

    .contact-info address a {
        word-break: break-all;
    }

    .contact-methods {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .contact-method {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 1rem;
        border: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        background: var(--pico-card-background-color);
    }

    .contact-method .icon {
        font-size: 1.5rem;
        line-height: 1;
    }

    .contact-method .info {
        flex: 1;
    }

    .contact-method .info strong {
        display: block;
        margin-bottom: 0.25rem;
    }

    .contact-method .info span {
        font-size: 0.875rem;
        color: var(--pico-muted-color);
    }

    .contact-image {
        border-radius: var(--pico-border-radius);
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .contact-image img {
        width: 100%;
        height: auto;
        max-height: 500px;
        object-fit: cover;
        border-radius: var(--pico-border-radius);
        box-shadow: var(--pico-box-shadow);
    }

    @media (max-width: 768px) {
        .contact-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<div class="container" id="_content">
    <div class="contact-section">
        <hgroup>
            <h2>联系我们</h2>
            <p>有任何问题或建议，欢迎通过以下方式与我们取得联系</p>
        </hgroup>
    </div>

    <div class="contact-grid">
        <div class="contact-info">
            <h3>联系方式</h3>
            <div class="contact-methods">
                <div class="contact-method">
                    <div class="icon">&#9993;</div>
                    <div class="info">
                        <strong>技术支持</strong>
                        <a href="mailto:gongjuren686@yeah.net">gongjuren686@yeah.net</a>
                        <span>服务端部署、API 接入、节点配置相关问题</span>
                    </div>
                </div>
                <div class="contact-method">
                    <div class="icon">&#128049;</div>
                    <div class="info">
                        <strong>站长</strong>
                        <a href="mailto:qijijiang@126.com">qijijiang@126.com</a>
                        <span>项目合作、功能建议、问题反馈</span>
                    </div>
                </div>
                <div class="contact-method">
                    <div class="icon">&#128187;</div>
                    <div class="info">
                        <strong>GitHub</strong>
                        <a href="https://github.com/chijichan/37AC" target="_blank" rel="nofollow">github.com/chijichan/37AC</a>
                        <span>项目源码、Issue 提交、贡献代码</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="contact-image">
            <img src="https://upload-bbs.miyoushe.com/upload/2025/02/07/313131301/ddf67f7b51d2c90ace429c0cd250f394_4886388257026393631.png"
                alt="二次元美图"
                loading="lazy" />
        </div>
    </div>
</div>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>