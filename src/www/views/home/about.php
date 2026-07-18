<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<style>
    .about-section {
        margin-top: 2rem;
    }

    .about-section hgroup {
        margin-bottom: 1.5rem;
    }

    .about-section hgroup h2 {
        margin-bottom: 0.25rem;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .about-card {
        padding: 1.5rem;
        border: 1px solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        background: var(--pico-card-background-color);
    }

    .about-card h3 {
        margin-bottom: 0.75rem;
    }

    .about-card p {
        margin: 0;
    }

    .tech-stack {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
    }

    .tech-stack span {
        padding: 0.25rem 0.75rem;
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        border-radius: var(--pico-border-radius);
        font-size: 0.875rem;
    }

    @media (max-width: 768px) {
        .about-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<div class="container" id="_content">
    <div class="about-section">
        <hgroup>
            <h2>关于 37AC</h2>
            <p>基于深度学习的二次元角色识别系统，让每一张动漫图片都能被精准识别</p>
        </hgroup>

        <p>
            37AC（Anime Character Recognition）是一个开源的、基于深度学习的二次元角色识别系统。
            项目采用分布式 C/S 架构，由中心服务器和多个边缘推理节点组成，支持高并发、多节点并行推理。
            无论是本地模型推理还是接入大语言模型（LLM），37AC 都能提供快速准确的角色识别能力。
        </p>
    </div>

    <div class="about-grid">
        <div class="about-card">
            <h3>核心能力</h3>
            <p>YOLOv8 快速人物定位 → ResNet18 + CBAM 注意力机制精确分类，支持本地推理与 LLM 多模态识别双引擎。</p>
        </div>
        <div class="about-card">
            <h3>分布式架构</h3>
            <p>中心服务器 + 边缘节点模式，支持能力感知调度、负载均衡、自动重连与心跳检测，保障服务高可用。</p>
        </div>
        <div class="about-card">
            <h3>双前端架构</h3>
            <p>Flask RESTful API 后端 + PHP MVC 响应式前端，同时提供 Web 仪表盘和 API 接口，方便二次开发。</p>
        </div>
        <div class="about-card">
            <h3>实时推送</h3>
            <p>基于 SSE（Server-Sent Events）的事件总线，任务结果实时推送到前端，支持流式上传与等待队列。</p>
        </div>
    </div>

    <div class="about-section">
        <hgroup>
            <h2>技术栈</h2>
            <p>项目涉及的主要技术与框架</p>
        </hgroup>
        <div class="tech-stack">
            <span>Python 3.12</span>
            <span>PyTorch 2.13</span>
            <span>Flask 3.1</span>
            <span>PHP 7+</span>
            <span>Pico CSS 2</span>
            <span>MySQL</span>
            <span>YOLOv8</span>
            <span>ResNet18</span>
            <span>CBAM</span>
            <span>SSE</span>
            <span>JWT</span>
        </div>
    </div>

    <div class="about-section">
        <hgroup>
            <h2>项目结构</h2>
            <p>源码仓库目录概览</p>
        </hgroup>
        <pre><code>37AC/
├── src/cli/       # 命令行客户端（边缘节点）
├── src/server/    # Flask 服务端（中心服务器）
├── src/www/       # PHP MVC Web 应用
├── docs/          # 项目文档
├── scripts/       # 数据库脚本
└── tests/         # 测试用例</code></pre>
    </div>

    <div class="about-section">
        <hgroup>
            <h2>开源协议</h2>
            <p>本项目基于开源协议发布，欢迎贡献代码与反馈建议</p>
        </hgroup>
        <p>37AC 是一个开源项目，代码托管在 GitHub 上。</p>
    </div>
</div>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>