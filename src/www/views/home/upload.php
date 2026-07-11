<?php
require_once ROOT_PATH . '/views/layout.php';
?>
<div class="anime-detector-container">
    <h2>上传图片，识别二次元角色</h2>

    <!-- 文件上传区域 -->
    <div class="upload-section">
        <div class="file-input-wrapper">
            <label for="fileInput" class="file-input-label">
                <?php require ROOT_PATH . '/views/components/icons/upload.php'; ?>
                <span>选择图片文件</span>
            </label>
            <input type="file" id="fileInput" accept="image/jpeg,image/png" class="file-input" />
            <p class="file-hint">支持 JPG、PNG 格式，最大 10MB</p>
        </div>
    </div>

    <!-- 处理区域 -->
    <div id="cropContainer" class="crop-container">
        <!-- 导航栏 -->
        <div class="crop-navigation">
            <div class="nav-tabs">
                <button class="nav-tab active" data-mode="quick">快速模式</button>
                <button class="nav-tab" data-mode="advanced">高级模式</button>
            </div>
        </div>

        <!-- ======== 快速模式：默认 auto，直接裁剪识别 ======== -->
        <div id="quickLayout">
            <div class="crop-layout">
                <div class="crop-main">
                    <h3>快速识别</h3>
                    <div class="image-wrapper">
                        <img id="imagePreview" src="#" alt="裁剪预览" class="crop-image" />
                    </div>
                </div>
                <div class="crop-preview-section">
                    <h3>预览</h3>
                    <div id="cropPreview" class="preview-box"></div>
                    <p class="preview-hint">实时预览</p>
                </div>
            </div>
        </div>

        <!-- ======== 高级模式：自定义识别 + 角色框选/去背景 ======== -->
        <div id="advancedLayout" class="advanced-layout" style="display: none;">
            <div class="advanced-grid">
                <!-- 左列：识别方式 -->
                <div class="advanced-left">
                    <fieldset class="recognition-type-selector">
                        <legend>识别方式</legend>
                        <label>
                            <input type="radio" name="recognitionType" value="auto" checked>
                            <span>自动选择</span>
                        </label>
                        <label>
                            <input type="radio" name="recognitionType" value="local">
                            <span>37ac模型 <small>快速识别</small></span>
                        </label>
                        <label>
                            <input type="radio" name="recognitionType" value="llm">
                            <span>大模型 API <small>多模态模型-深度思考</small></span>
                        </label>
                    </fieldset>

                    <!-- 角色框选（仅在高级模式显示） -->
                    <fieldset class="remove-bg-method-selector">
                        <legend>角色框选</legend>
                        <label>
                            <input type="radio" name="removeBgMethod" value="canvas" checked>
                            <span>快速框选 <small>即时，适合纯色背景</small></span>
                        </label>
                        <label>
                            <input type="radio" name="removeBgMethod" value="ai">
                            <span>AI 去背景 <small>深度学习，高质量</small></span>
                        </label>
                    </fieldset>

                    <button id="removeBgBtn" class="btn btn-secondary" style="width:100%;">开始框选角色</button>
                    <div class="progress" id="progressContainer" style="display: none;">
                        <div class="progress-bar" id="progressBar"></div>
                    </div>
                </div>

                <!-- 右列：预览 -->
                <div class="advanced-right">
                    <div class="image-box">
                        <h4 id="imageTitle">待处理</h4>
                        <div class="image-wrapper">
                            <img id="mainImage" src="#" alt="处理后图片" class="bg-image" />
                            <canvas id="bboxOverlay" class="bbox-overlay"></canvas>
                            <div class="image-placeholder" id="imagePlaceholder">
                                <p>请先上传图片</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="crop-controls">
            <button id="confirmCropBtn" class="btn btn-primary">确认识别</button>
            <button id="cancelCropBtn" class="btn btn-secondary">取消</button>
        </div>
    </div>

    <!-- 加载状态 -->
    <div id="loadingSpinner" class="loading-spinner">
        <div class="spinner">
            <img src="https://static.322337.xyz/view.php/2b41dcf3c57aabd59adb77f0c90c6eba.gif" />
        </div>
        <p>正在识别中，请稍候...</p>
    </div>

    <!-- 结果展示 -->
    <div id="result" class="result-container"></div>
</div>

<style>
    .anime-detector-container {
        max-width: 900px;
        margin: 0 auto;
        padding: var(--pico-spacing);
    }

    .upload-section {
        background: var(--pico-card-sectioning-background-color);
        border: var(--pico-border-width) dashed var(--pico-form-element-border-color);
        border-radius: var(--pico-border-radius);
        padding: calc(var(--pico-spacing) * 1.5);
        text-align: center;
        margin-bottom: var(--pico-spacing);
        transition: all var(--pico-transition);
        position: relative;
    }

    .upload-section:hover {
        border-color: var(--pico-primary);
        background: var(--pico-form-element-background-color);
    }

    .upload-section.drag-over {
        border-color: var(--pico-primary);
        background-color: var(--pico-primary-focus);
        transform: scale(1.02);
        box-shadow: var(--pico-card-box-shadow);
    }

    .upload-section.drag-invalid {
        border-color: var(--pico-form-element-invalid-border-color);
        background-color: var(--pico-form-element-invalid-background-color);
    }

    .upload-section .icon {
        font-size: 1.2em;
        margin-right: 0.5rem;
    }

    .upload-section div .icon {
        width: 1.2em;
        height: auto;
        margin-right: 0.5rem;
        vertical-align: middle;
    }

    .file-input-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: calc(var(--pico-spacing) * 0.5);
    }

    .file-input-label {
        display: inline-flex;
        align-items: center;
        gap: calc(var(--pico-spacing) * 0.25);
        padding: var(--pico-form-element-spacing-vertical) var(--pico-form-element-spacing-horizontal);
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        border-radius: var(--pico-border-radius);
        cursor: pointer;
        transition: background var(--pico-transition);
        font-weight: var(--pico-font-weight);
    }

    .file-input-label:hover {
        background: var(--pico-primary-hover-background);
    }

    .file-input {
        display: none;
    }

    .file-hint {
        color: var(--pico-muted-color);
        font-size: 0.875em;
        margin: 0;
    }

    .crop-container {
        display: none;
        background: var(--pico-card-background-color);
        border: var(--pico-border-width) solid var(--pico-card-border-color);
        border-radius: var(--pico-border-radius);
        padding: var(--pico-spacing);
        margin-bottom: var(--pico-spacing);
        box-shadow: var(--pico-card-box-shadow);
    }

    /* 新增导航栏样式 */
    .crop-navigation {
        margin-bottom: calc(var(--pico-spacing) * 0.5);
        border-bottom: var(--pico-border-width) solid var(--pico-muted-border-color);
    }

    .nav-tabs {
        display: flex;
        gap: 0;
    }

    .nav-tab {
        padding: var(--pico-form-element-spacing-vertical) var(--pico-form-element-spacing-horizontal);
        border: none;
        background: none;
        cursor: pointer;
        font-size: var(--pico-font-size);
        font-weight: var(--pico-font-weight);
        color: var(--pico-muted-color);
        border-bottom: var(--pico-border-width) solid transparent;
        transition: all var(--pico-transition);
    }

    .nav-tab:hover {
        color: var(--pico-primary);
        background-color: var(--pico-card-sectioning-background-color);
    }

    .nav-tab.active {
        color: var(--pico-primary);
        border-bottom-color: var(--pico-primary-border);
        background-color: var(--pico-card-background-color);
    }

    .crop-layout {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: var(--pico-spacing);
        align-items: start;
    }

    .crop-main h3,
    .crop-preview-section h3 {
        margin-bottom: calc(var(--pico-spacing) * 0.5);
        color: var(--pico-h3-color);
        font-size: var(--pico-h3-font-size, 1.5rem);
        font-weight: var(--pico-h3-font-weight, bold);
    }

    .image-wrapper {
        border: var(--pico-border-width) solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
        overflow: hidden;
        max-width: 500px;
        position: relative;
        min-height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--pico-card-sectioning-background-color);
    }

    .crop-image {
        max-width: 100%;
        max-height: 400px;
        height: auto;
        display: block;
    }

    .bg-image {
        max-width: 100%;
        max-height: 400px;
        width: auto;
        height: auto;
        display: block;
        object-fit: contain;
        transition: opacity 0.25s ease;
    }

    .bg-image.fade-out {
        opacity: 0;
    }

    .bbox-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 10;
    }

    .preview-box {
        width: 120px;
        height: 120px;
        border: var(--pico-border-width) solid var(--pico-primary-border);
        border-radius: var(--pico-border-radius);
        overflow: hidden;
        background: var(--pico-card-sectioning-background-color);
    }

    .preview-hint {
        font-size: 0.75em;
        color: var(--pico-muted-color);
        margin-top: calc(var(--pico-spacing) * 0.25);
    }

    /* 高级模式样式 */
    .advanced-layout {
        width: 100%;
    }

    .advanced-grid {
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: var(--pico-spacing);
        align-items: start;
    }

    .advanced-left {
        display: flex;
        flex-direction: column;
        gap: var(--pico-spacing);
    }

    .advanced-right {
        min-width: 0;
    }

    .image-box {
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .image-box h4 {
        margin-bottom: calc(var(--pico-spacing) * 0.25);
        color: var(--pico-h4-color);
        font-size: var(--pico-h4-font-size, 1.25rem);
        font-weight: var(--pico-h4-font-weight, bold);
    }

    .image-placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
        color: var(--pico-muted-color);
        font-size: 0.875em;
        text-align: center;
        padding: var(--pico-spacing);
    }

    .recognition-type-selector,
    .remove-bg-method-selector {
        margin: 0;
        padding: calc(var(--pico-spacing) * 0.5);
        border: var(--pico-border-width) solid var(--pico-muted-border-color);
        border-radius: var(--pico-border-radius);
    }

    .recognition-type-selector legend,
    .remove-bg-method-selector legend {
        font-weight: var(--pico-font-weight);
        margin-bottom: calc(var(--pico-spacing) * 0.25);
    }

    .recognition-type-selector label,
    .remove-bg-method-selector label {
        display: flex;
        align-items: center;
        gap: calc(var(--pico-spacing) * 0.25);
        cursor: pointer;
        padding: calc(var(--pico-spacing) * 0.15) calc(var(--pico-spacing) * 0.25);
    }

    .recognition-type-selector label:hover,
    .remove-bg-method-selector label:hover {
        background: var(--pico-card-sectioning-background-color);
        border-radius: var(--pico-border-radius);
    }

    .progress {
        width: 100%;
        height: 20px;
        background-color: var(--pico-progress-background-color);
        border-radius: var(--pico-border-radius);
        margin: calc(var(--pico-spacing) * 0.375) 0;
        display: none;
    }

    .progress-bar {
        height: 100%;
        background-color: var(--pico-progress-color);
        border-radius: var(--pico-border-radius);
        width: 0%;
        transition: width var(--pico-transition);
    }

    .crop-controls {
        display: flex;
        gap: calc(var(--pico-spacing) * 0.5);
        justify-content: center;
        margin-top: calc(var(--pico-spacing) * 0.5);
        padding-top: calc(var(--pico-spacing) * 0.5);
        border-top: var(--pico-border-width) solid var(--pico-muted-border-color);
    }

    .action-section {
        text-align: center;
        margin: var(--pico-spacing) 0;
    }

    .btn {
        padding: var(--pico-form-element-spacing-vertical) var(--pico-form-element-spacing-horizontal);
        border: var(--pico-border-width) solid transparent;
        border-radius: var(--pico-border-radius);
        font-size: 1rem;
        font-weight: var(--pico-font-weight);
        cursor: pointer;
        transition: all var(--pico-transition);
        min-width: 140px;
    }

    .btn-primary {
        background: var(--pico-primary-background);
        color: var(--pico-primary-inverse);
        border-color: var(--pico-primary-border);
    }

    .btn-primary:hover:not(:disabled) {
        background: var(--pico-primary-hover-background);
        border-color: var(--pico-primary-hover-border);
    }

    .btn-primary:disabled {
        background: var(--pico-secondary-background);
        cursor: not-allowed;
        opacity: var(--pico-form-element-disabled-opacity);
    }

    .btn-secondary {
        background: var(--pico-secondary-background);
        color: var(--pico-secondary-inverse);
        border-color: var(--pico-secondary-border);
    }

    .btn-secondary:hover {
        background: var(--pico-secondary-hover-background);
        border-color: var(--pico-secondary-hover-border);
    }

    .loading-spinner {
        display: none;
        text-align: center;
        padding: calc(var(--pico-spacing) * 2);
    }

    .spinner {
        width: 40px;
        height: 40px;
        margin: 0 auto calc(var(--pico-spacing) * 0.5);
    }

    .result-container {
        margin-top: var(--pico-spacing);
        padding: var(--pico-spacing);
        background: var(--pico-card-sectioning-background-color);
        border-radius: var(--pico-border-radius);
        display: none;
    }

    .result-show {
        display: block;
        animation: fadeIn 0.5s ease;
    }

    .recognition-badge {
        margin: calc(var(--pico-spacing) * 0.25) 0;
        font-size: 0.875rem;
    }

    .recognition-badge .badge {
        font-size: 0.8rem;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }

        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @media (max-width: 768px) {

        .crop-layout,
        .advanced-grid {
            grid-template-columns: 1fr;
            gap: calc(var(--pico-spacing) * 0.5);
        }

        .preview-box {
            width: 80px;
            height: 80px;
        }

        .crop-controls {
            flex-direction: column;
        }

        .btn {
            width: 100%;
        }

        .nav-tabs {
            flex-direction: column;
        }

        .nav-tab {
            text-align: left;
            border-bottom: var(--pico-border-width) solid var(--pico-muted-border-color);
            border-right: none;
        }

        .nav-tab.active {
            border-bottom-color: var(--pico-muted-border-color);
            border-left: var(--pico-border-width) solid var(--pico-primary-border);
        }

        .image-wrapper {
            min-height: 150px;
        }

        .bg-image {
            max-height: 300px;
        }
    }
</style>

<script type="module">
    import {
        removeBackground
    } from 'https://cdn.jsdelivr.net/npm/@imgly/background-removal@1.7.0/+esm';

    class AnimeDetector {
        constructor() {
            this.elements = this.initializeElements();
            this.state = this.initializeState();
            this.initEventListeners();
        }

        // ========== 初始化方法 ==========

        initializeElements() {
            return {
                fileInput: document.getElementById('fileInput'),
                imagePreview: document.getElementById('imagePreview'),
                mainImage: document.getElementById('mainImage'),
                cropContainer: document.getElementById('cropContainer'),
                quickLayout: document.getElementById('quickLayout'),
                advancedLayout: document.getElementById('advancedLayout'),
                cropPreview: document.getElementById('cropPreview'),
                confirmCropBtn: document.getElementById('confirmCropBtn'),
                cancelCropBtn: document.getElementById('cancelCropBtn'),
                removeBgBtn: document.getElementById('removeBgBtn'),
                bboxOverlay: document.getElementById('bboxOverlay'),
                loadingSpinner: document.getElementById('loadingSpinner'),
                resultDiv: document.getElementById('result'),
                progressContainer: document.getElementById('progressContainer'),
                progressBar: document.getElementById('progressBar'),
                imagePlaceholder: document.getElementById('imagePlaceholder'),
                imageTitle: document.getElementById('imageTitle')
            };
        }

        initializeState() {
            return {
                cropper: null,
                originalFile: null,
                isUploading: false,
                currentMode: 'quick' // 'quick' 或 'advanced'
            };
        }

        // ========== 事件监听器 ==========

        initEventListeners() {
            // 文件选择事件
            this.elements.fileInput.addEventListener('change', (event) => {
                this.handleFileSelect(event);
            });

            // 导航标签切换
            this.setupNavTabs();

            // 裁剪相关按钮
            this.setupCropButtons();

            // 背景去除按钮
            this.setupRemoveBgButton();

            // 拖放功能
            this.setupDragAndDrop();
        }

        setupNavTabs() {
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.addEventListener('click', async (e) => {
                    await this.switchMode(e.target.dataset.mode);
                });
            });
        }

        setupCropButtons() {
            this.elements.confirmCropBtn.addEventListener('click', () => {
                this.handleCropConfirm();
            });

            this.elements.cancelCropBtn.addEventListener('click', () => {
                this.handleCropCancel();
            });
        }

        setupRemoveBgButton() {
            this.elements.removeBgBtn.addEventListener('click', () => {
                this.handleRemoveBackground();
            });

            // 监听框选/去背景方式切换，更新按钮文字
            document.querySelectorAll('input[name="removeBgMethod"]').forEach(radio => {
                radio.addEventListener('change', () => {
                    const method = document.querySelector('input[name="removeBgMethod"]:checked').value;
                    this.elements.removeBgBtn.textContent = method === 'canvas' ? '开始框选角色' : '开始去除背景';
                });
            });
        }

        setupDragAndDrop() {
            const uploadSection = document.querySelector('.upload-section');

            // 阻止默认拖放行为
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadSection.addEventListener(eventName, this.preventDefaults, false);
            });

            // 拖入/拖过：高亮边框
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadSection.addEventListener(eventName, () => {
                    uploadSection.classList.add('drag-over');
                }, false);
            });

            // 拖出/放下：取消高亮
            ['dragleave', 'drop'].forEach(eventName => {
                uploadSection.addEventListener(eventName, () => {
                    uploadSection.classList.remove('drag-over');
                }, false);
            });

            // 放下文件处理
            uploadSection.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const file = files[0];
                    this.handleDroppedFile(file);
                }
            }, false);
        }

        // ========== 工具方法 ==========

        preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        isValidImageFile(file) {
            if (!file) return false;

            const allowedMimeTypes = ['image/jpeg', 'image/jpg', 'image/png'];
            const maxSize = 10 * 1024 * 1024; // 10MB

            const isAllowedType = allowedMimeTypes.includes(file.type);
            const isWithinSizeLimit = file.size <= maxSize;

            return isAllowedType && isWithinSizeLimit;
        }

        canvasToBlob(canvas) {
            return new Promise((resolve) => {
                canvas.toBlob((blob) => {
                    resolve(blob);
                }, 'image/jpeg', 0.92);
            });
        }

        // ========== 模式切换 ==========

        async switchMode(mode) {
            this.state.currentMode = mode;
            this.updateNavTabs(mode);
            this.updateLayoutVisibility(mode);

            if (this.state.originalFile) {
                this.reinitializeViewForCurrentMode();
            }
        }

        updateNavTabs(mode) {
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.mode === mode);
            });
        }

        updateLayoutVisibility(mode) {
            const showQuick = mode === 'quick';
            const showAdvanced = mode === 'advanced';

            this.elements.quickLayout.style.display = showQuick ? 'block' : 'none';
            this.elements.advancedLayout.style.display = showAdvanced ? 'block' : 'none';

            this.updateConfirmButton(mode);
        }

        updateConfirmButton(mode) {
            if (mode === 'quick') {
                this.elements.confirmCropBtn.textContent = '开始识别';
            } else {
                this.elements.confirmCropBtn.textContent = '开始识别（处理后）';
            }
            this.elements.confirmCropBtn.style.display = 'inline-block';
        }

        reinitializeViewForCurrentMode() {
            if (this.state.currentMode === 'quick') {
                this.initCropper();
            } else if (this.state.currentMode === 'advanced') {
                this.setupRemoveBgView();
            }
        }

        // ========== 文件处理 ==========

        handleDroppedFile(file) {
            if (!this.isValidImageFile(file)) {
                this.showDragError();
                return;
            }

            this.state.originalFile = file;
            this.loadImageForProcessing(file);
        }

        showDragError() {
            const uploadSection = document.querySelector('.upload-section');
            uploadSection.classList.add('drag-invalid');
            setTimeout(() => uploadSection.classList.remove('drag-invalid'), 1000);
            this.showError('请选择有效的图片文件（仅支持 JPG、JPEG、PNG 格式，且不超过 10MB）');
        }

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (!this.isValidImageFile(file)) {
                this.showError('请选择有效的图片文件（仅支持 JPG、JPEG、PNG 格式，且不超过 10MB）');
                return;
            }

            this.state.originalFile = file;
            this.loadImageForProcessing(file);
        }

        async loadImageForProcessing(file) {
            const reader = new FileReader();

            reader.onload = async (e) => {
                const imageUrl = e.target.result;
                await this.updateImageViews(imageUrl);
                this.showCropInterface();
                this.reinitializeViewForCurrentMode();
            };

            reader.onerror = () => {
                this.showError('图片读取失败，请重试');
            };

            reader.readAsDataURL(file);
        }

        async updateImageViews(imageUrl) {
            if (this.state.currentMode === 'quick') {
                this.elements.imagePreview.src = imageUrl;
                this.elements.mainImage.src = imageUrl;
            } else if (this.state.currentMode === 'advanced') {
                await this._fadeImageTo(this.elements.mainImage, imageUrl);
                this.resetRemoveBgStatus();
            }
        }

        // ========== 裁剪功能 ==========

        showCropInterface() {
            this.elements.cropContainer.style.display = 'block';
            this.hideResult();
        }

        initCropper() {
            if (this.state.cropper) {
                this.state.cropper.destroy();
            }

            if (this.elements.imagePreview.complete) {
                this.initializeCropperInstance();
            } else {
                this.elements.imagePreview.onload = () => {
                    this.initializeCropperInstance();
                };
            }
        }

        initializeCropperInstance() {
            this.state.cropper = new Cropper(this.elements.imagePreview, {
                aspectRatio: NaN,
                viewMode: 1,
                autoCropArea: 0.8,
                responsive: true,
                preview: this.elements.cropPreview,
                guides: true,
                center: true,
                highlight: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false
            });
        }

        // ========== 背景去除功能 ==========

        setupRemoveBgView() {
            if (this.elements.imageTitle.textContent == '成功') return;

            this.resetRemoveBgStatus();
            this.elements.removeBgBtn.disabled = !this.state.originalFile;
        }

        resetRemoveBgStatus() {
            this._hideBoundingBox();
            this.elements.imageTitle.textContent = '待处理';
            this.elements.imageTitle.style.color = '';
            this.elements.imagePlaceholder.style.display = this.elements.mainImage.src &&
                this.elements.mainImage.src !== '#' ? 'none' : 'flex';
            this.elements.progressContainer.style.display = 'none';
        }

        async handleRemoveBackground() {
            if (!this.state.originalFile || this.state.isUploading) return;

            const method = document.querySelector('input[name="removeBgMethod"]:checked').value;

            try {
                this.startRemoveBgProcess(method);

                let blob;
                if (method === 'canvas') {
                    blob = await this._quickSelectCanvas();
                } else {
                    blob = await this._removeBgAI();
                }

                const url = URL.createObjectURL(blob);
                await this.finishRemoveBgProcess(url, method);

            } catch (error) {
                this.handleRemoveBgError(error, method);
            }
        }

        startRemoveBgProcess(method) {
            this.elements.removeBgBtn.disabled = true;
            this.elements.removeBgBtn.textContent = '处理中...';
            if (method === 'ai') {
                this.elements.progressContainer.style.display = 'block';
                this.elements.progressBar.style.width = '0%';
            }
            this.elements.imagePlaceholder.style.display = 'none';
        }

        // ===== 快速框选：Canvas 色差 + 密度分析 =====

        /**
         * 检测画面主体的包围盒
         * @returns {{x:number, y:number, w:number, h:number}|null}
         */
        async _detectBoundingBox() {
            const img = await this._loadImage(this.state.originalFile);
            const w = img.width,
                h = img.height;

            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);

            const imageData = ctx.getImageData(0, 0, w, h);
            const data = imageData.data;

            // 1) 从四角采样，自动检测主背景色
            const corners = [
                [0, 0],
                [w - 2, 0],
                [0, h - 2],
                [w - 2, h - 2],
                [Math.floor(w / 4), 0],
                [Math.floor(w * 3 / 4), 0],
                [0, Math.floor(h / 4)],
                [w - 2, Math.floor(h / 4)],
            ];
            let sumR = 0,
                sumG = 0,
                sumB = 0,
                cnt = 0;
            for (const [cx, cy] of corners) {
                const idx = (cy * w + cx) * 4;
                sumR += data[idx];
                sumG += data[idx + 1];
                sumB += data[idx + 2];
                cnt++;
            }
            const bgR = Math.round(sumR / cnt),
                bgG = Math.round(sumG / cnt),
                bgB = Math.round(sumB / cnt);

            // 2) 动态阈值
            let varR = 0,
                varG = 0,
                varB = 0;
            for (const [cx, cy] of corners) {
                const idx = (cy * w + cx) * 4;
                varR += (data[idx] - bgR) ** 2;
                varG += (data[idx + 1] - bgG) ** 2;
                varB += (data[idx + 2] - bgB) ** 2;
            }
            const threshold = Math.max(25, Math.min(80,
                Math.round(Math.sqrt((varR + varG + varB) / (cnt * 3)) * 1.5)));

            // 3) 标记前景像素
            const isFg = new Uint8Array(w * h);
            for (let i = 0; i < data.length; i += 4) {
                const idx = i >> 2;
                isFg[idx] = (Math.abs(data[i] - bgR) < threshold &&
                    Math.abs(data[i + 1] - bgG) < threshold &&
                    Math.abs(data[i + 2] - bgB) < threshold) ? 0 : 1;
            }

            // 4) 密度网格
            const GS = 32;
            const cols = Math.ceil(w / GS),
                rows = Math.ceil(h / GS);
            const density = new Float32Array(cols * rows);
            for (let y = 0; y < h; y++)
                for (let x = 0; x < w; x++)
                    if (isFg[y * w + x]) density[Math.floor(y / GS) * cols + Math.floor(x / GS)]++;

            let maxD = 0;
            for (const d of density)
                if (d > maxD) maxD = d;
            if (maxD > 0)
                for (let i = 0; i < density.length; i++) density[i] /= maxD;

            // 5) 包围盒
            const DT = 0.08;
            let minGX = cols,
                maxGX = 0,
                minGY = rows,
                maxGY = 0,
                hasFg = false;
            for (let gy = 0; gy < rows; gy++)
                for (let gx = 0; gx < cols; gx++)
                    if (density[gy * cols + gx] >= DT) {
                        hasFg = true;
                        if (gx < minGX) minGX = gx;
                        if (gx > maxGX) maxGX = gx;
                        if (gy < minGY) minGY = gy;
                        if (gy > maxGY) maxGY = gy;
                    }

            if (!hasFg) return null;

            const PAD = 20;
            return {
                x: Math.max(0, minGX * GS - PAD),
                y: Math.max(0, minGY * GS - PAD),
                w: Math.min(w - Math.max(0, minGX * GS - PAD), (maxGX - minGX + 1) * GS + PAD * 2),
                h: Math.min(h - Math.max(0, minGY * GS - PAD), (maxGY - minGY + 1) * GS + PAD * 2),
            };
        }

        /**
         * 在预览图上绘制框选矩形（最终帧，无动画）
         * @param {{x:number, y:number, w:number, h:number}|null} box
         */
        _drawBoundingBox(box) {
            if (!box) {
                this._hideBoundingBox();
                return;
            }
            this._drawScaledBoundingBox(box, 1);
        }

        _hideBoundingBox() {
            const canvas = this.elements.bboxOverlay;
            canvas.width = 0;
            canvas.height = 0;
        }

        async _cropToBox(box) {
            const img = await this._loadImage(this.state.originalFile);
            const canvas = document.createElement('canvas');
            canvas.width = box.w;
            canvas.height = box.h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, box.x, box.y, box.w, box.h, 0, 0, box.w, box.h);
            return await this._canvasToBlob(canvas);
        }

        /**
         * 平滑切换 img 的 src（淡出 → 换图 → 淡入）
         * @param {HTMLImageElement} imgEl
         * @param {string} newSrc
         * @returns {Promise<void>}
         */
        async _fadeImageTo(imgEl, newSrc) {
            // 淡出
            imgEl.classList.add('fade-out');
            await new Promise(r => setTimeout(r, 150));

            imgEl.src = newSrc;

            // 等待加载
            if (!imgEl.complete) {
                await new Promise((resolve) => {
                    imgEl.addEventListener('load', resolve, {
                        once: true
                    });
                    imgEl.addEventListener('error', resolve, {
                        once: true
                    });
                });
            }

            // 淡入
            imgEl.classList.remove('fade-out');
            await new Promise(r => setTimeout(r, 250));
        }

        /**
         * 将预览区切换回原始图像（带平滑过渡）
         */
        async _restoreOriginalImage() {
            const url = URL.createObjectURL(this.state.originalFile);
            await this._fadeImageTo(this.elements.mainImage, url);
            this.elements.imageTitle.textContent = '待处理';
            this.elements.imageTitle.style.color = '';
        }

        /**
         * 用 requestAnimationFrame 实现框选矩形从中心展开的动画
         */
        async _animateBoundingBox(box) {
            const duration = 450; // ms
            const start = performance.now();

            const img = this.elements.mainImage;
            const wrapper = img.parentElement;

            return new Promise((resolve) => {
                const animate = (now) => {
                    const elapsed = now - start;
                    const t = Math.min(elapsed / duration, 1);
                    // easeOutCubic: 1-(1-t)^3，先快后慢更自然
                    const ease = 1 - Math.pow(1 - t, 3);

                    this._drawScaledBoundingBox(box, ease);

                    if (t < 1) {
                        requestAnimationFrame(animate);
                    } else {
                        resolve();
                    }
                };
                requestAnimationFrame(animate);
            });
        }

        /**
         * 按缩放比例 t (0→1) 绘制框选矩形（从中心展开）
         */
        _drawScaledBoundingBox(box, t) {
            const canvas = this.elements.bboxOverlay;
            const img = this.elements.mainImage;
            const wrapper = img.parentElement;

            // 重置 canvas（含清除画布）
            canvas.width = wrapper.clientWidth;
            canvas.height = wrapper.clientHeight;
            const ctx = canvas.getContext('2d');

            // 图像显示空间映射
            const imgW = img.naturalWidth,
                imgH = img.naturalHeight;
            const containerW = canvas.width,
                containerH = canvas.height;
            const scale = Math.min(containerW / imgW, containerH / imgH, 1);
            const dispW = imgW * scale,
                dispH = imgH * scale;
            const offsetX = (containerW - dispW) / 2;
            const offsetY = (containerH - dispH) / 2;

            // 框选目标位置（像素空间 → 显示空间）
            const rx = offsetX + box.x * scale;
            const ry = offsetY + box.y * scale;
            const rw = box.w * scale;
            const rh = box.h * scale;

            // 从中心按 t 缩放
            const cx = rx + rw / 2;
            const cy = ry + rh / 2;
            const sw = rw * t;
            const sh = rh * t;
            const sx = cx - sw / 2;
            const sy = cy - sh / 2;

            if (t <= 0.01) return;

            // 半透明暗色遮罩
            ctx.fillStyle = 'rgba(0,0,0,0.35)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 挖出高亮区域
            ctx.clearRect(sx, sy, sw, sh);

            // 边框（虚线逐渐变实线）
            const dashLen = Math.max(4, 10 * (1 - t));
            ctx.strokeStyle = '#00ff88';
            ctx.lineWidth = 2 + t * 2;
            ctx.setLineDash([dashLen, dashLen]);
            ctx.strokeRect(sx, sy, sw, sh);

            // 四角角标（透明度随 t 淡入）
            if (t > 0.3) {
                const cornerT = (t - 0.3) / 0.7; // 0.3~1.0 之间淡入
                ctx.lineWidth = 4;
                ctx.setLineDash([]);
                ctx.globalAlpha = cornerT;

                const cl = Math.min(16, 12 + 4 * t);
                // 左上
                ctx.beginPath();
                ctx.moveTo(sx, sy + cl);
                ctx.lineTo(sx, sy);
                ctx.lineTo(sx + cl, sy);
                ctx.stroke();
                // 右上
                ctx.beginPath();
                ctx.moveTo(sx + sw - cl, sy);
                ctx.lineTo(sx + sw, sy);
                ctx.lineTo(sx + sw, sy + cl);
                ctx.stroke();
                // 左下
                ctx.beginPath();
                ctx.moveTo(sx, sy + sh - cl);
                ctx.lineTo(sx, sy + sh);
                ctx.lineTo(sx + cl, sy + sh);
                ctx.stroke();
                // 右下
                ctx.beginPath();
                ctx.moveTo(sx + sw - cl, sy + sh);
                ctx.lineTo(sx + sw, sy + sh);
                ctx.lineTo(sx + sw, sy + sh - cl);
                ctx.stroke();

                ctx.globalAlpha = 1;
            }
        }

        /**
         * 完整的快速框选流程：切回原图 → 检测 → 动画 → 裁剪
         */
        async _quickSelectCanvas() {
            // 1) 切换回原始图像（动画舞台）
            await this._restoreOriginalImage();

            // 2) 检测画面主体包围盒
            const box = await this._detectBoundingBox();

            if (!box) {
                this._hideBoundingBox();
                const img = await this._loadImage(this.state.originalFile);
                const c = document.createElement('canvas');
                c.width = img.width;
                c.height = img.height;
                c.getContext('2d').drawImage(img, 0, 0);
                return await this._canvasToBlob(c);
            }

            // 3) 动画：框选矩形从中心展开（450ms，easeOutCubic）
            await this._animateBoundingBox(box);

            // 4) 保持显示片刻让用户看到结果
            await new Promise(r => setTimeout(r, 350));

            // 5) 隐藏框选，裁剪角色区域
            this._hideBoundingBox();
            return await this._cropToBox(box);
        }

        _loadImage(file) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = reject;
                img.src = URL.createObjectURL(file);
            });
        }

        _canvasToBlob(canvas) {
            // 用 JPEG 压缩避免图片体积超大
            return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
        }

        // ===== AI 模式：@imgly/background-removal =====

        async _removeBgAI() {
            const config = {
                publicPath: 'https://static.322337.xyz/file/package/dist/',
                device: 'gpu',
                model: 'small',
                output: {
                    format: 'image/png',
                    quality: 0.8
                },
                progress: (key, current, total) => {
                    const progress = (current / total) * 100;
                    this.elements.progressBar.style.width = `${progress}%`;
                    console.log(`下载进度 ${key}: ${current} / ${total}`);
                }
            };
            return await removeBackground(this.state.originalFile, config);
        }

        async finishRemoveBgProcess(url, method) {
            await this._fadeImageTo(this.elements.mainImage, url);
            this.elements.imageTitle.textContent = '成功';
            this.elements.imageTitle.style.color = 'var(--pico-success-color)';
            if (method === 'ai') {
                this.elements.progressContainer.style.display = 'none';
            }
            this.elements.removeBgBtn.disabled = false;
            this.elements.removeBgBtn.textContent = method === 'canvas' ? '开始框选角色' : '开始去除背景';
        }

        handleRemoveBgError(error, method) {
            console.error('背景去除失败:', error);
            this.showError('背景去除失败，请重试或更换图片');
            this.elements.removeBgBtn.disabled = false;
            this.elements.removeBgBtn.textContent = method === 'canvas' ? '开始框选角色' : '开始去除背景';
            if (method === 'ai') {
                this.elements.progressContainer.style.display = 'none';
            }
            this.elements.imagePlaceholder.style.display = this.elements.mainImage.src &&
                this.elements.mainImage.src !== '#' ? 'none' : 'flex';
        }

        // ========== 确认操作 ==========

        async handleCropConfirm() {
            if (this.state.isUploading) return;

            try {
                this.setLoadingState(true);
                const blob = await this.getProcessedImageBlob();
                await this.uploadImage(blob);

            } catch (error) {
                this.showError(`处理失败: ${error.message}`);
            } finally {
                this.setLoadingState(false);
            }
        }

        async getProcessedImageBlob() {
            if (this.state.currentMode === 'quick') {
                // 快速模式：直接上传原图或裁剪
                if (this.state.cropper) {
                    const croppedCanvas = this.state.cropper.getCroppedCanvas();
                    return await this.canvasToBlob(croppedCanvas);
                }
                // 未裁剪则用原始文件
                return this.state.originalFile;

            } else if (this.state.currentMode === 'advanced') {
                // 高级模式：先用原图进行框选或去背景预处理
                if (!this.elements.mainImage.src || this.elements.mainImage.src === '#') {
                    throw new Error('请先上传图片');
                }

                if (this.elements.imageTitle.textContent === '成功') {
                    // 已有预处理结果
                    const response = await fetch(this.elements.mainImage.src);
                    return await response.blob();
                }

                // 先框选/去背景再识别
                await this.handleRemoveBackground();

                if (this.elements.imageTitle.textContent !== '成功') {
                    throw new Error('角色框选或去背景失败');
                }

                const response = await fetch(this.elements.mainImage.src);
                return await response.blob();
            }
        }

        handleCropCancel() {
            this.resetUI();
            this.elements.fileInput.value = '';
        }

        // ========== 上传和结果处理 ==========

        async uploadImage(blob) {
            this.state.isUploading = true;
            this.elements.confirmCropBtn.disabled = true;

            const formData = this.createFormData(blob);

            try {
                // === 方案1: 流式上传 (POST /upload + SSE 流) ===
                try {
                    await this.streamUpload(formData);
                    return;
                } catch (streamErr) {
                    // 流式上传失败（如服务端不支持），降级到传统方式
                    console.warn('流式上传降级:', streamErr.message);
                }

                // === 方案2: 传统方式 (JSON + SSE 推送) ===
                this.showLoading(null, formData.get('recognition_type') || 'auto');

                const response = await Auth.fetch(`${window.API_BASE_URL}/upload`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-API-Key': '37ac_ls340v2qkcbqqt7xbdi0d1kvb9cd1qz4cfgp3s4z'
                    }
                });

                if (!response.ok) {
                    throw new Error(`服务器错误: ${response.status}`);
                }

                const data = await this.processUploadResponse(response);

                if (data.status === 'queued' && data.task_id) {
                    await this.streamTaskResult(data.task_id);
                } else {
                    throw new Error(data.message || '上传成功，但未返回任务ID');
                }

            } catch (error) {
                throw error;
            }
        }

        async streamUpload(formData) {
            // 尝试流式上传：POST /upload 返回 SSE 流，直接在 HTTP 响应中推送结果
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${window.API_BASE_URL}/upload`);
            xhr.setRequestHeader('X-API-Key', '37ac_ls340v2qkcbqqt7xbdi0d1kvb9cd1qz4cfgp3s4z');
            xhr.setRequestHeader('X-Stream-Response', 'true');

            return new Promise((resolve, reject) => {
                let resultData = null;
                let taskId = null;
                let buffer = '';

                xhr.onreadystatechange = () => {
                    // 等待拿到响应头确认 content-type
                    if (xhr.readyState === XMLHttpRequest.HEADERS_RECEIVED) {
                        const contentType = xhr.getResponseHeader('Content-Type') || '';
                        if (!contentType.includes('text/event-stream')) {
                            // 服务端不支持流式，终止请求并降级
                            xhr.abort();
                            reject(new Error('服务端不支持流式响应'));
                            return;
                        }
                    }

                    if (xhr.readyState === XMLHttpRequest.LOADING || xhr.readyState === XMLHttpRequest.DONE) {
                        buffer += xhr.responseText;
                        // 按行解析 SSE 数据
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || ''; // 保留未完成行

                        for (const line of lines) {
                            const match = line.match(/^data:\s*(.*)/);
                            if (!match) continue;
                            try {
                                const data = JSON.parse(match[1]);

                                if (data.task_id) taskId = data.task_id;

                                if (data.status === 'queued') {
                                    // 显示加载状态
                                    this.showLoading(taskId, data.recognition_type);
                                } else if (data.status === 'waiting') {
                                    // 更新提示：等待空闲节点
                                    this.showLoading(taskId, 'waiting');
                                    const spinnerText = document.querySelector('.loading-spinner p');
                                    if (spinnerText) {
                                        spinnerText.textContent = '等待空闲节点中... 节点上线后自动分配推理';
                                    }
                                } else if (data.status === 'completed') {
                                    this.showResult(data);
                                    resolve(data);
                                    return;
                                } else if (data.status === 'failed' || data.status === 'error') {
                                    reject(new Error(data.message || data.error || '推理失败'));
                                    return;
                                } else if (data.status === 'timeout') {
                                    reject(new Error(data.message || '推理超时'));
                                    return;
                                }
                            } catch (e) {
                                // 忽略解析错误，继续等待
                            }
                        }

                        // 流结束但没有结果，降级
                        if (xhr.readyState === XMLHttpRequest.DONE && !resultData) {
                            if (taskId) {
                                // 至少拿到了 taskId，尝试 SSE 端点
                                reject(new Error('STREAM_DONE_FALLBACK:' + taskId));
                            } else {
                                reject(new Error('未收到任何任务数据'));
                            }
                        }
                    }
                };

                xhr.onerror = () => reject(new Error('网络错误'));
                xhr.send(formData);
            }).catch(err => {
                if (err.message && err.message.startsWith('STREAM_DONE_FALLBACK:')) {
                    const taskId = err.message.split(':')[1];
                    return this.streamTaskResult(taskId).then(data => {
                        this.showResult(data);
                    });
                }
                throw err;
            });
        }

        createFormData(blob) {
            const formData = new FormData();
            const fileName = this.state.currentMode === 'advanced' ?
                `no_bg_${this.state.originalFile.name}` :
                this.state.originalFile.name;

            const file = new File([blob], fileName, {
                type: blob.type
            });
            formData.append('file', file);

            // 高级模式中附加识别方式选择（快速模式默认 auto）
            if (this.state.currentMode === 'advanced') {
                const recognitionType = document.querySelector('input[name="recognitionType"]:checked');
                if (recognitionType) {
                    formData.append('recognition_type', recognitionType.value);
                }
            } else {
                formData.append('recognition_type', 'auto');
            }

            return formData;
        }

        async processUploadResponse(response) {
            const raw = await response.json();
            return raw.data || raw;
        }

        async streamTaskResult(taskId) {
            // === SSE 实时流（主方案）===
            try {
                const data = await new Promise((resolve, reject) => {
                    const es = new EventSource(`${window.API_BASE_URL}/tasks/${taskId}/stream`);

                    es.onmessage = (e) => {
                        try {
                            const data = JSON.parse(e.data);
                            if (data.status === 'completed') {
                                es.close();
                                resolve(data);
                            } else if (data.status === 'waiting') {
                                // 任务在等待队列中，更新提示信息，保持连接等待
                                const spinnerText = document.querySelector('.loading-spinner p');
                                if (spinnerText) {
                                    spinnerText.textContent = '等待空闲节点中... 节点上线后自动分配推理';
                                }
                            } else if (data.status === 'timeout' || data.status === 'error') {
                                es.close();
                                reject(new Error(data.message || '推理超时'));
                            }
                        } catch (parseErr) {
                            es.close();
                            reject(parseErr);
                        }
                    };

                    es.onerror = () => {
                        es.close();
                        // SSE 连接失败，降级到轮询
                        console.warn('SSE 连接失败，降级到轮询模式');
                        this.pollTaskResultLegacy(taskId).then(resolve).catch(reject);
                    };
                });

                this.showResult(data);
            } catch (error) {
                this.showError(error.message || '获取推理结果失败，请稍后重试');
            }
        }

        // ========== 轮询降级方案 ==========

        async pollTaskResultLegacy(taskId) {
            const maxAttempts = 15;
            let attempt = 0;

            const poll = async () => {
                attempt++;

                try {
                    const result = await this.fetchTaskResult(taskId);

                    if (result.status === 'completed') {
                        return result;
                    } else if (result.status === 'pending') {
                        if (attempt < maxAttempts) {
                            await new Promise(resolve => setTimeout(resolve, 2000));
                            return poll();
                        } else {
                            throw new Error('推理超时，请稍后再试');
                        }
                    } else {
                        throw new Error(result.message || '获取结果失败');
                    }
                } catch (error) {
                    if (attempt < maxAttempts) {
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        return poll();
                    } else {
                        throw error;
                    }
                }
            };

            await new Promise(resolve => setTimeout(resolve, 2000));
            return poll();
        }

        async fetchTaskResult(taskId) {
            const response = await fetch(`${window.API_BASE_URL}/tasks/${taskId}`);
            if (!response.ok) {
                throw new Error(`查询失败: ${response.status}`);
            }

            const raw = await response.json();
            return raw.data || raw;
        }

        // ========== 结果显示 ==========

        showResult(data) {
            // 隐藏加载动画
            this.setLoadingState(false);

            const result = data.result || {};
            // 顶层 error 优先，或从 result.error 取
            const error = data.error || result.error;
            if (error) {
                this.showError(error);
                return;
            }
            // 兼容37ac模型 (label 含 "角色名/文件名") 和 LLM 模型 (label 直接是名称)
            const labelStr = result.label || '';
            const characterName = labelStr.includes('/') ? labelStr.split("/")[1] : labelStr;
            const recognitionType = data.recognition_type || result.recognition_type || 'local';
            const html = this.generateResultHTML(characterName, result, recognitionType);

            this.elements.resultDiv.innerHTML = html;
            this.elements.resultDiv.classList.add('result-show');
        }

        generateResultHTML(characterName, result, recognitionType) {
            const typeLabel = {
                local: '37ac模型',
                llm: '大模型 API',
                auto: '自动选择'
            } [recognitionType] || recognitionType;
            const classProbsHtml = result.class_probs && result.class_probs.length > 0 ?
                `<div class="probability-list">
                       <h4>概率分布:</h4>
                       ${result.class_probs.map(item => this.generateProbabilityItem(item)).join('')}
                   </div>` :
                '';

            return `
            <div class="result-content">
                <h3>识别结果: ${characterName}</h3>
                <a href="https://zh.moegirl.org.cn/index.php?title=${characterName}" target="_blank">
                    ${characterName} - 萌娘百科
                </a>
                <p class="recognition-badge">识别方式: <span class="badge">${typeLabel}</span></p>
                <p class="confidence"><strong>置信度:</strong> ${result.confidence || '-'}%</p>
                ${classProbsHtml}
        `;
        }

        generateProbabilityItem(item) {
            const characterName = item.name.split("/")[1];
            return `
            <div class="probability-item">
                <span class="character-name">${characterName}</span>
                <span class="probability-value">${item.prob.toFixed(2)}%</span>
                <div class="probability-bar">
                    <div class="probability-fill" style="width: ${item.prob}%"></div>
                </div>
            </div>
        `;
        }

        showError(message) {
            // 隐藏加载动画
            this.setLoadingState(false);

            this.elements.resultDiv.innerHTML = `
            <div class="error-message">
                <span style="color: var(--pico-form-element-invalid-border-color);">
                    <svg t="1759466683420" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="7411" width="24" height="24">
                        <path d="M886.784 746.496q29.696 30.72 43.52 56.32t-4.608 58.368q-4.096 6.144-11.264 14.848t-14.848 16.896-15.36 14.848-12.8 9.728q-25.6 15.36-60.416 8.192t-62.464-34.816l-43.008-43.008-57.344-57.344-67.584-67.584-73.728-73.728-131.072 131.072q-60.416 60.416-98.304 99.328-38.912 38.912-77.312 48.128t-68.096-17.408l-7.168-7.168-11.264-11.264-11.264-11.264q-6.144-6.144-7.168-8.192-11.264-14.336-13.312-29.184t2.56-29.184 13.824-27.648 20.48-24.576q9.216-8.192 32.768-30.72l55.296-57.344q33.792-32.768 75.264-73.728t86.528-86.016q-49.152-49.152-93.696-93.184t-79.872-78.848-57.856-56.832-27.648-27.136q-26.624-26.624-27.136-52.736t17.92-52.736q8.192-10.24 23.552-24.064t21.504-17.92q30.72-20.48 55.296-17.92t49.152 28.16l31.744 31.744q23.552 23.552 58.368 57.344t78.336 76.288 90.624 88.576q38.912-38.912 76.288-75.776t69.632-69.12 58.368-57.856 43.52-43.008q24.576-23.552 53.248-31.232t55.296 12.8q1.024 1.024 6.656 5.12t11.264 9.216 10.752 9.728 7.168 5.632q27.648 26.624 27.136 57.856t-27.136 57.856q-18.432 18.432-45.568 46.08t-60.416 60.416-70.144 69.632l-77.824 77.824q37.888 36.864 74.24 72.192t67.584 66.048 56.32 56.32 41.472 41.984z" p-id="7412"></path>
                    </svg> ${message}
                </span>
            </div>
        `;

            this.elements.resultDiv.classList.add('result-show');
        }

        showLoading(taskId, recognitionType) {
            this.setLoadingState(true);
            // 更新加载提示文字
            const spinnerText = this.elements.loadingSpinner.querySelector('p');
            if (spinnerText) {
                const modeText = recognitionType === 'llm' ? '大模型深度思考' :
                    recognitionType === 'local' ? '本地模型快速识别' :
                    '自动选择识别方式';
                spinnerText.textContent = `正在识别中，请稍候... (${modeText})`;
            }
        }

        hideResult() {
            this.elements.resultDiv.classList.remove('result-show');
        }

        setLoadingState(loading) {
            this.state.isUploading = loading;
            this.elements.loadingSpinner.style.display = loading ? 'block' : 'none';

            if (!loading) {
                this.elements.confirmCropBtn.disabled = false;
            }
        }

        resetUI() {
            if (this.state.cropper) {
                this.state.cropper.destroy();
                this.state.cropper = null;
            }

            this.elements.cropContainer.style.display = 'none';
            this.elements.imagePreview.src = '#';
            this.elements.mainImage.src = '#';
            this.hideResult();

            this.state.originalFile = null;
            this.state.isUploading = false;
        }
    }

    // ========== 页面初始化 ==========

    document.addEventListener('DOMContentLoaded', () => {
        new AnimeDetector();
    });
</script>
<?php

require_once ROOT_PATH . '/views/footer.php';
?>