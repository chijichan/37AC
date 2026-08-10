<?php
$extra_css = ['/static/css/vendor/cropper.min.css'];
require_once ROOT_PATH . '/views/layout.php';
?>

<!-- Cropper.js 仅本页使用（已本地化） -->
<script src="/static/scripts/vendor/cropper.min.js" defer></script>

<style>
    .upload-page {
        max-width: 860px;
        padding-top: 2.2rem;
        padding-bottom: 3.5rem;
    }

    .upload-page>.page-head {
        margin-bottom: 1.8rem;
    }

    .upload-page>.page-head p {
        margin-top: .4rem;
    }

    /* 上传区 */
    .upload-card {
        padding: 1.5rem;
        margin-bottom: 1.3rem;
    }

    .upload-area {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: .7rem;
        min-height: 180px;
        border: 2px dashed var(--ac-ink-100);
        border-radius: var(--ac-radius-card);
        background: var(--ac-bg);
        color: var(--ac-ink-500);
        cursor: pointer;
        transition: border-color var(--ac-dur-fast) var(--ac-ease-out),
            background var(--ac-dur-fast) var(--ac-ease-out),
            transform var(--ac-dur-fast) var(--ac-ease-spring);
    }

    .upload-area:hover,
    .upload-area.drag-over {
        border-color: var(--ac-pink-400);
        background: var(--ac-pink-50);
    }

    .upload-area.drag-over {
        transform: scale(1.01);
    }

    .upload-area .ua-icon {
        font-size: 2.4rem;
        color: var(--ac-pink-400);
    }

    .upload-area .ua-title {
        font-weight: 700;
        color: var(--ac-ink-900);
    }

    .upload-area .ua-sub {
        font-size: .85rem;
    }

    /* 链接上传 */
    .link-divider {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 1.3rem 0 .9rem;
        color: var(--ac-ink-300);
        font-size: .82rem;
    }

    .link-divider::before,
    .link-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid var(--ac-ink-100);
    }

    .link-row {
        display: flex;
        gap: .6rem;
    }

    .link-row .input {
        flex: 1;
    }

    .link-row .btn {
        flex-shrink: 0;
    }

    /* 分组卡片（重置 fieldset 默认样式） */
    fieldset.option-group {
        border: none;
        padding: 1.2rem 1.3rem;
        margin: 0 0 1.3rem;
        border-radius: var(--ac-radius-card);
        background: var(--ac-surface);
        box-shadow: var(--ac-shadow-card);
        transition: opacity var(--ac-dur) var(--ac-ease-out);
    }

    /* 未选择图片时的降级态 */
    fieldset.option-group:disabled {
        opacity: .5;
    }

    fieldset.option-group:disabled legend::after {
        content: '（请先选择图片）';
        font-weight: 600;
        font-size: .82rem;
        color: var(--ac-ink-500);
        margin-left: .4rem;
    }

    fieldset.option-group legend {
        float: left;
        width: 100%;
        padding: 0;
        margin-bottom: .9rem;
        font-family: var(--ac-font-display);
        font-weight: 800;
        font-size: 1rem;
        color: var(--ac-ink-900);
    }

    fieldset.option-group .group-body {
        clear: both;
    }

    .checkbox-row {
        display: flex;
        align-items: center;
        gap: .5rem;
        font-size: .95rem;
        font-weight: 600;
        color: var(--ac-ink-900);
        cursor: pointer;
        width: fit-content;
    }

    .checkbox-row input[type="checkbox"] {
        width: 18px;
        height: 18px;
        accent-color: var(--ac-pink-600);
        cursor: pointer;
    }

    .sub-options {
        display: none;
        margin-top: .9rem;
        padding: .9rem 1rem;
        border-radius: var(--ac-radius-input);
        background: var(--ac-bg);
    }

    .sub-options.active {
        display: block;
        animation: page-in .25s var(--ac-ease-out);
    }

    .sub-options .field {
        margin-bottom: 0;
    }

    /* ===== Cropper 框选框主题适配（樱花粉） ===== */
    .cropper-view-box {
        outline: none;
        border-radius: 6px;
        box-shadow: 0 0 0 2px var(--ac-pink-500);
    }

    .cropper-face {
        background-color: #fff;
        opacity: .15;
        border-radius: 6px;
    }

    .cropper-modal {
        background-color: var(--ac-ink-900);
        opacity: .45;
    }

    .cropper-line {
        background-color: var(--ac-pink-400);
    }

    .cropper-dashed {
        border-color: rgba(255, 255, 255, .55);
        opacity: .6;
    }

    .cropper-center::before,
    .cropper-center::after {
        background-color: var(--ac-pink-300);
    }

    .cropper-point {
        background-color: var(--ac-pink-500);
        border: 1.5px solid #fff;
        border-radius: 50%;
        height: 10px;
        width: 10px;
        opacity: 1;
        box-shadow: 0 1px 4px rgba(50, 41, 49, .3);
    }

    .cropper-point.point-e {
        margin-top: -5px;
        right: -5px;
    }

    .cropper-point.point-n {
        margin-left: -5px;
        top: -5px;
    }

    .cropper-point.point-w {
        left: -5px;
        margin-top: -5px;
    }

    .cropper-point.point-s {
        bottom: -5px;
        left: 50%;
        margin-left: -5px;
    }

    .cropper-point.point-ne {
        right: -5px;
        top: -5px;
    }

    .cropper-point.point-nw {
        left: -5px;
        top: -5px;
    }

    .cropper-point.point-sw {
        bottom: -5px;
        left: -5px;
    }

    .cropper-point.point-se {
        bottom: -5px;
        height: 16px;
        right: -5px;
        width: 16px;
        opacity: 1;
    }

    /* 裁剪区 */
    .cropper-wrap {
        display: none;
        margin-bottom: 1.3rem;
    }

    .cropper-wrap.active {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 1.2rem;
    }

    .cropper-col {
        display: flex;
        flex-direction: column;
        gap: .6rem;
        min-width: 0;
    }

    .cropper-col .col-label {
        font-size: .82rem;
        font-weight: 600;
        color: var(--ac-ink-500);
    }

    .cropper-container-box {
        border-radius: var(--ac-radius-input);
        overflow: hidden;
        background: var(--ac-bg);
    }

    .cropper-container-box img {
        display: block;
        max-width: 100%;
    }

    .preview-label-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    #preview {
        width: 100%;
        aspect-ratio: 4 / 3;
        border-radius: var(--ac-radius-input);
        overflow: hidden;
        background: var(--ac-bg);
        border: 1.5px solid var(--ac-ink-100);
    }

    .cropper-actions {
        display: flex;
        flex-direction: column;
        gap: .6rem;
    }

    /* 提交区 */
    .submit-wrap {
        display: none;
        margin-bottom: 1.3rem;
    }

    .submit-wrap.active {
        display: block;
    }

    .preview-box {
        display: none;
        margin-top: 1rem;
        text-align: center;
    }

    .preview-box.active {
        display: block;
    }

    .preview-box img {
        max-width: 260px;
        border-radius: var(--ac-radius-input);
        box-shadow: var(--ac-shadow-card);
        margin: 0 auto;
    }

    /* 加载 */
    .loading-wrap {
        display: none;
        flex-direction: column;
        align-items: center;
        gap: .8rem;
        padding: 2rem 0;
        margin-bottom: 1.3rem;
        text-align: center;
    }

    .loading-wrap.active {
        display: flex;
    }

    .loading-wrap img {
        width: 72px;
        height: 72px;
        object-fit: contain;
    }

    .loading-wrap .loading-text {
        font-weight: 700;
        color: var(--ac-pink-500);
        font-family: var(--ac-font-display);
    }

    .loading-wrap .progress-hint {
        font-size: .88rem;
        color: var(--ac-ink-500);
    }

    /* 结果 */
    .result-wrap {
        display: none;
    }

    .result-wrap.active {
        display: block;
    }

    .result-card {
        padding: 1.6rem;
    }

    .result-top {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: .6rem;
        margin-bottom: .2rem;
    }

    .result-name {
        font-family: var(--ac-font-display);
        font-size: 1.5rem;
        font-weight: 800;
        color: var(--ac-ink-900);
        margin-right: .2rem;
    }

    .result-link {
        font-size: .88rem;
    }

    .result-confidence {
        color: var(--ac-ink-500);
        font-size: .92rem;
        margin-bottom: 1.2rem;
    }

    .result-confidence .mono {
        color: var(--ac-pink-600);
        font-weight: 700;
    }

    .prob-list {
        display: flex;
        flex-direction: column;
        gap: .7rem;
    }

    .prob-item {
        display: flex;
        align-items: center;
        gap: .8rem;
    }

    .prob-item .name {
        flex: 0 0 7.5em;
        font-weight: 600;
        font-size: .92rem;
        color: var(--ac-ink-900);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .prob-item .prob-bar {
        flex: 1;
    }

    .prob-item .pct {
        flex: 0 0 4.2em;
        text-align: right;
        font-family: var(--ac-font-mono);
        font-size: .85rem;
        color: var(--ac-ink-700);
    }

    .result-error {
        text-align: center;
        color: var(--ac-danger);
        padding: 1.5rem;
    }

    @media (max-width: 720px) {
        .cropper-wrap.active {
            grid-template-columns: 1fr;
        }

        .prob-item .name {
            flex-basis: 5.5em;
        }
    }
</style>

<div class="upload-page ac-container">
    <div class="page-head">
        <h2>上传识别</h2>
        <p>支持 JPG / PNG，最大 10MB，可拖拽上传。</p>
    </div>

    <div class="card upload-card">
        <div class="upload-area" id="uploadArea">
            <input type="file" id="fileInput" accept="image/jpeg,image/png" hidden />
            <div class="ua-icon"><i class="ph ph-cloud-arrow-up"></i></div>
            <div class="ua-title">点击选择或拖拽图片到这里</div>
            <div class="ua-sub">识别结果通常在几秒内返回</div>
        </div>

        <div class="link-divider"><span>或粘贴图片链接</span></div>
        <div class="link-row">
            <input type="url" id="linkInput" class="input" placeholder="https://example.com/image.jpg" />
            <button type="button" class="btn btn-secondary" id="btnLoadLink">加载图片</button>
        </div>
    </div>

    <!-- 识别模型选择 -->
    <fieldset class="option-group" id="recognitionGroup" disabled>
        <legend>识别模型</legend>
        <div class="group-body">
            <div class="field">
                <label for="recognitionType">推理模型</label>
                <select id="recognitionType" class="select">
                    <option value="auto" selected>自动选择（推荐）</option>
                    <option value="local">37ac模型（快速识别）</option>
                    <option value="llm">大体量多模态模型（精度更高）</option>
                </select>
                <span class="hint">37ac模型速度快；大体量多模态模型精度更高；自动模式由节点根据配置选择。</span>
            </div>
        </div>
    </fieldset>

    <!-- 图片处理选项 -->
    <fieldset class="option-group" id="imageProcessingGroup" disabled>
        <legend>图片处理</legend>
        <div class="group-body">
            <label class="checkbox-row" for="enableCrop">
                <input type="checkbox" id="enableCrop" />
                <span>裁剪图片</span>
            </label>
            <div id="cropSubOptions" class="sub-options">
                <div class="field">
                    <label for="cropMode">裁剪模式</label>
                    <select id="cropMode" class="select">
                        <option value="auto">自动裁剪（YOLO 识别边界）</option>
                        <option value="manual">手动裁剪（可视化框选）</option>
                    </select>
                    <span class="hint">自动裁剪将框选图片中的主要人物区域；手动裁剪可自由选择区域。</span>
                </div>
            </div>

            <div style="height:.8rem"></div>

            <label class="checkbox-row" for="enableBackgroundRemoval">
                <input type="checkbox" id="enableBackgroundRemoval" />
                <span>移除背景（高精度抠图）</span>
            </label>
            <div id="backgroundRemovalSubOptions" class="sub-options">
                <span class="hint">仅移除图片背景，保留主体（下载模型可能需要一些时间）。</span>
            </div>
        </div>
    </fieldset>

    <!-- 裁剪器 -->
    <div class="cropper-wrap card" id="cropperWrap">
        <div class="cropper-col">
            <span class="col-label">原图（拖动框选裁剪区域）</span>
            <div class="cropper-container-box">
                <img id="cropperImage" src="" alt="待裁剪图片" />
            </div>
        </div>
        <div class="cropper-col">
            <div class="preview-label-row">
                <span class="col-label">预览</span>
            </div>
            <div id="preview"></div>
            <div class="cropper-actions">
                <button type="button" class="btn btn-primary btn-sm" id="btnCropImage">裁剪图片</button>
                <button type="button" class="btn btn-ghost btn-sm" id="btnCropReset">重置选框</button>
            </div>
        </div>
    </div>

    <!-- 提交 -->
    <div class="submit-wrap card" id="submitWrap">
        <form id="uploadForm">
            <button type="submit" class="btn btn-primary btn-lg btn-block">开始识别</button>
        </form>
        <div class="preview-box" id="previewWrap">
            <img id="previewImage" alt="识别预览" />
        </div>
    </div>

    <!-- 加载状态 -->
    <div class="loading-wrap" id="loadingWrap">
        <img src="https://static.322337.xyz/view.php/2b41dcf3c57aabd59adb77f0c90c6eba.gif" alt="" />
        <p class="loading-text">识别中，请稍候</p>
        <p class="progress-hint" id="progressStatusText">正在上传图片</p>
        <button type="button" class="btn btn-ghost btn-sm" id="btnCancelRequest">取消识别</button>
    </div>

    <!-- 结果 -->
    <div class="result-wrap" id="resultWrap"></div>
</div>

<script type="module">
    import {
        removeBackground
    } from '/static/scripts/vendor/imgly-background-removal.esm.js';

    /**
     * 转义 HTML 特殊字符，防止 XSS
     * @param {string} text
     * @returns {string}
     */
    function escapeHtml(text) {
        if (text == null) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * 二次元图片识别工具（上传 → 处理 → 识别）
     */
    class AnimeDetector {
        constructor() {
            this.initElements();
            this.bindEvents();
            this.state = {
                tempFile: null, // 原始临时文件
                cropInstance: null, // Cropper.js 实例
                croppedFile: null, // 最终裁剪文件
                bgRemovedFile: null, // 最终去背景文件
                originalImageURL: null, // 原图预览 URL
                hasCroppedImage: false, // 是否有裁剪后的图片
                hasBgRemovedImage: false, // 是否有去背景后的图片
            };
            this.abortController = null;
        }

        /* DOM 元素 */
        initElements() {
            this.fileInput = document.getElementById('fileInput');
            this.uploadForm = document.getElementById('uploadForm');
            this.uploadArea = document.getElementById('uploadArea');
            this.resultWrap = document.getElementById('resultWrap');
            this.previewWrap = document.getElementById('previewWrap');
            this.previewImage = document.getElementById('previewImage');
            this.loadingWrap = document.getElementById('loadingWrap');
            this.submitWrap = document.getElementById('submitWrap');

            // 裁剪相关
            this.enableCropCheckbox = document.getElementById('enableCrop');
            this.cropSubOptions = document.getElementById('cropSubOptions');
            this.cropModeSelect = document.getElementById('cropMode');

            // 去背景相关
            this.enableBgRemovalCheckbox = document.getElementById('enableBackgroundRemoval');
            this.bgRemovalSubOptions = document.getElementById('backgroundRemovalSubOptions');

            // 链接上传
            this.linkInput = document.getElementById('linkInput');
            this.btnLoadLink = document.getElementById('btnLoadLink');

            // 选项组
            this.recognitionGroup = document.getElementById('recognitionGroup');
            this.recognitionTypeSelect = document.getElementById('recognitionType');
            this.imageProcessingGroup = document.getElementById('imageProcessingGroup');
        }

        /* 事件绑定 */
        bindEvents() {
            this.uploadArea.addEventListener('click', () => this.fileInput.click());
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
            this.uploadForm.addEventListener('submit', (e) => this.handleSubmit(e));

            // 拖拽上传
            this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));

            // 裁剪选项切换
            this.enableCropCheckbox.addEventListener('change', () => {
                this.cropSubOptions.classList.toggle('active', this.enableCropCheckbox.checked);
                if (!this.enableCropCheckbox.checked) {
                    this.resetCropState();
                }
                this.updateCropMode();
            });

            this.cropModeSelect.addEventListener('change', () => this.updateCropMode());

            // 去背景选项切换
            this.enableBgRemovalCheckbox.addEventListener('change', () => {
                this.bgRemovalSubOptions.classList.toggle('active', this.enableBgRemovalCheckbox.checked);
            });

            // 链接上传
            this.btnLoadLink.addEventListener('click', () => this.handleLinkLoad());
            this.linkInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleLinkLoad();
                }
            });

            // 裁剪按钮
            document.getElementById('btnCropImage').addEventListener('click', () => this.handleCropImage());
            document.getElementById('btnCropReset').addEventListener('click', () => this.handleCropReset());

            // 取消识别按钮
            document.getElementById('btnCancelRequest').addEventListener('click', () => this.cancelRequest());
        }

        /* 链接加载 */
        handleLinkLoad() {
            const url = this.linkInput.value.trim();
            if (!url) {
                Notify.error('请输入图片链接');
                return;
            }
            if (!this.isValidImageUrl(url)) {
                Notify.error('请输入有效的图片链接（支持 http/https）');
                return;
            }
            this.fetchImageFromURL(url);
        }

        /* 校验图片链接是否安全 */
        isValidImageUrl(url) {
            try {
                const u = new URL(url, window.location.href);
                if (u.protocol !== 'http:' && u.protocol !== 'https:') {
                    return false;
                }
                if (u.protocol === 'http:' && window.location.protocol === 'https:') {
                    return false;
                }
                return true;
            } catch (e) {
                return false;
            }
        }

        /* 处理文件选择 */
        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) this.handleFile(file);
        }

        /* 处理拖拽 */
        handleDragOver(event) {
            event.preventDefault();
            this.uploadArea.classList.add('drag-over');
        }

        handleDragLeave(event) {
            event.preventDefault();
            this.uploadArea.classList.remove('drag-over');
        }

        handleDrop(event) {
            event.preventDefault();
            this.uploadArea.classList.remove('drag-over');
            const files = event.dataTransfer.files;
            if (files.length > 0) this.handleFile(files[0]);
        }

        /* 处理图片文件 */
        handleFile(file) {
            if (!file.type.match('image.*')) {
                Notify.error('请选择 JPG 或 PNG 格式的图片');
                return;
            }

            if (file.size > 10 * 1024 * 1024) {
                Notify.error('图片大小不能超过 10MB');
                return;
            }

            this.state.tempFile = file;
            this.resetCropState();
            this.state.hasBgRemovedImage = false;

            // 显示预览，清空上次结果
            this.updatePreview(file);
            this.hideResult();

            // 显示处理选项
            this.recognitionGroup.disabled = false;
            this.imageProcessingGroup.disabled = false;

            // 更新提交按钮状态
            this.updateSubmitButton();
        }

        /* 更新裁剪模式 */
        updateCropMode() {
            const isManual = this.enableCropCheckbox.checked && this.cropModeSelect.value === 'manual';

            if (isManual && this.state.originalImageURL) {
                this.initCropper();
            } else {
                this.destroyCropper();
                if (this.cropModeSelect.value !== 'manual') {
                    this.resetCropState();
                }
            }
        }

        /* 重置裁剪状态 */
        resetCropState() {
            this.state.croppedFile = null;
            this.state.hasCroppedImage = false;
        }

        /* 初始化 Cropper */
        initCropper() {
            if (this.state.cropInstance) return;

            const cropperImage = document.getElementById('cropperImage');
            cropperImage.src = this.state.originalImageURL;

            const cropperWrap = document.getElementById('cropperWrap');
            cropperWrap.classList.add('active');

            this.state.cropInstance = new Cropper(cropperImage, {
                // 不锁定宽高比，允许自由调整选框形状
                preview: '#preview',
                viewMode: 1,
                guides: true,
                center: true,
                highlight: false,
                background: false,
                autoCropArea: 0.8,
                movable: true,
                zoomable: true,
                scalable: true,
                rotatable: true,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
            });
        }

        /* 销毁 Cropper */
        destroyCropper() {
            if (this.state.cropInstance) {
                this.state.cropInstance.destroy();
                this.state.cropInstance = null;
            }
            document.getElementById('cropperWrap').classList.remove('active');
        }

        /* 手动裁剪图片 */
        handleCropImage() {
            if (!this.state.cropInstance) return;

            // 仅指定宽度，高度按选框实际宽高比计算，避免自由形状裁剪时变形
            const canvas = this.state.cropInstance.getCroppedCanvas({
                width: 800,
                minWidth: 256,
                maxWidth: 2048,
                fillColor: '#fff',
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high',
            });

            if (!canvas) {
                Notify.error('裁剪失败，请重试');
                return;
            }

            canvas.toBlob((blob) => {
                if (!blob) {
                    Notify.error('裁剪失败，请重试');
                    return;
                }

                // 生成裁剪后的文件
                const fileName = `cropped_${Date.now()}.png`;
                this.state.croppedFile = new File([blob], fileName, {
                    type: 'image/png'
                });
                this.state.hasCroppedImage = true;

                // 更新预览
                this.updatePreview(this.state.croppedFile);

                Notify.success('裁剪完成');
                this.updateSubmitButton();
            }, 'image/png', 0.9);
        }

        /* 重置裁剪选框 */
        handleCropReset() {
            if (this.state.cropInstance) {
                this.state.cropInstance.reset();
            }
        }

        /* 处理图片（裁剪 + 去背景） */
        async processImage() {
            if (!this.state.tempFile) {
                Notify.error('请先选择图片');
                return null;
            }

            let processedFile = this.state.tempFile;

            try {
                // 去背景
                if (this.enableBgRemovalCheckbox.checked) {
                    this.updateProgressStatus('正在移除背景（首次使用需下载模型，请稍候）');
                    try {
                        // WASM 模型资源自托管，避免走默认 CDN
                        const bgRemovedBlob = await removeBackground(processedFile, {
                            publicPath: 'https://static.322337.xyz/file/package/dist/',
                        });
                        processedFile = new File([bgRemovedBlob], `bg_removed_${Date.now()}.png`, {
                            type: 'image/png'
                        });
                        this.state.bgRemovedFile = processedFile;
                        this.state.hasBgRemovedImage = true;
                    } catch (err) {
                        console.error('背景移除失败:', err);
                        Notify.error('背景移除失败，将使用原图继续识别');
                    }
                }

                // 裁剪（仅在未手动裁剪时执行自动裁剪）
                if (this.enableCropCheckbox.checked &&
                    this.cropModeSelect.value === 'auto' &&
                    !this.state.hasCroppedImage) {
                    // TODO: 实现自动裁剪（YOLO 识别）
                    this.updateProgressStatus('正在自动裁剪图片');
                    await new Promise(resolve => setTimeout(resolve, 500)); // 模拟裁剪耗时
                }

                // 如果已手动裁剪，使用裁剪后的文件
                if (this.state.hasCroppedImage && this.state.croppedFile) {
                    processedFile = this.state.croppedFile;
                }

                return processedFile;
            } catch (err) {
                console.error('图片处理失败:', err);
                Notify.error('图片处理失败: ' + err.message);
                return null;
            }
        }

        /* 更新预览 */
        updatePreview(file) {
            if (this.state.originalImageURL) {
                URL.revokeObjectURL(this.state.originalImageURL);
            }
            this.state.originalImageURL = URL.createObjectURL(file);
            this.previewImage.src = this.state.originalImageURL;
            this.previewWrap.classList.add('active');
        }

        /* 更新进度状态文本 */
        updateProgressStatus(text) {
            const progressText = document.getElementById('progressStatusText');
            if (progressText) {
                progressText.textContent = text;
            }
        }

        /* 更新提交按钮状态 */
        updateSubmitButton() {
            if (this.state.tempFile) {
                this.submitWrap.classList.add('active');
            } else {
                this.submitWrap.classList.remove('active');
            }
        }

        /* 提交识别（流式） */
        async handleSubmit(event) {
            event.preventDefault();

            this.showLoading(true);
            this.hideResult();

            try {
                // 处理图片
                const processedFile = await this.processImage();
                if (!processedFile) {
                    this.showLoading(false);
                    return;
                }

                // 更新预览
                this.updatePreview(processedFile);

                // 构造 FormData（字段名 file 与后端约定一致）
                const formData = new FormData();
                formData.append('file', processedFile);
                // 推理模型选择：local / llm / auto
                formData.append('recognition_type', this.recognitionTypeSelect.value);

                this.updateProgressStatus('正在上传图片');

                // 每次请求新建 AbortController，用于取消上传/识别
                this.abortController = new AbortController();

                // 发送流式请求（经 Nginx + PHP 代理，API Key 由服务端注入）
                // Nginx 多 worker + php-cgi 多进程下长连接不再阻塞其他请求
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-Stream-Response': 'true',
                    },
                    body: formData,
                    signal: this.abortController.signal,
                });

                if (!response.ok) {
                    let errorMessage = '上传失败';
                    let errorDetail = '';

                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.message || errorMessage;
                        errorDetail = errorData.detail || '';
                    } catch (e) {
                        errorMessage = `服务器错误 (${response.status})`;
                    }

                    throw new Error(errorDetail ? `${errorMessage}: ${errorDetail}` : errorMessage);
                }

                // 处理 SSE 流式响应
                // 后端事件格式：{"status":"queued|waiting|processing|completed|failed|error", ...}
                // 完成时携带 result（节点返回的预测结构：label/confidence/class_probs）
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let finalResult = null;
                let streamError = null;
                let streamTimeout = false;
                this.currentTaskId = null; // 记录 task_id，用于 SSE 完成事件丢失时回退查询

                while (true) {
                    const {
                        done,
                        value
                    } = await reader.read();

                    if (done) break;

                    buffer += decoder.decode(value, {
                        stream: true
                    });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // 保留不完整的行

                    for (const line of lines) {
                        const trimmed = line.trim();

                        if (!trimmed) continue;

                        // 忽略 SSE 注释行（heartbeat 等）
                        if (trimmed.startsWith(':')) continue;

                        if (trimmed.startsWith('data: ')) {
                            try {
                                const jsonData = JSON.parse(trimmed.slice(6));
                                this.handleStreamEvent(jsonData);

                                // 最终结果
                                if (jsonData.status === 'completed' && jsonData.result) {
                                    finalResult = jsonData.result;
                                }

                                // 失败 / 错误
                                if (jsonData.status === 'failed' || jsonData.status === 'error') {
                                    streamError = jsonData.message || '识别过程中发生错误';
                                    break;
                                }

                                // 等待超时：标记但不视为失败，流结束后给出提示而非报错
                                if (jsonData.status === 'timeout') {
                                    streamError = null;
                                    streamTimeout = true;
                                }
                            } catch (e) {
                                console.error('解析流数据失败:', e);
                            }
                        }
                    }

                    if (streamError) break;
                }

                // 处理流结束后可能残留的一行数据
                if (buffer.trim()) {
                    const trimmed = buffer.trim();
                    if (!trimmed.startsWith(':') && trimmed.startsWith('data: ')) {
                        try {
                            const jsonData = JSON.parse(trimmed.slice(6));
                            this.handleStreamEvent(jsonData);
                            if (jsonData.status === 'completed' && jsonData.result) {
                                finalResult = jsonData.result;
                            }
                            if (jsonData.status === 'failed' || jsonData.status === 'error') {
                                streamError = jsonData.message || '识别过程中发生错误';
                            }
                            if (jsonData.status === 'timeout') {
                                streamError = null;
                                streamTimeout = true;
                            }
                        } catch (e) {
                            console.error('解析流数据失败:', e);
                        }
                    }
                }

                // 处理最终结果
                if (streamError) {
                    throw new Error(streamError);
                }
                if (finalResult) {
                    this.showResult(finalResult);
                } else if (streamTimeout) {
                    // 等待超时但任务可能仍在后台处理：提示用户稍后查询，而非误报失败
                    this.updateProgressStatus('识别时间较长，任务仍在后台处理中');
                    this.showError('等待超时，任务仍在后台处理中，请稍后刷新页面查看结果。若长时间无结果，请检查节点是否在线。');
                } else {
                    // 流正常结束但未收到结果：多为 SSE 完成事件经代理丢失。
                    // 结果其实已保存在数据库，回退查询 /api/tasks/{task_id}，避免误报失败。
                    await this.recoverResult();
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    this.updateProgressStatus('识别已取消');
                    this.showError('识别已取消');
                } else {
                    console.error('识别请求失败:', error);
                    this.showError(error.message || '网络连接失败，请检查网络后重试');
                }
            } finally {
                this.showLoading(false);
                this.abortController = null;
            }
        }

        /* 处理流式事件（后端按 status 字段推送状态） */
        handleStreamEvent(eventData) {
            const status = eventData.status;
            const message = eventData.message || '';
            // 记录 task_id（queued 事件最先携带），供完成事件丢失时回退查询
            if (eventData.task_id) {
                this.currentTaskId = eventData.task_id;
            }
            // 在函数顶部统一声明，避免 switch case 内重复 const 声明（ES 语法限制）
            let timeoutSec = 0;
            let retryIn = 0;

            switch (status) {
                case 'queued':
                    // 携带预估等待上限（后端按识别方式计算），供用户参考
                    timeoutSec = eventData.timeout || 0;
                    this.updateProgressStatus(timeoutSec ?
                        `任务已提交，等待推理（最长等待约 ${Math.round(timeoutSec / 60)} 分钟）...` :
                        '任务已提交，等待推理...');
                    break;

                case 'waiting':
                    // 无空闲节点排队中：显示预计重试间隔，提示节点上线后自动分发
                    retryIn = eventData.retry_in || 0;
                    this.updateProgressStatus(retryIn > 0 ?
                        `${message || '没有空闲节点，任务排队中'}（约 ${retryIn} 秒后自动重试，节点上线即分发）` :
                        (message || '没有空闲节点，任务排队中...'));
                    break;

                case 'assigned':
                    this.updateProgressStatus('任务已分配，等待识别');
                    break;

                case 'processing':
                    this.updateProgressStatus('正在识别图片');
                    break;

                case 'completed':
                    this.updateProgressStatus('识别完成');
                    break;

                case 'failed':
                case 'error':
                    this.updateProgressStatus(message || '识别失败');
                    break;

                case 'timeout':
                    // 等待超时：任务可能仍在后端处理中，提示用户稍后查询而非误报失败
                    this.updateProgressStatus(message || '等待时间较长，任务仍在后台处理中');
                    break;
            }
        }

        /* 显示加载状态 */
        showLoading(show) {
            if (show) {
                this.loadingWrap.classList.add('active');
            } else {
                this.loadingWrap.classList.remove('active');
            }
        }

        /* 显示结果（所有 API 返回文本均经 escapeHtml 转义） */
        showResult(data) {
            // 节点结果失败（模型缺失、图片损坏等）
            if (!data || data.success === false || data.error) {
                this.showError((data && data.error) || '识别失败，请稍后重试');
                return;
            }
            this.resultWrap.innerHTML = this.generateResultHTML(data);
            this.resultWrap.classList.add('active');
        }

        /* 生成结果 HTML（兼容节点返回结构：label/confidence(0-100)/class_probs/recognition_type） */
        generateResultHTML(data) {
            // 置信度：API 明确使用 0-100 表示百分数，直接使用无需换算
            const toPercent = (v) => Number(v) || 0;
            const rawConfidence = Number(data.confidence) || 0;

            const topCharacters = data.top_characters || (data.class_probs || []).map(p => ({
                name: p.name,
                probability: toPercent(Number(p.prob) || 0),
            }));
            // label 格式为「作品名/角色名」（角色IP/角色名），拆分为 IP 与角色名分别展示
            const labelParts = (data.label || '').split('/').map(s => s.trim()).filter(Boolean);
            const characterIP = labelParts[0] || '未知作品';
            const characterName = labelParts[1] || labelParts[0] || '未知角色';
            const from_source = (data.from_source !== undefined) ?
                data.from_source :
                (data.recognition_type === 'llm' ? 1 : 0);
            const confidence = toPercent(rawConfidence).toFixed(2);

            let html = '<div class="card result-card">';
            html += '<div class="result-top">';
            html += `<span class="result-name">${escapeHtml(characterName)}</span>`;
            if (characterIP && characterIP !== characterName) {
                html += `<span class="badge badge-neutral">${escapeHtml(characterIP)}</span>`;
            }
            if (characterName !== '未知角色') {
                html += `<a class="result-link" href="https://zh.moegirl.org.cn/${encodeURIComponent(characterName)}" target="_blank" rel="nofollow">萌娘百科</a>`;
            }
            html += `<span class="badge ${from_source === 0 ? 'badge-pink' : 'badge-mint'}">${from_source === 0 ? '37ac模型' : '大模型'}</span>`;
            html += '</div>';
            html += `<div class="result-confidence">置信度 <span class="mono">${confidence}%</span></div>`;

            // 前 5 高概率角色
            if (topCharacters.length > 0) {
                html += '<div class="prob-list">';
                topCharacters.slice(0, 5).forEach((item) => {
                    html += this.generateProbabilityItem(item);
                });
                html += '</div>';
            }

            html += '</div>';
            return html;
        }

        /* 生成概率条目 HTML */
        generateProbabilityItem(item) {
            // 兼容 {name, probability(0-100)} 与节点 {name, prob(0-100)}，均按 0-100 处理
            const raw = Number(item.probability ?? item.prob) || 0;
            const percentage = raw.toFixed(2);
            return `
                <div class="prob-item">
                    <span class="name">${escapeHtml(item.name)}</span>
                    <span class="prob-bar"><i style="width:${percentage}%"></i></span>
                    <span class="pct">${percentage}%</span>
                </div>
            `;
        }

        /* 显示错误 */
        showError(message) {
            const html = `
                <div class="card result-error">
                    识别失败：${escapeHtml(message)}
                </div>
            `;
            this.resultWrap.innerHTML = html;
            this.resultWrap.classList.add('active');
            Notify.error(message);
        }

        /* 隐藏结果 */
        hideResult() {
            this.resultWrap.classList.remove('active');
        }

        /* 回退查询任务结果：SSE 完成事件丢失时，轮询 /api/tasks/{task_id} 获取已保存的结果 */
        async recoverResult() {
            if (!this.currentTaskId) {
                throw new Error('未收到识别结果');
            }
            const taskId = this.currentTaskId;
            this.updateProgressStatus('正在获取识别结果...');

            // 最多轮询若干次，间隔递增：结果已在数据库，短时内即可查询到
            const maxAttempts = 6;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    const resp = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        const result = data && data.result;
                        // 完成且带结果 → 展示
                        if (result && data.status === 'completed') {
                            this.showResult(result);
                            return;
                        }
                        // 明确失败 / 错误 → 直接抛出对应提示
                        if (data.status === 'failed' || data.status === 'error') {
                            throw new Error(data.message || '识别失败，请稍后重试');
                        }
                        // pending / 尚无结果 → 继续轮询
                    }
                } catch (e) {
                    // 网络瞬时错误可重试；业务错误直接上抛
                    if (e && e.message && e.message !== '未收到识别结果' && e.message !== 'Failed to fetch') {
                        throw e;
                    }
                }
                await new Promise(resolve => setTimeout(resolve, 1500 * attempt));
            }

            // 轮询结束仍未拿到结果：提示稍后刷新查询，而非误报失败
            this.updateProgressStatus('识别时间较长，任务仍在后台处理中');
            this.showError('识别结果暂未返回，任务可能仍在后台处理中，请稍后刷新页面查看结果。若长时间无结果，请检查节点是否在线。');
        }

        /* 从 URL 获取图片 */
        async fetchImageFromURL(url) {
            try {
                // 校验 URL 格式
                if (!this.isValidImageUrl(url)) {
                    Notify.error('请输入有效的图片链接（支持 http/https）');
                    return;
                }

                this.showLoading(true);
                this.updateProgressStatus('正在从链接加载图片');

                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`无法加载图片 (${response.status})`);
                }

                const blob = await response.blob();
                if (!blob.type.match('image.*')) {
                    throw new Error('链接返回的不是图片文件');
                }

                const fileName = `url_image_${Date.now()}.${blob.type.split('/')[1]}`;
                const file = new File([blob], fileName, {
                    type: blob.type
                });

                this.state.tempFile = file;
                this.resetCropState();
                this.state.hasBgRemovedImage = false;

                // 显示预览，清空上次结果
                this.updatePreview(file);
                this.hideResult();

                // 显示处理选项
                this.recognitionGroup.disabled = false;
                this.imageProcessingGroup.disabled = false;

                // 更新提交按钮状态
                this.updateSubmitButton();
                Notify.success('图片加载完成');
            } catch (err) {
                console.error('从链接加载图片失败:', err);
                Notify.error('无法从链接加载图片: ' + err.message);
            } finally {
                this.showLoading(false);
            }
        }

        /* 取消请求 */
        cancelRequest() {
            if (this.abortController) {
                this.abortController.abort();
                this.abortController = null;
            }
        }

        /* 销毁资源 */
        destroy() {
            if (this.state.originalImageURL) {
                URL.revokeObjectURL(this.state.originalImageURL);
            }
            this.destroyCropper();
            this.cancelRequest();
        }
    }

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {
        const detector = new AnimeDetector();

        // 页面卸载时清理资源
        window.addEventListener('beforeunload', () => detector.destroy());
    });
</script>

<?php
require_once ROOT_PATH . '/views/footer.php';
?>