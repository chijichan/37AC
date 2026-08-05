<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .about-hero {
        padding: 3rem 0 1rem;
    }

    .about-hero p {
        margin-top: .5rem;
        font-size: 1.05rem;
    }

    .about-section {
        padding: 2.2rem 0;
    }

    .about-section h2 {
        margin-bottom: .4rem;
    }

    .about-section .section-sub {
        margin-bottom: 1.6rem;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.2rem;
    }

    .about-grid .card h3 {
        display: flex;
        align-items: center;
        gap: .5rem;
        margin-bottom: .6rem;
    }

    .about-grid .card h3 i {
        color: var(--ac-pink-500);
        font-size: 1.3rem;
    }

    .about-grid .card p {
        font-size: .95rem;
    }

    .tech-stack {
        display: flex;
        flex-wrap: wrap;
        gap: .55rem;
    }

    .project-tree {
        font-family: var(--ac-font-mono);
        font-size: .88rem;
        line-height: 1.8;
        color: var(--ac-ink-700);
        overflow-x: auto;
    }

    @media (max-width: 768px) {
        .about-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<section class="about-hero ac-container">
    <h2>关于 37AC</h2>
    <p>基于深度学习的二次元角色识别系统，让每一张动漫图片都能被认出。</p>
</section>

<section class="about-section ac-container">
    <p>
        37AC（Anime Character Recognition）是一个基于深度学习的二次元角色识别系统。
        项目采用分布式 C/S 架构，由中心服务器和多个边缘推理节点组成，支持多节点并行推理。
        无论是本地模型推理还是接入多模态大模型（LLM），37AC 都能提供快速的角色识别能力。
    </p>
</section>

<section class="about-section ac-container">
    <h2>核心设计</h2>
    <p class="section-sub">系统在工程上的四个关键决策。</p>
    <div class="about-grid">
        <div class="card card-hover reveal">
            <h3><i class="ph ph-scan"></i>双引擎流水线</h3>
            <p>YOLOv8 快速定位人物区域，ResNet18 与 CBAM 注意力机制精确分类，支持本地推理与 LLM 多模态识别双引擎。</p>
        </div>
        <div class="card card-hover reveal">
            <h3><i class="ph ph-share-network"></i>分布式架构</h3>
            <p>中心服务器加边缘节点模式，支持能力感知调度、负载均衡、自动重连与心跳检测，保障服务可用性。</p>
        </div>
        <div class="card card-hover reveal">
            <h3><i class="ph ph-layout"></i>双前端架构</h3>
            <p>Flask RESTful API 后端配合 PHP MVC 响应式前端，同时提供 Web 仪表盘和开放 API，方便二次开发。</p>
        </div>
        <div class="card card-hover reveal">
            <h3><i class="ph ph-broadcast"></i>实时推送</h3>
            <p>基于 SSE（Server-Sent Events）的事件总线，任务状态与结果实时推送到前端，支持流式上传。</p>
        </div>
    </div>
</section>

<section class="about-section ac-container">
    <h2>技术栈</h2>
    <p class="section-sub">项目涉及的主要技术与框架。</p>
    <div class="tech-stack reveal">
        <span class="badge badge-pink">Python 3.12</span>
        <span class="badge badge-pink">PyTorch</span>
        <span class="badge badge-pink">Flask 3</span>
        <span class="badge badge-pink">PHP 7+</span>
        <span class="badge badge-pink">MySQL</span>
        <span class="badge badge-pink">YOLOv8</span>
        <span class="badge badge-pink">ResNet18</span>
        <span class="badge badge-pink">CBAM</span>
        <span class="badge badge-pink">SSE</span>
        <span class="badge badge-pink">JWT</span>
        <span class="badge badge-pink">DirectML</span>
    </div>
</section>

<section class="about-section ac-container">
    <h2>项目结构</h2>
    <p class="section-sub">源码仓库目录概览。</p>
    <div class="card">
        <pre class="project-tree">37AC/
├─ src/cli/       # 命令行客户端（训练、预测、边缘节点）
├─ src/server/    # Flask 服务端（中心服务器）
├─ src/www/       # PHP MVC Web 应用
├─ docs/          # 项目文档
├─ scripts/       # 数据库脚本
└─ tests/         # 测试用例</pre>
    </div>
</section>

<section class="about-section ac-container">
    <h2>开源协议</h2>
    <p class="section-sub">本项目仅限内部研究使用，禁止商用及二次分发。</p>
    <p>代码托管在 <a href="https://github.com/chijichan/37AC" target="_blank" rel="nofollow">GitHub</a>，欢迎提交 Issue 与建议。</p>
</section>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>
