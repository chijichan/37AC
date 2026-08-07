<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    /* ===== Hero ===== */
    .hero {
        display: grid;
        grid-template-columns: 1.05fr .95fr;
        align-items: center;
        gap: 3rem;
        padding: 3.5rem 0 4rem;
    }

    .hero-copy h1 {
        margin-bottom: 1rem;
    }

    .hero-copy .lede {
        font-size: 1.08rem;
        margin-bottom: 1.8rem;
    }

    .hero-actions {
        display: flex;
        gap: .8rem;
        flex-wrap: wrap;
    }

    .hero-media {
        position: relative;
    }

    .hero-media video {
        width: 100%;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-float);
        transform: rotate(1.2deg);
        transition: transform var(--ac-dur) var(--ac-ease-spring);
    }

    .hero-media:hover video {
        transform: rotate(0deg) scale(1.01);
    }

    .hero-media::before {
        content: '';
        position: absolute;
        inset: 8% -4% -4% 8%;
        background: var(--ac-pink-100);
        border-radius: var(--ac-radius-card);
        z-index: -1;
    }

    /* ===== Bento 特性 ===== */
    .section {
        padding: 3.5rem 0;
    }

    .section-head {
        margin-bottom: 2rem;
    }

    .section-head p {
        margin-top: .4rem;
    }

    .bento {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.2rem;
    }

    .bento .cell {
        padding: 1.6rem;
        border-radius: var(--ac-radius-card);
        background: var(--ac-surface);
        box-shadow: var(--ac-shadow-card);
    }

    .bento .cell h3 {
        margin-bottom: .55rem;
    }

    .bento .cell p {
        font-size: .95rem;
    }

    .bento .cell-hero {
        grid-row: span 2;
        background: linear-gradient(160deg, var(--ac-pink-50), var(--ac-pink-100));
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .bento .cell-hero h3 {
        font-size: 1.5rem;
    }

    .bento .cell-accent {
        background: var(--ac-pink-50);
    }

    .bento .cell-fill {
        grid-column: span 2;
    }

    .bento .cell-icon {
        font-size: 1.6rem;
        color: var(--ac-pink-500);
        margin-bottom: .8rem;
    }

    /* ===== 展示 ===== */
    .showcase-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.6rem;
        align-items: start;
    }

    .showcase-grid figure {
        margin: 0;
    }

    .showcase-grid img {
        width: 100%;
        border-radius: var(--ac-radius-card);
        box-shadow: var(--ac-shadow-card);
    }

    .showcase-grid figcaption {
        margin-top: .6rem;
        font-size: .85rem;
        color: var(--ac-ink-500);
    }

    .showcase-grid .offset {
        margin-top: 3rem;
    }

    /* ===== 底部 CTA ===== */
    .cta {
        text-align: center;
        padding: 4rem 1rem 4.5rem;
    }

    .cta h2 {
        margin-bottom: .6rem;
    }

    .cta p {
        margin: 0 auto 1.6rem;
    }

    @media (max-width: 860px) {
        .hero {
            grid-template-columns: 1fr;
            gap: 2rem;
            padding-top: 2.2rem;
        }

        .hero-media::before {
            inset: 8% 4% -4% 8%;
        }

        .hero-media video {
            transform: none;
        }

        .hero-media:hover video {
            transform: none;
        }

        .bento {
            grid-template-columns: 1fr;
        }

        .bento .cell-hero,
        .bento .cell-fill {
            grid-row: auto;
            grid-column: auto;
        }

        .showcase-grid {
            grid-template-columns: 1fr;
        }

        .showcase-grid .offset {
            margin-top: 0;
        }
    }
</style>

<section class="hero ac-container">
    <div class="hero-copy">
        <h1>认出每一张图里的她</h1>
        <p class="lede">上传截图、插画或 COS 照片，37AC 通过双引擎模型告诉你角色是谁、来自哪部作品，分布式节点秒级返回结果。</p>
        <div class="hero-actions">
            <a href="/upload" class="btn btn-primary btn-lg">开始识别</a>
            <a href="/about" class="btn btn-ghost btn-lg">工作原理</a>
        </div>
    </div>
    <div class="hero-media">
        <video autoplay muted loop playsinline
            src="https://static.322337.xyz/view.php/775149afcebb606746e9140edf909879.mp4"></video>
    </div>
</section>

<section class="section ac-container">
    <div class="section-head reveal">
        <h2>一套完整的识别流水线</h2>
        <p>从图片上传到结果推送，每一步都为速度和准确率做过取舍。</p>
    </div>
    <div class="bento">
        <div class="cell cell-hero reveal">
            <div class="cell-icon"><i class="ph ph-scan"></i></div>
            <h3>双引擎识别</h3>
            <p>YOLOv8 先定位画面中的人物区域，ResNet18 配合 CBAM 注意力机制完成精细分类，本地推理毫秒级响应。</p>
        </div>
        <div class="cell reveal">
            <div class="cell-icon"><i class="ph ph-sparkle"></i></div>
            <h3>LLM 增强</h3>
            <p>接入多模态大模型，本地模型认不出的冷门角色交给它继续判断。</p>
        </div>
        <div class="cell cell-accent reveal">
            <div class="cell-icon"><i class="ph ph-share-network"></i></div>
            <h3>分布式节点</h3>
            <p>中心调度加边缘推理，多节点按能力自动匹配任务，并行消化请求。</p>
        </div>
        <div class="cell cell-fill reveal">
            <div class="cell-icon"><i class="ph ph-broadcast"></i></div>
            <h3>实时推送</h3>
            <p>基于 SSE 的流式结果返回，排队、分配、识别中的每个状态都实时可见，不再盯着转圈等待。</p>
        </div>
    </div>
</section>

<section class="section ac-container">
    <div class="section-head reveal">
        <h2>实际效果</h2>
        <p>插画、截图、手办照片都可以直接上传。</p>
    </div>
    <div class="showcase-grid">
        <figure class="reveal">
            <img src="https://upload-bbs.miyoushe.com/upload/2026/05/16/313131301/0c4ac0a32f95757ab03f112f6bca3a70_1548251836036077026.jpg"
                alt="角色识别示例：游戏插画" loading="lazy" />
            <figcaption>插画识别示例</figcaption>
        </figure>
        <figure class="offset reveal">
            <img src="https://upload-bbs.miyoushe.com/upload/2026/05/16/313131301/47a0df48f93aaab740ad020f82a50c26_3771695543515120247.png"
                alt="角色识别示例：角色立绘" loading="lazy" />
            <figcaption>立绘识别示例</figcaption>
        </figure>
    </div>
</section>

<section class="cta ac-container reveal">
    <h2>上传第一张图片</h2>
    <p>支持 JPG 与 PNG，最大 10MB。</p>
    <a href="/upload" class="btn btn-primary btn-lg">开始识别</a>
</section>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>