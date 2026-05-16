<?php
require_once ROOT_PATH . '/views/layout.php';
?>

<!-- <div class="jumbotron">
    <h1>Flask</h1>
    <p class="lead">Flask is a free web framework for building great Web sites and Web applications using HTML, CSS and JavaScript.</p>
    <p><a href="http://flask.pocoo.org/" class="btn btn-primary btn-large">Learn more &raquo;</a></p>
</div>

<div class="row">
    <div class="col-md-4">
        <h2>Getting started</h2>
        <p>
            Flask gives you a powerful, patterns-based way to build dynamic websites that
            enables a clean separation of concerns and gives you full control over markup
            for enjoyable, agile development.
        </p>
        <p><a class="btn btn-default" href="http://flask.pocoo.org/docs/">Learn more &raquo;</a></p>
    </div>
    <div class="col-md-4">
        <h2>Get more libraries</h2>
        <p>The Python Package Index is a repository of software for the Python programming language.</p>
        <p><a class="btn btn-default" href="https://pypi.python.org/pypi">Learn more &raquo;</a></p>
    </div>
    <div class="col-md-4">
        <h2>Microsoft Azure</h2>
        <p>You can easily publish to Microsoft Azure using Visual Studio. Find out how you can host your application using a free trial today.</p>
        <p><a class="btn btn-default" href="http://azure.microsoft.com">Learn more &raquo;</a></p>
    </div>
</div> -->

<style>
    .article {
        max-width: 100vw;
        height: 80vh;
        display: grid;
        grid-template-rows: 40vh 40vh;
        position: relative;
    }

    .article img {
        object-fit: cover;
        width: 100%;
        height: 100%;
        height: 40vh;
    }

    .article video {
        object-fit: cover;
        width: 100%;
        height: 100%;
        height: 40vh;
    }

    .article__poster {
        position: sticky;
        top: 0;
        left: 0;
        right: 0;
        height: 40vh;
        overflow: hidden;
    }

    .article__info {
        text-align: center;
        z-index: 2;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 0.5rem;
        height: 40vh;
    }

    .article__info {
        background: canvas;
    }

    .poster__info {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: rgba(255, 255, 255, 0);
        color: white;
        text-align: center;
        z-index: 10;
    }

    .poster__info h2 {
        font-size: 3rem;
        margin-bottom: 1rem;
        font-weight: bold;
    }

    .poster__info p {
        font-size: 1.5rem;
        margin: 0;
    }

    .poster__info .left {
        position: absolute;
        left: 0;

        transform: translateY(-50%);
        z-index: 10;
        color: white;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
    }

    .poster__info .right {
        position: absolute;
        right: 0;

        transform: translateY(-50%);
        z-index: 10;
        color: white;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
    }

    #FIRST {
        height: 90vh;
        grid-template-rows: 45vh 45vh;
    }

    #FIRST .article__poster {
        height: 45vh;
    }

    #FIRST .article__poster video {
        height: 45vh;
    }

    #FIRST .article__info {
        height: 45vh;
    }
</style>
<div class="article" id="FIRST" style="--index: 0">
    <div class="article__poster">
        <div class="poster__info">
            <h2 style="color: rgba(255, 255, 255, 0.8);">37AC</h2>
            <p style="color: rgba(255, 255, 255, 0.8);">AI角色识别系统</p>
        </div>
        <video autoplay muted src="https://static.322337.xyz/view.php/775149afcebb606746e9140edf909879.mp4" autobuffer="true"
            width="100%"></video>
    </div>
    <div class="article__info">
        <h2>精准识别 · 智能分析</h2>
        <p>基于"old"AI技术，快速识别二次元角色，不提供准确的角色信息和来源分析。让每一张图片都不再陌生！</p>
    </div>
</div>
<div class="article" style="--index: 1">
    <div class="article__poster">
        <div class="poster__info">
            <h2
                style="color: rgba(0, 0, 0, 0.8); text-shadow: -1px 1px 0 rgba(255, 255, 255, 0.9), 1px 1px 0 rgba(255, 255, 255, 0.9), 1px -1px 0 rgba(255, 255, 255, 0.9), -1px -1px 0 rgba(255, 255, 255, 0.9); margin-top: -80px;">
                #SECOND</h2>
            <p
                style="color: rgba(0, 0, 0, 0.8); text-shadow: -1px 1px 0 rgba(255, 255, 255, 0.9), 1px 1px 0 rgba(255, 255, 255, 0.9), 1px -1px 0 rgba(255, 255, 255, 0.9), -1px -1px 0 rgba(255, 255, 255, 0.9);">
                角色识别案例</p>
        </div>
        <!-- <img class="img-responsive" src="https://static.322337.xyz/view.php/47a0df48f93aaab740ad020f82a50c26.png" -->
        <img class="img-responsive" src="https://upload-bbs.miyoushe.com/upload/2026/05/16/313131301/47a0df48f93aaab740ad020f82a50c26_3771695543515120247.png"
            alt="欸嘿嘿" />
    </div>
    <div class="article__info">
        <h2>高清识别</h2>
        <p>支持高清图片识别，准确率高达20%以上，快速匹配动漫、游戏角色数据库。</p>
    </div>
</div>
<div class="article" style="--index: 2">
    <div class="article__poster">
        <div class="poster__info">
            <h2
                style="color: rgb(116,225,223,0.8); text-shadow: -1px 1px 0 rgba(255, 255, 255, 0.9), 1px 1px 0 rgba(255, 255, 255, 0.9), 1px -1px 0 rgba(255, 255, 255, 0.9), -1px -1px 0 rgba(255, 255, 255, 0.9);">
                #THIRD</h2>
            <p
                style="color: rgb(116,225,223,0.8); text-shadow: -1px 1px 0 rgba(255, 255, 255, 0.9), 1px 1px 0 rgba(255, 255, 255, 0.9), 1px -1px 0 rgba(255, 255, 255, 0.9), -1px -1px 0 rgba(255, 255, 255, 0.9);">
                智能匹配</p>
        </div>
        <!-- <img class="img-responsive" src="https://static.322337.xyz/view.php/0c4ac0a32f95757ab03f112f6bca3a70.jpg" alt="欸嘿嘿嘿" /> -->
        <img class="img-responsive" src="https://upload-bbs.miyoushe.com/upload/2026/05/16/313131301/0c4ac0a32f95757ab03f112f6bca3a70_1548251836036077026.jpg" alt="欸嘿嘿嘿" />
    </div>
    <div class="article__info">
        <h2>没有多平台支持</h2>
        <p>不兼容各种图片格式，不支持批量识别，为您的二次元收藏提供不完整的角色信息管理。</p>
    </div>
</div>
<?php

require_once ROOT_PATH . '/views/footer.php';
?>