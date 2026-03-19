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

    <!-- 裁剪区域 -->
    <div id="cropContainer" class="crop-container">
        <!-- 新增导航栏 -->
        <div class="crop-navigation">
            <div class="nav-tabs">
                <button class="nav-tab active" data-mode="crop">裁剪模式</button>
                <button class="nav-tab" data-mode="remove-bg">去除背景</button>
            </div>
        </div>

        <!-- 裁剪布局 -->
        <div id="cropLayout" class="crop-layout">
            <div class="crop-main">
                <h3>调整选框以精确框选角色</h3>
                <div class="image-wrapper">
                    <img id="imagePreview" src="#" alt="裁剪预览" class="crop-image" />
                </div>
            </div>

            <div class="crop-preview-section">
                <h3>预览效果</h3>
                <div id="cropPreview" class="preview-box"></div>
                <p class="preview-hint">实时预览裁剪结果</p>
            </div>
        </div>

        <!-- 背景去除布局 -->
        <div id="removeBgLayout" class="remove-bg-layout" style="display: none;">
            <div class="remove-bg-main">
                <h3>去除图片背景</h3>
                <div class="remove-bg-content">
                    <div class="single-image-container">
                        <div class="image-box">
                            <h4 id="imageTitle">待处理</h4>
                            <div class="image-wrapper">
                                <img id="mainImage" src="#" alt="处理后图片" class="bg-image" />
                                <div class="image-placeholder" id="imagePlaceholder">
                                    <p>请先上传图片，然后点击"开始去除背景"</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="remove-bg-controls">
                        <button id="removeBgBtn" class="btn btn-primary">开始去除背景</button>
                        <div class="progress" id="progressContainer" style="display: none;">
                            <div class="progress-bar" id="progressBar"></div>
                        </div>
                        <p class="processing-hint">首次使用需要下载AI模型，请耐心等待</p>
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

    /* 背景去除布局样式 */
    .remove-bg-layout {
        width: 100%;
    }

    .remove-bg-main h3 {
        margin-bottom: calc(var(--pico-spacing) * 0.5);
        color: var(--pico-h3-color);
        font-size: var(--pico-h3-font-size, 1.5rem);
    }

    .remove-bg-content {
        width: 100%;
    }

    .single-image-container {
        width: 100%;
        margin-bottom: calc(var(--pico-spacing) * 0.5);
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

    .remove-bg-controls {
        text-align: center;
        margin-top: calc(var(--pico-spacing) * 0.5);
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

    .processing-hint {
        font-size: 0.75em;
        color: var(--pico-muted-color);
        margin-top: calc(var(--pico-spacing) * 0.25);
        font-style: italic;
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

    @keyframes spin {
        0% {
            transform: rotate(0deg);
        }

        100% {
            transform: rotate(360deg);
        }
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

    /* 响应式设计 */
    @media (max-width: 768px) {
        .crop-layout {
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
                cropLayout: document.getElementById('cropLayout'),
                removeBgLayout: document.getElementById('removeBgLayout'),
                cropPreview: document.getElementById('cropPreview'),
                confirmCropBtn: document.getElementById('confirmCropBtn'),
                cancelCropBtn: document.getElementById('cancelCropBtn'),
                removeBgBtn: document.getElementById('removeBgBtn'),
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
                currentMode: 'crop' // 'crop' 或 'remove-bg'
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
                tab.addEventListener('click', (e) => {
                    this.switchMode(e.target.dataset.mode);
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

        switchMode(mode) {
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
            const showCropMode = mode === 'crop';
            const showRemoveBgMode = mode === 'remove-bg';

            this.elements.cropLayout.style.display = showCropMode ? 'grid' : 'none';
            this.elements.removeBgLayout.style.display = showRemoveBgMode ? 'block' : 'none';

            this.updateConfirmButton(mode);
        }

        updateConfirmButton(mode) {
            if (mode === 'crop') {
                this.elements.confirmCropBtn.textContent = '确认识别';
            } else if (mode === 'remove-bg') {
                this.elements.confirmCropBtn.textContent = '使用去背景图片识别';
            }
            this.elements.confirmCropBtn.style.display = 'inline-block';
        }

        reinitializeViewForCurrentMode() {
            if (this.state.currentMode === 'crop') {
                this.initCropper();
            } else if (this.state.currentMode === 'remove-bg') {
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

        loadImageForProcessing(file) {
            const reader = new FileReader();

            reader.onload = (e) => {
                const imageUrl = e.target.result;
                this.updateImageViews(imageUrl);
                this.showCropInterface();
                this.reinitializeViewForCurrentMode();
            };

            reader.onerror = () => {
                this.showError('图片读取失败，请重试');
            };

            reader.readAsDataURL(file);
        }

        updateImageViews(imageUrl) {
            if (this.state.currentMode === 'crop') {
                this.elements.imagePreview.src = imageUrl;
                this.elements.mainImage.src = imageUrl;
            } else if (this.state.currentMode === 'remove-bg') {
                this.elements.mainImage.src = imageUrl;
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
            this.elements.imageTitle.textContent = '待处理';
            this.elements.imageTitle.style.color = '';
            this.elements.imagePlaceholder.style.display = this.elements.mainImage.src &&
                this.elements.mainImage.src !== '#' ? 'none' : 'flex';
            this.elements.progressContainer.style.display = 'none';
        }

        async handleRemoveBackground() {
            if (!this.state.originalFile || this.state.isUploading) return;

            try {
                this.startRemoveBgProcess();

                const blob = await this.performBackgroundRemoval();
                const url = URL.createObjectURL(blob);

                this.finishRemoveBgProcess(url);

            } catch (error) {
                this.handleRemoveBgError(error);
            }
        }

        startRemoveBgProcess() {
            this.elements.removeBgBtn.disabled = true;
            this.elements.progressContainer.style.display = 'block';
            this.elements.progressBar.style.width = '0%';
            this.elements.imagePlaceholder.style.display = 'none';
        }

        async performBackgroundRemoval() {
            const config = {
                publicPath: 'https://static.322337.xyz/file/package/dist/',
                device: 'gpu',
                // model: 'large',
                // model: 'medium',
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

        finishRemoveBgProcess(url) {
            this.elements.mainImage.src = url;
            this.elements.imageTitle.textContent = '成功';
            this.elements.imageTitle.style.color = 'var(--pico-success-color)';
            this.elements.progressContainer.style.display = 'none';
            this.elements.removeBgBtn.disabled = false;
        }

        handleRemoveBgError(error) {
            console.error('背景去除失败:', error);
            this.showError('背景去除失败，请重试或更换图片');
            this.elements.removeBgBtn.disabled = false;
            this.elements.progressContainer.style.display = 'none';
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
                this.showError(`${this.state.currentMode === 'crop' ? '裁剪' : '处理'}失败: ${error.message}`);
            } finally {
                this.setLoadingState(false);
            }
        }

        async getProcessedImageBlob() {
            if (this.state.currentMode === 'crop') {
                if (!this.state.cropper) {
                    throw new Error('请先选择图片');
                }
                const croppedCanvas = this.state.cropper.getCroppedCanvas();
                return await this.canvasToBlob(croppedCanvas);

            } else if (this.state.currentMode === 'remove-bg') {
                return await this.getRemoveBgResultBlob();
            }
        }

        async getRemoveBgResultBlob() {
            if (!this.elements.mainImage.src || this.elements.mainImage.src === '#') {
                throw new Error('请先进行背景去除');
            }

            if (this.elements.imageTitle.textContent !== '成功') {
                throw new Error('请先进行背景去除处理');
            }

            const response = await fetch(this.elements.mainImage.src);
            return await response.blob();
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
                const response = await fetch('http://127.0.0.1:13138/upload', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response.ok) {
                    throw new Error(`服务器错误: ${response.status}`);
                }

                const data = await this.processUploadResponse(response);

                if (data.status === 'queued' && data.task_id) {
                    await this.pollTaskResult(data.task_id);
                } else {
                    throw new Error(data.message || '上传成功，但未返回任务ID');
                }

            } catch (error) {
                throw error;
            }
        }

        createFormData(blob) {
            const formData = new FormData();
            const fileName = this.state.currentMode === 'remove-bg' ?
                `no_bg_${this.state.originalFile.name}` :
                `cropped_${this.state.originalFile.name}`;

            const file = new File([blob], fileName, {
                type: blob.type
            });
            formData.append('file', file);

            return formData;
        }

        async processUploadResponse(response) {
            const raw = await response.json();
            return raw.data || raw;
        }

        async pollTaskResult(taskId) {
            const maxAttempts = 15;
            let attempt = 0;

            const poll = async () => {
                attempt++;

                try {
                    const result = await this.fetchTaskResult(taskId);

                    if (result.status === 'completed') {
                        this.showResult(result);
                        return;
                    } else if (result.status === 'pending') {
                        await this.handlePendingResult(attempt, maxAttempts, poll);
                    } else {
                        throw new Error(result.message || '获取结果失败');
                    }
                } catch (error) {
                    await this.handlePollError(error, attempt, maxAttempts, poll);
                }
            };

            await new Promise(resolve => setTimeout(resolve, 2000));
            await poll();
        }

        async fetchTaskResult(taskId) {
            const response = await fetch(`http://127.0.0.1:13138/tasks/${taskId}`);
            if (!response.ok) {
                throw new Error(`查询失败: ${response.status}`);
            }

            const raw = await response.json();
            return raw.data || raw;
        }

        async handlePendingResult(attempt, maxAttempts, pollCallback) {
            if (attempt < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                await pollCallback();
            } else {
                throw new Error('推理超时，请稍后再试');
            }
        }

        async handlePollError(error, attempt, maxAttempts, pollCallback) {
            if (attempt < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                await pollCallback();
            } else {
                this.showError(error.message || '获取推理结果失败，请稍后重试');
            }
        }

        // ========== 结果显示 ==========

        showResult(data) {
            const characterName = data.result.label.split("/")[1];
            const html = this.generateResultHTML(characterName, data.result);

            this.elements.resultDiv.innerHTML = html;
            this.elements.resultDiv.classList.add('result-show');
        }

        generateResultHTML(characterName, result) {
            return `
            <div class="result-content">
                <h3>识别结果: ${characterName}</h3>
                <a href="https://zh.moegirl.org.cn/index.php?title=${characterName}" target="_blank">
                    ${characterName} - 萌娘百科
                </a>
                <p class="confidence"><strong>置信度:</strong> ${result.confidence}%</p>
                
                <div class="probability-list">
                    <h4>概率分布:</h4>
                    ${result.class_probs.map(item => this.generateProbabilityItem(item)).join('')}
                </div>
            </div>
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
    export default AnimeDetector;
</script>
<?php

require_once ROOT_PATH . '/views/footer.php';
?>