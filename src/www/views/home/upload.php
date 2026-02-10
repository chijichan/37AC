<?php
require_once ROOT_PATH . '/views/layout.php';
?>
<div class="anime-detector-container">
    <h2>上传图片，识别二次元角色</h2>

    <!-- 文件上传区域 -->
    <div class="upload-section">
        <div class="file-input-wrapper">
            <label for="fileInput" class="file-input-label">
                <i class="upload-icon"><svg t="1759466481798" class="icon" viewBox="0 0 1024 1024" version="1.1"
                        xmlns="http://www.w3.org/2000/svg" p-id="4741" width="32" height="32">
                        <path
                            d="M855.04 385.024q19.456 2.048 38.912 10.24t33.792 23.04 21.504 37.376 2.048 54.272q-2.048 8.192-8.192 40.448t-14.336 74.24-18.432 86.528-19.456 76.288q-5.12 18.432-14.848 37.888t-25.088 35.328-36.864 26.112-51.2 10.24l-567.296 0q-21.504 0-44.544-9.216t-42.496-26.112-31.744-40.96-12.288-53.76l0-439.296q0-62.464 33.792-97.792t95.232-35.328l503.808 0q22.528 0 46.592 8.704t43.52 24.064 31.744 35.84 12.288 44.032l0 11.264-53.248 0q-40.96 0-95.744-0.512t-116.736-0.512-115.712-0.512-92.672-0.512l-47.104 0q-26.624 0-41.472 16.896t-23.04 44.544q-8.192 29.696-18.432 62.976t-18.432 61.952q-10.24 33.792-20.48 65.536-2.048 8.192-2.048 13.312 0 17.408 11.776 29.184t29.184 11.776q31.744 0 43.008-39.936l54.272-198.656q133.12 1.024 243.712 1.024l286.72 0z"
                            p-id="4742"></path>
                    </svg></i>
                <span>选择图片文件</span>
            </label>
            <input type="file" id="fileInput" accept="image/*" class="file-input" />
            <p class="file-hint">支持 JPG、PNG 格式，最大 10MB</p>
        </div>
    </div>

    <!-- 裁剪区域 -->
    <div id="cropContainer" class="crop-container">
        <div class="crop-layout">
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
        padding: 20px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .upload-section {
        background: #f8f9fa;
        border: 2px dashed #dee2e6;
        border-radius: 12px;
        padding: 30px;
        text-align: center;
        margin-bottom: 24px;
        transition: all 0.3s ease;
        position: relative;
    }

    .upload-section:hover {
        border-color: #007bff;
        background: #f1f8ff;
    }

    .upload-section.drag-over {
        border-color: #007bff;
        background-color: #e3f2fd;
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(0, 123, 255, 0.2);
    }

    .upload-section.drag-invalid {
        border-color: #dc3545;
        background-color: #ffebee;
    }

    .file-input-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
    }

    .file-input-label {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        background: #007bff;
        color: white;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.3s ease;
        font-weight: 500;
    }

    .file-input-label:hover {
        background: #0056b3;
    }

    .file-input {
        display: none;
    }

    .file-hint {
        color: #6c757d;
        font-size: 14px;
        margin: 0;
    }

    .crop-container {
        display: none;
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .crop-layout {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 24px;
        align-items: start;
    }

    .crop-main h3,
    .crop-preview-section h3 {
        margin-bottom: 16px;
        color: #343a40;
        font-size: 18px;
    }

    .image-wrapper {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        overflow: hidden;
        max-width: 500px;
    }

    .crop-image {
        max-width: 100%;
        height: auto;
        display: block;
    }

    .preview-box {
        width: 120px;
        height: 120px;
        border: 2px solid #007bff;
        border-radius: 8px;
        overflow: hidden;
        background: #f8f9fa;
    }

    .preview-hint {
        font-size: 12px;
        color: #6c757d;
        margin-top: 8px;
    }

    .crop-controls {
        display: flex;
        gap: 12px;
        justify-content: center;
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #e9ecef;
    }

    .action-section {
        text-align: center;
        margin: 24px 0;
    }

    .btn {
        padding: 12px 24px;
        border: none;
        border-radius: 6px;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        min-width: 140px;
    }

    .btn-primary {
        background: #007bff;
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        background: #0056b3;
        transform: translateY(-1px);
    }

    .btn-primary:disabled {
        background: #6c757d;
        cursor: not-allowed;
        transform: none;
    }

    .btn-secondary {
        background: #6c757d;
        color: white;
    }

    .btn-secondary:hover {
        background: #545b62;
    }

    .loading-spinner {
        display: none;
        text-align: center;
        padding: 40px;
    }

    .spinner {
        width: 40px;
        height: 40px;
        /* border: 4px solid #f3f3f3;
        border-top: 4px solid #007bff;
        border-radius: 50%; */
        /* animation: spin 1s linear infinite; */
        margin: 0 auto 16px;
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
        margin-top: 24px;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 8px;
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
            gap: 16px;
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
    }
</style>

<script>
    class AnimeDetector {
        constructor() {
            this.elements = {
                fileInput: document.getElementById('fileInput'),
                imagePreview: document.getElementById('imagePreview'),
                cropContainer: document.getElementById('cropContainer'),
                cropPreview: document.getElementById('cropPreview'),
                confirmCropBtn: document.getElementById('confirmCropBtn'),
                cancelCropBtn: document.getElementById('cancelCropBtn'),
                loadingSpinner: document.getElementById('loadingSpinner'),
                resultDiv: document.getElementById('result')
            };

            this.state = {
                cropper: null,
                originalFile: null,
                isUploading: false
            };

            this.initEventListeners();
        }

        initEventListeners() {
            this.elements.fileInput.addEventListener('change', (event) => {
                this.handleFileSelect(event);
            });

            // 裁剪相关按钮
            this.elements.confirmCropBtn.addEventListener('click', () => {
                this.handleCropConfirm();
            });
            this.elements.cancelCropBtn.addEventListener('click', () => {
                this.handleCropCancel();
            });

            const uploadSection = document.querySelector('.upload-section');

            // 阻止默认拖放行为（非常重要！）
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

            // 放下（Drop）文件时处理
            uploadSection.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const file = files[0];
                    this.handleDroppedFile(file);
                }
            }, false);
        }

        // 阻止默认行为
        preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // 检查是否为有效的图片文件（仅允许 jpg、jpeg、png，且不超过 10MB）
        isValidImageFile(file) {
            if (!file) {
                return false;
            }

            // 只允许以下 MIME 类型
            const allowedMimeTypes = ['image/jpeg', 'image/jpg', 'image/png'];
            const isAllowedType = allowedMimeTypes.includes(file.type);

            if (!isAllowedType) {
                return false;
            }

            // 文件大小限制：10MB
            const maxSize = 10 * 1024 * 1024; // 10MB
            const isWithinSizeLimit = file.size <= maxSize;

            if (!isWithinSizeLimit) {
                return false;
            }

            // 所有校验通过
            return true;
        }

        handleDroppedFile(file) {
            if (!this.isValidImageFile(file)) {
                const uploadSection = document.querySelector('.upload-section');
                uploadSection.classList.add('drag-invalid');
                setTimeout(() => uploadSection.classList.remove('drag-invalid'), 1000);
                this.showError('请选择有效的图片文件（仅支持 JPG、JPEG、PNG 格式，且不超过 10MB）');
                return;
            }

            this.state.originalFile = file;
            this.loadImageForCropping(file);
        }

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (!this.isValidImageFile(file)) {
                this.showError('请选择有效的图片文件（仅支持 JPG、JPEG、PNG 格式，且不超过 10MB）');
                return;
            }

            this.state.originalFile = file;
            this.loadImageForCropping(file);
        }

        loadImageForCropping(file) {
            const reader = new FileReader();

            reader.onload = (e) => {
                this.elements.imagePreview.src = e.target.result;
                this.showCropInterface();
                this.initCropper();
            };

            reader.onerror = () => {
                this.showError('图片读取失败，请重试');
            };

            reader.readAsDataURL(file);
        }

        showCropInterface() {
            this.elements.cropContainer.style.display = 'block';
            this.hideResult();
        }

        initCropper() {
            // 销毁现有的Cropper实例
            if (this.state.cropper) {
                this.state.cropper.destroy();
            }

            // 初始化新的Cropper实例[6](@ref)
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

        async handleCropConfirm() {
            if (!this.state.cropper || this.state.isUploading) {
                return;
            }

            try {
                this.setLoadingState(true);
                const croppedCanvas = this.state.cropper.getCroppedCanvas();
                const blob = await this.canvasToBlob(croppedCanvas);
                await this.uploadImage(blob);

            } catch (error) {
                this.showError(`裁剪处理失败: ${error.message}`);
            } finally {
                this.setLoadingState(false);
            }
        }

        canvasToBlob(canvas) {
            return new Promise((resolve) => {
                canvas.toBlob((blob) => {
                    resolve(blob);
                }, 'image/jpeg', 0.92);
            });
        }

        handleCropCancel() {
            this.resetUI();
            this.elements.fileInput.value = '';
        }

        async handleUpload() {
            if (this.state.isUploading) {
                return;
            }

            if (!this.state.originalFile) {
                this.showError('请先选择图片文件');
                return;
            }

            try {
                this.setLoadingState(true);
                await this.uploadImage(this.state.originalFile);

            } catch (error) {
                this.showError(`上传失败: ${error.message}`);
            } finally {
                this.setLoadingState(false);
            }
        }

        async uploadImage(blob) {
            this.state.isUploading = true;
            this.elements.confirmCropBtn.disabled = true;

            const formData = new FormData();
            const file = new File([blob], `cropped_${this.state.originalFile.name}`, {
                type: blob.type
            });
            formData.append('file', file);

            try {
                const response = await fetch('https://api.322337.xyz/upload', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response.ok) {
                    throw new Error(`服务器错误: ${response.status}`);
                }

                const data = await response.json();

                // 假设后端返回格式为：
                // {
                //   "status": "queued",
                //   "task_id": "6093950a-4dab-4289-96ad-ed6eb901700c"
                // }
                if (data.status === 'queued' && data.task_id) {
                    const task_id = data.task_id;
                    // this.showLoadingResult(); // 可选：显示“推理中...”
                    await this.pollTaskResult(task_id); // 开始轮询任务结果
                } else {
                    // 后端返回了错误或未知格式
                    throw new Error(data.error || '上传成功，但未返回任务ID');
                }

            } catch (error) {
                throw error;
            }
        }

        handleResponse(data) {
            if (data.error) {
                this.showError(data.error);
                return;
            }

            if (data.success) {
                this.showResult(data);
                return;
            }

            this.showError('未知响应格式');
        }

        async pollTaskResult(task_id) {
            const maxAttempts = 30; // 最多轮询 30 次（约 1 分钟，假设每 2 秒一次）
            let attempt = 0;

            const poll = async () => {
                attempt++;
                try {
                    const response = await fetch(`https://api.322337.xyz/task-result/${task_id}`);
                    if (!response.ok) {
                        throw new Error(`查询失败: ${response.status}`);
                    }

                    const data = await response.json();

                    if (data.status === 'completed') {
                        // this.hideLoadingResult(); // 隐藏“推理中”提示（如有）
                        this.showResult(data);   // 展示结果
                        return;
                    } else if (data.status === 'pending') {
                        // 结果还未返回，继续轮询
                        if (attempt < maxAttempts) {
                            await new Promise(resolve => setTimeout(resolve, 2000)); // 等待 2 秒
                            await poll(); // 递归调用自身
                        } else {
                            throw new Error('推理超时，请稍后再试');
                        }
                    } else {
                        // 其它错误状态
                        throw new Error(data.message || '获取结果失败');
                    }
                } catch (error) {
                    if (attempt < maxAttempts) {
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        await poll();
                    } else {
                        // this.hideLoadingResult();
                        this.showError(error.message || '获取推理结果失败，请稍后重试');
                    }
                }
            };

            await new Promise(resolve => setTimeout(resolve, 2000));
            await poll(); // 开始轮询
        }

        showResult(data) {
            const html = `
            <div class="result-content">
                <h3>识别结果: ${data.result.label}</h3>
                <a href="https://zh.moegirl.org.cn/index.php?title=${data.result.label}" Target="_blank"“">${data.result.label} - 萌娘百科</a>
                <p class="confidence"><strong>置信度:</strong> ${data.result.confidence}%</p>
                
                <div class="probability-list">
                    <h4>概率分布:</h4>
                    ${data.result.class_probs.map(item => `
                        <div class="probability-item">
                            <span class="character-name">${item.name}</span>
                            <span class="probability-value">${item.prob.toFixed(2)}%</span>
                            <div class="probability-bar">
                                <div class="probability-fill" style="width: ${item.prob}%"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

            this.elements.resultDiv.innerHTML = html;
            this.elements.resultDiv.classList.add('result-show');
        }

        showError(message) {
            this.elements.resultDiv.innerHTML = `
            <div class="error-message">
                <span style="color: #dc3545;"><svg t="1759466683420" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="7411" width="24" height="24"><path d="M886.784 746.496q29.696 30.72 43.52 56.32t-4.608 58.368q-4.096 6.144-11.264 14.848t-14.848 16.896-15.36 14.848-12.8 9.728q-25.6 15.36-60.416 8.192t-62.464-34.816l-43.008-43.008-57.344-57.344-67.584-67.584-73.728-73.728-131.072 131.072q-60.416 60.416-98.304 99.328-38.912 38.912-77.312 48.128t-68.096-17.408l-7.168-7.168-11.264-11.264-11.264-11.264q-6.144-6.144-7.168-8.192-11.264-14.336-13.312-29.184t2.56-29.184 13.824-27.648 20.48-24.576q9.216-8.192 32.768-30.72l55.296-57.344q33.792-32.768 75.264-73.728t86.528-86.016q-49.152-49.152-93.696-93.184t-79.872-78.848-57.856-56.832-27.648-27.136q-26.624-26.624-27.136-52.736t17.92-52.736q8.192-10.24 23.552-24.064t21.504-17.92q30.72-20.48 55.296-17.92t49.152 28.16l31.744 31.744q23.552 23.552 58.368 57.344t78.336 76.288 90.624 88.576q38.912-38.912 76.288-75.776t69.632-69.12 58.368-57.856 43.52-43.008q24.576-23.552 53.248-31.232t55.296 12.8q1.024 1.024 6.656 5.12t11.264 9.216 10.752 9.728 7.168 5.632q27.648 26.624 27.136 57.856t-27.136 57.856q-18.432 18.432-45.568 46.08t-60.416 60.416-70.144 69.632l-77.824 77.824q37.888 36.864 74.24 72.192t67.584 66.048 56.32 56.32 41.472 41.984z" p-id="7412"></path></svg> ${message}</span>
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
            this.hideResult();

            this.state.originalFile = null;
            this.state.isUploading = false;
        }
    }

    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', () => {
        new AnimeDetector();
    });
</script>
<?php

require_once ROOT_PATH . '/views/footer.php';
?>