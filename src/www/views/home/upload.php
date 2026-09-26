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

    /* 去掉 datalist 的原生下拉三角（Chrome/Edge 的 input[list] 指示器） */
    .upload-page input[list]::-webkit-calendar-picker-indicator {
        display: none !important;
        width: 0;
        height: 0;
        opacity: 0;
    }

    /* 骨架卡片：列表 / 结果区加载态（不写字，直接流水卡片） */
    .skeleton-card {
        display: grid;
        grid-template-columns: 64px 1fr auto;
        gap: .8rem;
        align-items: center;
        padding: .6rem;
        border: 1px solid var(--ac-line, #f0e6ea);
        border-radius: var(--ac-radius-card);
    }

    .sk-thumb {
        width: 64px;
        height: 64px;
        border-radius: var(--ac-radius-input);
    }

    .sk-line {
        display: block;
        height: 12px;
        border-radius: 999px;
    }

    .sk-chip {
        display: inline-block;
        width: 72px;
        height: 18px;
        border-radius: 999px;
    }

    .sk-btn {
        display: block;
        width: 78px;
        height: 32px;
        border-radius: 999px;
    }

    .skeleton-card .sk-body {
        display: block;
    }

    @media (max-width: 720px) {
        .skeleton-card {
            grid-template-columns: 56px 1fr;
        }

        .skeleton-card .sk-btn {
            display: none;
        }
    }

    /* 空内容框：套用仪表盘同款流水光效（复用设计系统的 skeleton-shimmer 关键帧） */
    .flow-empty {
        background: linear-gradient(90deg, var(--ac-ink-100, #f0e6ea) 25%, var(--ac-surface-2, #faf6f8) 50%, var(--ac-ink-100, #f0e6ea) 75%) !important;
        background-size: 200% 100% !important;
        animation: skeleton-shimmer 1.4s infinite;
    }

    .human-crop-canvas.is-empty {
        border-style: solid;
        border-color: transparent;
    }


    /* 一张图多个角色：待提交列表 */
    .human-form-actions {
        display: flex;
        gap: .6rem;
        flex-wrap: wrap;
    }

    .human-pending {
        margin-top: 1rem;
    }

    .pending-item {
        display: grid;
        grid-template-columns: 56px 1fr auto;
        gap: .7rem;
        align-items: center;
        padding: .5rem;
        margin-top: .5rem;
        border: 1px solid var(--ac-line, #f0e6ea);
        border-radius: var(--ac-radius-card);
        background: var(--ac-surface-2, #faf6f8);
    }

    .pending-thumb {
        width: 56px;
        height: 56px;
        object-fit: cover;
        border-radius: var(--ac-radius-input);
        background: var(--ac-surface, #fff);
    }

    .pending-name {
        font-weight: 700;
        color: var(--ac-ink-900);
    }

    /* 已有票：按投票人分组 */
    .vote-group {
        margin-top: .8rem;
    }

    .vote-group-head {
        font-size: .8rem;
        font-weight: 700;
        color: var(--ac-ink-600);
        padding-bottom: .2rem;
        border-bottom: 1px solid var(--ac-line, #f0e6ea);
    }

    /* 能工智人：未选图时整块收起，选了才展开（避免空图 + 空表单） */
    .human-annotate-card[hidden] {
        display: none !important;
    }

    /* 站点导航是 sticky（--ac-nav-h=64px）：滚动定位时留出导航高度，
       否则 scrollIntoView(block:start) 会把卡片标题压在导航条下面 */
    .human-annotate-card,
    .human-crop-wrap,
    .cropper-wrap,
    .result-wrap,
    .history-item {
        scroll-margin-top: calc(var(--ac-nav-h, 64px) + 14px);
    }

    /* 待标注列表会在「骨架卡 ↔ 真实卡片」之间换高度，关掉浏览器的滚动锚定：
       否则它在上面内容变高时会自己改 scrollTop，和我们的平滑滚动打架，
       表现就是先冲过去、再退回正确位置。 */
    #panel-human,
    #humanTaskList {
        overflow-anchor: none;
    }

    .human-crop-canvas {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 240px;
        border: 1px dashed var(--ac-line, #e6dade);
        background: var(--ac-surface-2, #faf6f8);
    }

    .human-crop-canvas img {
        display: none;
        max-width: 100%;
    }

    .human-crop-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: .5rem;
        padding: 2rem 1rem;
        color: var(--ac-ink-500);
        font-size: .85rem;
        text-align: center;
    }

    .human-crop-placeholder i {
        font-size: 1.7rem;
        color: var(--ac-pink-300, #f0a6c8);
    }

    .human-crop-side .col-label {
        display: block;
        margin-bottom: .4rem;
        font-size: .8rem;
        font-weight: 700;
        color: var(--ac-ink-600);
    }

    .human-crop-actions {
        display: flex;
        justify-content: flex-end;
        margin-bottom: .4rem;
    }

    /* 能工智人：左边自己拉框，右边预览 */
    .human-crop {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 200px;
        gap: 1rem;
        align-items: start;
        margin-bottom: 1.1rem;
    }

    .human-crop-canvas {
        background: var(--ac-surface-2, #f6f2f4);
        border-radius: var(--ac-radius-card);
        overflow: hidden;
        min-height: 160px;
    }

    .human-crop-canvas img {
        display: block;
        max-width: 100%;
    }

    .human-crop-side .hint {
        margin-bottom: .6rem;
    }

    .human-crop-preview {
        width: 100%;
        height: 160px;
        overflow: hidden;
        border-radius: var(--ac-radius-card);
        background: var(--ac-surface-2, #f6f2f4);
        margin-bottom: .6rem;
    }

    .human-crop-preview img {
        display: block;
        max-width: 100%;
    }

    .form-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: .9rem;
    }

    .history-item.active {
        border-color: var(--ac-pink-400);
        box-shadow: 0 0 0 2px var(--ac-pink-100);
    }

    @media (max-width: 720px) {
        .human-crop {
            grid-template-columns: 1fr;
        }
    }

    /* 37ac 卡片里的"每个人物"区块 */
    .char-block {
        margin-top: .7rem;
        padding-top: .55rem;
        border-top: 1px dashed var(--ac-line, #f0e6ea);
    }

    .char-block:first-of-type {
        border-top: 0;
        padding-top: 0;
    }

    .char-head {
        display: flex;
        align-items: center;
        gap: .35rem;
        flex-wrap: wrap;
        margin-bottom: .35rem;
    }

    .char-index {
        font-family: var(--ac-font-mono);
        font-size: .78rem;
        color: var(--ac-ink-500);
    }

    .char-name {
        font-weight: 800;
        color: var(--ac-ink-900);
    }

    .char-conf {
        font-size: .78rem;
        color: var(--ac-ink-600);
    }

    /* 候选行：角色名 + IP 徽章（name 列原来是固定 7.5em，长名被截断才显得"IP 和角色不分"） */
    .upload-page .prob-item .name {
        flex: 1 1 auto;
        min-width: 0;
        max-width: 52%;
    }

    .cand-ip {
        margin-left: .35rem;
        font-size: .68rem;
        vertical-align: middle;
    }

    .cand-link {
        margin: -.1rem 0 .35rem;
        font-size: .75rem;
        text-align: right;
    }

    .cand-link a {
        color: var(--ac-pink-600);
        text-decoration: none;
    }

    .channel-error {
        margin-top: .5rem;
        font-size: .82rem;
        color: var(--ac-danger, #d64550);
        word-break: break-word;
    }

    /* 面板内各卡片之间留出间距（之前历史列表和结果区贴在一起） */
    .tab-panel .card+.card,
    .tab-panel .result-wrap {
        margin-top: 1rem;
    }

    /* 顶部加载条：与仪表盘同款（.skeleton 自带闪动） */
    .dashboard-loading {
        display: none;
        justify-content: center;
        padding: 2rem 0;
    }

    .dashboard-loading[aria-busy="true"] {
        display: flex;
    }

    /* ---------- 标签页：上传识别 / 历史识别 / 能工智人 ---------- */
    .upload-tabs {
        display: flex;
        gap: .4rem;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid var(--ac-line, #f0e6ea);
        flex-wrap: wrap;
    }

    .upload-tab {
        appearance: none;
        border: 0;
        background: transparent;
        padding: .6rem 1rem;
        font: inherit;
        font-weight: 800;
        color: var(--ac-ink-500);
        cursor: pointer;
        border-bottom: 2px solid transparent;
        display: inline-flex;
        align-items: center;
        gap: .35rem;
    }

    .upload-tab:hover {
        color: var(--ac-pink-600);
    }

    .upload-tab.active {
        color: var(--ac-pink-700);
        border-bottom-color: var(--ac-pink-600);
    }

    .tab-panel {
        display: none;
    }

    .tab-panel.active {
        display: block;
    }

    .panel-head {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .panel-head h3 {
        margin: 0 0 .2rem;
    }

    .tag-human {
        display: inline-block;
        padding: .1rem .45rem;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-pink-100);
        color: var(--ac-pink-700);
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .06em;
        vertical-align: middle;
    }

    /* ---------- 结果：三通道分区（37ac / 大模型 / 能工智人） ---------- */
    .channel-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .channel-card {
        padding: 1.1rem 1.2rem;
    }

    .channel-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: .5rem;
        margin-bottom: .7rem;
    }

    .channel-title {
        font-weight: 800;
        color: var(--ac-ink-900);
    }

    .channel-empty {
        color: var(--ac-ink-500);
        font-size: .9rem;
    }

    .channel-chip {
        display: inline-block;
        padding: .1rem .45rem;
        border-radius: var(--ac-radius-pill);
        font-size: .72rem;
        font-weight: 700;
        background: var(--ac-surface-2, #f6f2f4);
        color: var(--ac-ink-600);
        white-space: nowrap;
    }

    .channel-chip.ok {
        background: var(--ac-pink-100);
        color: var(--ac-pink-700);
    }

    .channel-chip.run {
        background: #fff4d6;
        color: #8a6100;
    }

    .channel-chip.bad {
        background: #ffe3e3;
        color: #a3242f;
    }

    .channel-meta {
        font-size: .8rem;
        color: var(--ac-ink-500);
        margin-top: .5rem;
    }

    .result-tools {
        display: flex;
        gap: .6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-top: .2rem;
    }

    .task-id-line {
        font-family: var(--ac-font-mono);
        font-size: .8rem;
        color: var(--ac-ink-500);
    }

    /* ---------- 历史识别 ---------- */
    .history-list {
        display: flex;
        flex-direction: column;
        gap: .6rem;
    }

    .history-item {
        display: grid;
        grid-template-columns: 64px 1fr auto;
        gap: .8rem;
        align-items: center;
        padding: .6rem;
        border: 1px solid var(--ac-line, #f0e6ea);
        border-radius: var(--ac-radius-card);
    }

    .history-thumb {
        width: 64px;
        height: 64px;
        object-fit: cover;
        border-radius: var(--ac-radius-input);
        background: var(--ac-surface-2, #f6f2f4);
    }

    .history-line {
        display: flex;
        gap: .6rem;
        align-items: baseline;
        flex-wrap: wrap;
    }

    .history-id {
        font-weight: 700;
    }

    .history-time {
        font-size: .8rem;
        color: var(--ac-ink-500);
    }

    .history-chips {
        display: flex;
        gap: .35rem;
        flex-wrap: wrap;
        margin-top: .35rem;
    }

    .history-actions {
        display: flex;
        gap: .4rem;
    }

    /* ---------- 能工智人（人工通道） ---------- */
    .human-preview {
        margin: .4rem 0 1rem;
    }

    .human-preview img {
        max-width: 100%;
        max-height: 320px;
        border-radius: var(--ac-radius-card);
        border: 1px solid var(--ac-line, #f0e6ea);
    }

    .human-form {
        display: flex;
        flex-direction: column;
        gap: .9rem;
        max-width: 520px;
    }

    .human-form .req {
        color: var(--ac-danger, #d64550);
    }

    .name-suggest {
        display: flex;
        gap: .35rem;
        flex-wrap: wrap;
        margin-top: .4rem;
    }

    .name-suggest button {
        appearance: none;
        border: 1px solid var(--ac-line, #e6dade);
        background: var(--ac-surface, #fff);
        border-radius: var(--ac-radius-pill);
        padding: .15rem .6rem;
        font: inherit;
        font-size: .8rem;
        cursor: pointer;
    }

    .name-suggest button:hover {
        border-color: var(--ac-pink-400);
        color: var(--ac-pink-700);
    }

    .human-votes {
        margin-top: 1.2rem;
    }

    .vote-row {
        display: flex;
        gap: .6rem;
        align-items: baseline;
        padding: .45rem 0;
        border-bottom: 1px dashed var(--ac-line, #f0e6ea);
        font-size: .9rem;
        flex-wrap: wrap;
    }

    .vote-row .who,
    .vote-row .model-guess {
        color: var(--ac-ink-500);
        font-size: .78rem;
    }

    /* ---------- 结果详情弹层：把检测框坐标用起来 ---------- */
    .channel-card[data-channel] {
        cursor: pointer;
        transition: box-shadow var(--ac-dur-fast) var(--ac-ease-out), transform var(--ac-dur-fast) var(--ac-ease-out);
    }

    .channel-card[data-channel]:hover {
        box-shadow: var(--ac-shadow-float);
        transform: translateY(-1px);
    }

    .channel-card[data-channel]:focus-visible {
        outline: 2px solid var(--ac-pink-400);
        outline-offset: 2px;
    }

    .channel-detail-hint {
        margin-left: auto;
        font-size: .72rem;
        font-weight: 700;
        color: var(--ac-pink-700);
        background: var(--ac-pink-50);
        border-radius: var(--ac-radius-pill);
        padding: .1rem .5rem;
        white-space: nowrap;
    }

    .char-block[data-index] {
        cursor: pointer;
        border-radius: var(--ac-radius-input);
        transition: background var(--ac-dur-fast) var(--ac-ease-out);
    }

    .char-block[data-index]:hover {
        background: var(--ac-pink-50);
    }

    .detail-modal {
        width: min(1040px, calc(100vw - 2rem));
        max-height: 90vh;
        padding: 1.15rem 1.25rem;
    }

    .detail-head {
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        gap: .5rem;
        margin-bottom: .5rem;
    }

    .detail-title {
        margin-right: auto;
        font-family: var(--ac-font-display);
        font-weight: 800;
        font-size: 1.05rem;
    }

    .detail-tabs {
        display: flex;
        gap: .2rem;
        padding: .2rem;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-surface-2);
    }

    .detail-tab {
        border: none;
        background: transparent;
        color: var(--ac-ink-500);
        font: inherit;
        font-size: .82rem;
        font-weight: 700;
        padding: .22rem .7rem;
        border-radius: var(--ac-radius-pill);
        cursor: pointer;
        transition: background var(--ac-dur-fast) var(--ac-ease-out), color var(--ac-dur-fast) var(--ac-ease-out);
    }

    .detail-tab.active {
        background: var(--ac-surface);
        color: var(--ac-pink-700);
        box-shadow: var(--ac-shadow-card);
    }

    .detail-close {
        border: none;
        background: transparent;
        color: var(--ac-ink-500);
        font-size: 1rem;
        line-height: 1;
        padding: .3rem .45rem;
        border-radius: var(--ac-radius-pill);
        cursor: pointer;
    }

    .detail-close:hover {
        background: var(--ac-surface-2);
        color: var(--ac-ink-900);
    }

    .detail-meta {
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        gap: .5rem;
        flex-wrap: wrap;
        margin-bottom: .7rem;
        font-size: .8rem;
        color: var(--ac-ink-500);
    }

    .detail-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
        gap: 1rem;
        align-items: start;
    }

    .detail-stage {
        position: relative;
        border-radius: var(--ac-radius-input);
        background: var(--ac-surface-2);
        overflow: hidden;
    }

    .detail-stage img {
        display: block;
        width: 100%;
        height: auto;
    }

    .detail-stage.is-empty {
        min-height: 240px;
    }

    .detail-box {
        position: absolute;
        border: 2px solid var(--ac-pink-500);
        border-radius: 8px;
        background: rgba(222, 79, 141, .1);
        cursor: pointer;
        transition: background var(--ac-dur-fast) var(--ac-ease-out), box-shadow var(--ac-dur-fast) var(--ac-ease-out);
    }

    .detail-box.is-vote {
        border-color: var(--ac-mint);
        background: rgba(61, 189, 180, .12);
    }

    .detail-box.is-active {
        background: rgba(222, 79, 141, .24);
        box-shadow: 0 0 0 3px rgba(222, 79, 141, .22);
        z-index: 2;
    }

    .detail-box.is-vote.is-active {
        background: rgba(61, 189, 180, .26);
        box-shadow: 0 0 0 3px rgba(61, 189, 180, .22);
    }

    .detail-box .box-tag {
        position: absolute;
        left: -2px;
        top: -1.4rem;
        display: inline-block;
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        padding: .08rem .45rem;
        border-radius: var(--ac-radius-pill);
        background: var(--ac-pink-500);
        color: #fff;
        font-size: .7rem;
        font-weight: 700;
        font-style: normal;
    }

    .detail-box .box-tag.inside {
        top: .2rem;
        left: .25rem;
    }

    .detail-box.is-vote .box-tag {
        background: var(--ac-mint);
    }

    .detail-list {
        display: flex;
        flex-direction: column;
        gap: .5rem;
        max-height: 62vh;
        overflow-y: auto;
        padding-right: .2rem;
    }

    .detail-row {
        border: 1px solid var(--ac-line, #f0e6ea);
        border-radius: var(--ac-radius-input);
        padding: .55rem .7rem;
        cursor: pointer;
        transition: border-color var(--ac-dur-fast) var(--ac-ease-out), background var(--ac-dur-fast) var(--ac-ease-out);
    }

    .detail-row.is-active {
        border-color: var(--ac-pink-400);
        background: var(--ac-pink-50);
    }

    .detail-row-head {
        display: flex;
        align-items: center;
        gap: .45rem;
        flex-wrap: wrap;
    }

    .detail-row-head strong {
        color: var(--ac-ink-900);
    }

    .detail-idx {
        font-family: var(--ac-font-mono);
        font-size: .74rem;
        font-weight: 700;
        color: var(--ac-pink-700);
        background: var(--ac-pink-100);
        border-radius: var(--ac-radius-pill);
        padding: .05rem .4rem;
    }

    .detail-bbox {
        margin-top: .3rem;
        font-family: var(--ac-font-mono);
        font-size: .72rem;
        color: var(--ac-ink-500);
    }

    .detail-sub {
        margin-top: .3rem;
        font-size: .78rem;
        color: var(--ac-ink-500);
    }

    .detail-note,
    .detail-empty {
        font-size: .84rem;
        color: var(--ac-ink-500);
        padding: .3rem 0;
    }

    @media (max-width: 860px) {
        .detail-grid {
            grid-template-columns: minmax(0, 1fr);
        }

        .detail-list {
            max-height: none;
        }
    }

    @media (max-width: 720px) {
        .history-item {
            grid-template-columns: 56px 1fr;
        }

        .history-actions {
            grid-column: 1 / -1;
            justify-content: flex-end;
        }
    }
</style>

<div class="upload-page ac-container">
    <div class="page-head">
        <h2>上传识别</h2>
        <p>支持 JPG / PNG，最大 50MB，可拖拽上传。</p>
    </div>

    <!-- 三个入口：上传识别 / 历史识别 / 能工智人 -->
    <div class="upload-tabs" role="tablist">
        <button type="button" class="upload-tab active" data-tab="upload" role="tab" aria-selected="true">
            <i class="ph ph-cloud-arrow-up"></i>上传识别
        </button>
        <button type="button" class="upload-tab" data-tab="history" role="tab" aria-selected="false">
            <i class="ph ph-clock-counter-clockwise"></i>历史识别
        </button>
        <button type="button" class="upload-tab" data-tab="human" role="tab" aria-selected="false">
            <i class="ph ph-users-three"></i>能工智人
        </button>
    </div>

    <!-- 顶部加载条（三个标签共用，与仪表盘同款闪动） -->
    <div class="dashboard-loading" id="dashboard-loading" aria-busy="false">
        <span class="skeleton" style="width: 200px; height: 20px;"></span>
    </div>

    <!-- ① 上传识别 -->
    <section class="tab-panel active" id="panel-upload">

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

        <!-- 结果：按通道分区（37ac / 大模型 / 能工智人） -->
        <div class="result-wrap" id="resultWrap"></div>
    </section>

    <!-- ② 历史识别 -->
    <section class="tab-panel" id="panel-history">
        <div class="card">
            <div class="panel-head">
                <div>
                    <h3>历史识别</h3>
                    <p class="hint">保存在本机浏览器的最近识别记录（最多 20 条）；换设备或清缓存后会消失。</p>
                </div>
                <button type="button" class="btn btn-ghost btn-sm" id="btnClearHistory">清空记录</button>
            </div>
            <div id="historyList" class="history-list"></div>
        </div>

        <div class="card">
            <div class="panel-head">
                <div>
                    <h3>大家最近在识别</h3>
                    <p class="hint">服务端最近的识别任务（只含任务与各通道状态，不含结果）；「查看结果」可看这一单的三通道结果，「去投票」直接跳人工通道。</p>
                </div>
                <button type="button" class="btn btn-ghost btn-sm" id="btnRefreshFeed">刷新</button>
            </div>
            <div id="publicFeed" class="history-list"></div>
        </div>

        <div class="result-wrap" id="historyResultWrap"></div>
    </section>

    <!-- ③ 能工智人（人工通道） -->
    <section class="tab-panel" id="panel-human">
        <div class="card">
            <div class="panel-head">
                <div>
                    <h3>能工智人 <span class="tag-human">HUMAN</span></h3>
                    <p class="hint">挑一张还没人标注的图 → 在图上框住要认的角色 → 填作品和角色名。无需登录，同一浏览器重复提交算改票。</p>
                </div>
                <button type="button" class="btn btn-ghost btn-sm" id="btnRefreshHumanTasks">刷新任务</button>
            </div>
            <div id="humanTaskList" class="history-list"></div>
        </div>

        <div class="card human-annotate-card" id="humanAnnotateCard" hidden>
            <div class="panel-head">
                <div>
                    <h3 id="humanTaskTitle">从上面挑一张图开始标注</h3>
                    <p class="hint" id="humanTaskMeta">点列表里的「标注这张」</p>
                </div>
            </div>

            <div class="human-crop" id="humanCropWrap">
                <div class="human-crop-canvas" id="humanCropCanvas">
                    <div class="human-crop-placeholder" id="humanCropPlaceholder">
                        <i class="ph ph-selection-plus"></i>
                        <span>选好图后，在图上按住拖动框住要认的角色</span>
                    </div>
                    <img id="humanCropImage" src="" alt="" />
                </div>
                <div class="human-crop-side">
                    <span class="col-label">框选预览</span>
                    <div id="humanCropPreview" class="human-crop-preview"></div>
                    <div class="human-crop-actions">
                        <button type="button" class="btn btn-ghost btn-sm" id="btnHumanCropReset">清除选框</button>
                    </div>
                    <p class="hint">不框也可以，就按整图提交。</p>
                </div>
            </div>

            <form id="humanForm" class="human-form" novalidate>
                <div class="form-row">
                    <div class="field">
                        <label for="humanIp">作品 / IP <span class="req">*</span></label>
                        <input type="text" id="humanIp" class="input" list="humanIpOptions" placeholder="如：蔚蓝档案" required />
                        <datalist id="humanIpOptions"></datalist>
                    </div>
                    <div class="field">
                        <label for="humanName">角色名 <span class="req">*</span></label>
                        <input type="text" id="humanName" class="input" list="humanNameOptions" placeholder="如：阿洛娜" required />
                        <datalist id="humanNameOptions"></datalist>
                    </div>
                </div>
                <div id="humanNameSuggest" class="name-suggest"></div>
                <div class="field">
                    <label for="humanNote">备注</label>
                    <input type="text" id="humanNote" class="input" placeholder="可选，例如：侧面照 / 卡面" />
                </div>
                <div class="human-form-actions">
                    <button type="button" class="btn btn-secondary" id="btnAddCharacter">＋ 添加这个角色</button>
                    <button type="submit" class="btn btn-primary" id="btnSubmitVotes">提交标注</button>
                </div>
                <p class="hint">一张图可以标多个角色：框住一个 → 填作品 / 角色名 → 点「添加这个角色」，重复即可；最后一次性提交。多个人标注同一张图也没问题。</p>
            </form>

            <div id="humanPending" class="human-pending"></div>

            <div id="humanVotes" class="human-votes"></div>
        </div>
    </section>
</div>

<script type="module">
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

    /** 前端可选图片体积上限：50MB —— 提交前会压到最长边 512px，实际上传体积远小于此 */
    const MAX_SELECT_BYTES = 50 * 1024 * 1024;
    /** 后端 /api/upload 的请求体上限（Flask MAX_CONTENT_LENGTH = 10MB），压缩异常时用于兜底提示 */
    const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

    /** 识别通道：一次上传同时请求三条通道（后端 channels 参数） */
    const CHANNELS = ['37ac', 'llm', 'human'];
    /** 通道展示元数据（顺序即页面展示顺序） */
    const CHANNEL_META = [{
            key: '37ac',
            label: '37ac 模型',
            short: '37ac'
        },
        {
            key: 'llm',
            label: '大模型（LLM）',
            short: '大模型'
        },
        {
            key: 'human',
            label: '能工智人（人工）',
            short: '人工'
        },
    ];
    /** 本机历史记录（localStorage） */
    const HISTORY_KEY = '37ac_history';
    const HISTORY_MAX = 20;

    /**
     * 二次元图片识别工具（上传 → 处理 → 识别）
     */
    class AnimeDetector {
        constructor() {
            this.initElements();
            this.bindEvents();
            this.currentTab = 'upload';
            this.humanLoadedTask = null;
            this.humanTaskData = null;
            this.initTabs();
            this.state = {
                tempFile: null, // 原始临时文件
                cropInstance: null, // Cropper.js 实例
                croppedFile: null, // 最终裁剪文件
                originalImageURL: null, // 原图预览 URL
                hasCroppedImage: false, // 是否有裁剪后的图片
            };
            this.abortController = null;
            // 每次"新识别"自增：旧 SSE 流 / 旧轮询看到 epoch 变了就立刻作废，
            // 避免旧结果回写到新结果上造成闪烁
            this.updateEpoch = 0;
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
            this.loadingIndicator = document.getElementById('dashboard-loading');
            this.submitWrap = document.getElementById('submitWrap');

            // 裁剪相关
            this.enableCropCheckbox = document.getElementById('enableCrop');
            this.cropSubOptions = document.getElementById('cropSubOptions');
            this.cropModeSelect = document.getElementById('cropMode');

            // 链接上传
            this.linkInput = document.getElementById('linkInput');
            this.btnLoadLink = document.getElementById('btnLoadLink');

            // 选项组
            this.imageProcessingGroup = document.getElementById('imageProcessingGroup');

            // 历史识别
            this.historyList = document.getElementById('historyList');
            this.historyResultWrap = document.getElementById('historyResultWrap');
            this.btnClearHistory = document.getElementById('btnClearHistory');
            this.publicFeed = document.getElementById('publicFeed');
            this.btnRefreshFeed = document.getElementById('btnRefreshFeed');
            this.btnRefreshHumanTasks = document.getElementById('btnRefreshHumanTasks');

            // 能工智人（人工通道）
            this.humanForm = document.getElementById('humanForm');
            this.humanTaskList = document.getElementById('humanTaskList');
            this.humanTaskTitle = document.getElementById('humanTaskTitle');
            this.humanTaskMeta = document.getElementById('humanTaskMeta');
            this.humanAnnotateCard = document.getElementById('humanAnnotateCard');
            this.humanCropPlaceholder = document.getElementById('humanCropPlaceholder');
            this.humanCropCanvas = document.getElementById('humanCropCanvas');
            this.humanCropImage = document.getElementById('humanCropImage');
            this.humanCropPreview = document.getElementById('humanCropPreview');
            this.humanIp = document.getElementById('humanIp');
            this.humanIpOptions = document.getElementById('humanIpOptions');
            this.humanName = document.getElementById('humanName');
            this.humanNameOptions = document.getElementById('humanNameOptions');
            this.humanNameSuggest = document.getElementById('humanNameSuggest');
            this.btnHumanCropReset = document.getElementById('btnHumanCropReset');
            this.humanNote = document.getElementById('humanNote');
            this.humanVotes = document.getElementById('humanVotes');
            this.humanPending = document.getElementById('humanPending');
            this.btnAddCharacter = document.getElementById('btnAddCharacter');
            this.btnSubmitVotes = document.getElementById('btnSubmitVotes');
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

            // 历史识别：点条目看结果，点「去投票」跳人工通道
            if (this.btnClearHistory) {
                this.btnClearHistory.addEventListener('click', () => this.clearHistory());
            }
            if (this.historyList) {
                this.historyList.addEventListener('click', (e) => {
                    const item = e.target.closest('.history-item');
                    if (!item) return;
                    const taskId = item.getAttribute('data-task');
                    const btn = e.target.closest('button[data-role]');
                    if (btn && btn.getAttribute('data-role') === 'vote') {
                        this.selectHumanTask(taskId);
                    } else {
                        this.openHistoryTask(taskId);
                    }
                });
            }

            // 结果区的「去能工智人投票」
            document.addEventListener('click', (e) => {
                const btn = e.target.closest('button[data-role="goto-human"]');
                if (btn) this.selectHumanTask(btn.getAttribute('data-task'));
            });

            // 结果卡片：点开详情（检测框坐标 + 完整候选）；
            // 点到卡片里某个角色行，就在详情里直接聚焦那一项
            document.addEventListener('click', (e) => {
                if (e.target.closest('a')) return; // 萌娘百科等链接照旧
                const card = e.target.closest('.result-wrap .channel-card[data-channel]');
                if (!card) return;
                const wrap = card.closest('.result-wrap');
                const row = e.target.closest('[data-index]');
                this.openResultDetail(card.getAttribute('data-channel'),
                    row ? Number(row.getAttribute('data-index')) : null, wrap);
            });
            // 键盘可达：卡片聚焦后回车/空格也能打开
            document.addEventListener('keydown', (e) => {
                if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
                const card = e.target && e.target.closest ? e.target.closest('.result-wrap .channel-card[data-channel]') : null;
                if (!card) return;
                e.preventDefault();
                this.openResultDetail(card.getAttribute('data-channel'), null, card.closest('.result-wrap'));
            });

            // 能工智人：待标注列表（点「标注这张」）+ 刷新 + 清除选框 + 点候选双填
            if (this.humanTaskList) {
                this.humanTaskList.addEventListener('click', (e) => {
                    const item = e.target.closest('.history-item');
                    const btn = e.target.closest('button[data-role="annotate"]');
                    if (!item || !btn) return;
                    // 不管从哪个入口进来都滚到标注卡片（列表已经渲染好了，位置准）
                    this.selectHumanTask(item.getAttribute('data-task'));
                });
            }
            if (this.btnRefreshHumanTasks) {
                this.btnRefreshHumanTasks.addEventListener('click', () => this.loadHumanTaskList());
            }
            // 用户自己滚动/触摸时放弃自动定位，不跟用户抢滚动条
            ['wheel', 'touchstart'].forEach((evt) => {
                window.addEventListener(evt, () => {
                    this.autoScrollPending = false;
                    this.scrollAnim = null;
                }, {
                    passive: true
                });
            });
            if (this.btnHumanCropReset) {
                this.btnHumanCropReset.addEventListener('click', () => {
                    if (this.humanCropInstance) this.humanCropInstance.clear();
                    if (this.humanCropPreview) this.humanCropPreview.classList.add('flow-empty');
                });
            }
            if (this.humanCropImage) {
                // 图片就绪后再挂裁剪器（Cropper 需要图片尺寸）
                this.humanCropImage.addEventListener('load', () => {
                    this.humanImageLoading = false;
                    this.humanCropImage.style.display = 'block';
                    if (this.humanCropPlaceholder) this.humanCropPlaceholder.style.display = 'none';
                    if (this.humanCropCanvas) this.humanCropCanvas.classList.remove('flow-empty');
                    this.initHumanCropper();
                    // 图片只会把页面撑长，标注卡片自己在上面没动过位置：
                    // 所以只有"上次因为页面不够长、没滚到位"时才补一次，
                    // 否则就会看成"图片加载完又多滑了一段"。
                    if (this.scrollAnim && this.scrollAnim.clamped) this.scrollToAnnotateCard(0);
                });
                this.humanCropImage.addEventListener('error', () => {
                    // 只有正在加载真实图片时才当错误（清空 src 会触发假 error）
                    if (!this.humanImageLoading) return;
                    this.humanImageLoading = false;
                    this.humanCropImage.style.display = 'none';
                    // 卡片里不写死文案：保持流水效果，错误用 toast 提示
                    if (this.humanCropPlaceholder) this.humanCropPlaceholder.style.display = 'none';
                    if (this.humanCropCanvas) this.humanCropCanvas.classList.add('is-empty', 'flow-empty');
                    Notify.error('这张图已过期或被清理，换一张试试');
                });
            }
            if (this.humanNameSuggest) {
                this.humanNameSuggest.addEventListener('click', (e) => {
                    const btn = e.target.closest('button[data-name]');
                    if (!btn) return;
                    if (this.humanIp) this.humanIp.value = btn.getAttribute('data-ip') || '';
                    if (this.humanName) this.humanName.value = btn.getAttribute('data-name') || '';
                });
            }
            if (this.humanForm) {
                this.humanForm.addEventListener('submit', (e) => this.submitHumanVotes(e));
            }
            if (this.btnAddCharacter) {
                this.btnAddCharacter.addEventListener('click', () => this.addPendingVote());
            }
            if (this.humanPending) {
                this.humanPending.addEventListener('click', (e) => {
                    const btn = e.target.closest('button[data-role="remove-pending"]');
                    const item = e.target.closest('.pending-item');
                    if (!btn || !item) return;
                    this.removePendingVote(Number(item.getAttribute('data-i')));
                });
            }

            // 公共 feed（大家的识别）
            if (this.btnRefreshFeed) {
                this.btnRefreshFeed.addEventListener('click', () => this.loadPublicFeed());
            }
            if (this.publicFeed) {
                this.publicFeed.addEventListener('click', (e) => {
                    const item = e.target.closest('.history-item');
                    if (!item) return;
                    const taskId = item.getAttribute('data-task');
                    const btn = e.target.closest('button[data-role]');
                    if (btn && btn.getAttribute('data-role') === 'vote') {
                        this.selectHumanTask(taskId);
                    } else {
                        this.openHistoryTask(taskId);
                    }
                });
            }
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

            if (file.size > MAX_SELECT_BYTES) {
                Notify.error(`图片大小不能超过 ${MAX_SELECT_BYTES / 1024 / 1024}MB`);
                return;
            }

            this.state.tempFile = file;
            this.resetCropState();

            // 显示预览，清空上次结果
            this.updatePreview(file);
            this.hideResult();

            // 显示处理选项
            this.imageProcessingGroup.disabled = false;

            // 手动裁剪模式下：图片更新后同步刷新裁剪器（replace 保留选框设置）
            if (this.state.cropInstance) {
                this.state.cropInstance.replace(this.state.originalImageURL);
            } else if (this.enableCropCheckbox.checked && this.cropModeSelect.value === 'manual') {
                this.initCropper();
            }

            // 图片加载完成后，将页面滚动到合适位置
            this.scrollToPreview();

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

        /* 处理图片（裁剪 + 压缩） */
        async processImage() {
            if (!this.state.tempFile) {
                Notify.error('请先选择图片');
                return null;
            }

            let processedFile = this.state.tempFile;

            try {
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

                // 压缩：用户确认好的图片，提交前把最长边压到 512px
                // （与后端 IMAGE_COMPRESS_MAX_SIDE / IMAGE_COMPRESS_QUALITY 口径一致）
                processedFile = await this.compressImage(processedFile, 512, 0.85);

                // 兜底：极端情况下压缩没生效（解码/编码失败会退回原图），别把超限文件发给后端
                if (processedFile.size > MAX_UPLOAD_BYTES) {
                    Notify.error(`压缩后仍有 ${(processedFile.size / 1024 / 1024).toFixed(1)}MB，超过后台上限，请换一张更小的图片`);
                    return null;
                }

                return processedFile;
            } catch (err) {
                console.error('图片处理失败:', err);
                Notify.error('图片处理失败: ' + err.message);
                return null;
            }
        }

        /**
         * 压缩图片：最长边超过 maxSide 时等比缩放并重新编码为 JPEG
         * - 已经小于等于 maxSide 的图片原样返回（不重新编码，避免无谓画质损失）
         * - 透明像素铺白底，避免转 JPEG 后出现黑块
         * - 任意环节失败都退回原图，不阻断识别
         * @param {File} file
         * @param {number} maxSide 最长边上限（px），默认 512，与后端 IMAGE_COMPRESS_MAX_SIDE 一致
         * @param {number} quality JPEG 质量，默认 0.85，与后端 IMAGE_COMPRESS_QUALITY 一致
         * @returns {Promise<File>}
         */
        async compressImage(file, maxSide = 512, quality = 0.85) {
            let bitmap;
            try {
                bitmap = await createImageBitmap(file);
            } catch (err) {
                console.warn('[upload] 无法解码图片，跳过压缩:', err);
                return file;
            }

            const longest = Math.max(bitmap.width, bitmap.height);
            if (longest <= maxSide) {
                if (bitmap.close) bitmap.close();
                return file;
            }

            const srcWidth = bitmap.width;
            const srcHeight = bitmap.height;
            const scale = maxSide / longest;
            const width = Math.max(1, Math.round(srcWidth * scale));
            const height = Math.max(1, Math.round(srcHeight * scale));

            this.updateProgressStatus(`正在压缩图片（${srcWidth}×${srcHeight} → ${width}×${height}）`);

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(bitmap, 0, 0, width, height);
            if (bitmap.close) bitmap.close();

            const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
            if (!blob) {
                console.warn('[upload] 压缩编码失败，改用原图');
                return file;
            }

            const compressed = new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', {
                type: 'image/jpeg'
            });
            console.log(`[upload] 图片压缩: ${srcWidth}×${srcHeight} ${(file.size / 1024).toFixed(0)}KB → ${width}×${height} ${(compressed.size / 1024).toFixed(0)}KB`);
            return compressed;
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

        /* 图片加载完成后，将页面滚动到合适位置（手动裁剪时滚动到裁剪器，否则滚动到预览） */
        scrollToPreview() {
            const target = (this.state.cropInstance ||
                    (this.enableCropCheckbox.checked && this.cropModeSelect.value === 'manual')) ?
                document.getElementById('cropperWrap') :
                this.previewWrap;
            const scroll = () => {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            };
            // 等待图片真正加载完成再滚动，避免高度未定导致滚动位置偏移
            if (this.previewImage.complete) {
                scroll();
            } else {
                this.previewImage.onload = scroll;
            }
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

            // 新请求进来：先拦掉旧的流与轮询，旧结果一律不再回写
            const epoch = this.beginUpdate();

            this.showLoading(true);
            this.hideResult();

            try {
                // 处理图片
                const processedFile = await this.processImage();
                if (epoch !== this.updateEpoch) return;
                if (!processedFile) {
                    this.showLoading(false);
                    return;
                }

                // 更新预览
                this.updatePreview(processedFile);

                // 构造 FormData（字段名 file 与后端约定一致）
                const formData = new FormData();
                formData.append('file', processedFile);
                // 推理模型选择：37ac / llm（来自 GET /models）
                // 多通道：一次上传同时请求 37ac / 大模型 / 能工智人
                formData.append('channels', CHANNELS.join(','));

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
                // 完成时携带 result（节点返回的预测结构：class_probs 按概率降序，第一项即最佳结果）
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let finalResult = null;
                let finalChannelStatus = null;
                let streamError = null;
                let streamTimeout = false;
                this.currentTaskId = null; // 记录 task_id，用于 SSE 完成事件丢失时回退查询

                while (true) {
                    if (epoch !== this.updateEpoch) {
                        // 已经有新的识别请求了：丢弃这条流
                        try {
                            await reader.cancel();
                        } catch (e) {
                            // 忽略
                        }
                        break;
                    }

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
                                    finalChannelStatus = jsonData.channel_status || finalChannelStatus;
                                }
                                // 部分通道已完成（例如 37ac 比 llm 快）：立刻渲染，别干等
                                this.renderPartialResult(jsonData, epoch);

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
                                finalChannelStatus = jsonData.channel_status || finalChannelStatus;
                            }
                            this.renderPartialResult(jsonData, epoch);
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
                    this.showResult(finalResult, finalChannelStatus);
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
                if (epoch !== this.updateEpoch) return; // 旧请求的报错直接丢弃，不打扰新请求
                if (error.name === 'AbortError') {
                    this.updateProgressStatus('识别已取消');
                    this.showError('识别已取消');
                } else {
                    console.error('识别请求失败:', error);
                    this.showError(error.message || '网络连接失败，请检查网络后重试');
                }
            } finally {
                if (epoch === this.updateEpoch) {
                    this.showLoading(false);
                    this.abortController = null;
                } else {
                    this.setBusy(false); // 旧请求只把 busy 计数还回去，不动新请求的加载态
                }
            }
        }

        /* 事件里带了部分通道结果就立刻渲染（partial/completed 都算） */
        renderPartialResult(eventData, epoch) {
            if (epoch !== undefined && epoch !== this.updateEpoch) return; // 旧请求的结果丢掉
            const data = eventData || {};
            const payload = data.channel_results || data.result;
            if (!payload) return;
            const isPartial = data.status === 'partial';
            if (!isPartial && data.status !== 'completed') return;
            // 旧字段 result 是 characters 数组；新字段 channel_results 是分通道对象
            const result = Array.isArray(payload) ? {
                characters: payload
            } : payload;
            if (!result || (Array.isArray(result.characters) && result.characters.length === 0 &&
                    !result['37ac'] && !result.llm && !result.human)) {
                return;
            }
            this.hasPartialResult = true;
            this.showResult(result, data.channel_status || {});
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
                    // 任务一建立就记进本机历史，失败也能回看
                    if (eventData.task_id) {
                        this.addHistoryEntry(eventData.task_id, {
                            channel_status: eventData.channel_status || {}
                        });
                    }
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

                case 'partial':
                    // 有通道先完成（例如 37ac），其余仍在跑：结果区已经先渲染出来了
                    this.updateProgressStatus('部分通道已完成，结果先展示，其余通道继续等待…');
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

        /* 顶部加载条（与仪表盘一致）：计数式，避免并发请求提前收起 */
        setBusy(active) {
            if (!this.loadingIndicator) return;
            this.busyCount = Math.max(0, (this.busyCount || 0) + (active ? 1 : -1));
            this.loadingIndicator.setAttribute('aria-busy', this.busyCount > 0 ? 'true' : 'false');
        }

        /* 显示加载状态 */
        showLoading(show) {
            if (show) {
                this.loadingWrap.classList.add('active');
            } else {
                this.loadingWrap.classList.remove('active');
            }
            this.setBusy(show);
        }

        /* 把三通道结果渲染进某个结果区；原始 payload 挂在元素上，供详情弹层取用 */
        renderChannelsInto(wrap, result, status, taskId) {
            if (!wrap) return;
            wrap.__detailPayload = {
                result: result || {},
                status: status || {},
                taskId: taskId || ''
            };
            this.lastResultPayload = wrap.__detailPayload;
            wrap.innerHTML = this.generateChannelsHTML(result, status, {
                taskId: taskId
            });
            wrap.classList.add('active');
            this.refreshDetailIfOpen(taskId);
        }

        /* 详情弹层开着、且是同一条任务：跟着刷新（新通道/新人工票到了，框也要跟着更新） */
        refreshDetailIfOpen(taskId) {
            if (this.detailDialog && this.detailDialog.open && this.detailState &&
                (this.detailState.taskId || '') === (taskId || '')) {
                this.renderDetail();
            }
        }

        /* 显示结果：按通道分区（37ac / 大模型 / 能工智人） */
        showResult(data, channelStatus) {
            // 节点结果失败（模型缺失、图片损坏等）：只有所有通道都失败才算整体失败
            if (!data || data.error) {
                this.showError((data && data.error) || '识别失败，请稍后重试');
                return;
            }
            const taskId = this.currentTaskId;
            const status = channelStatus || (data && data.channel_status) || {};
            // 详情弹层要用：整份结果（含 characters[].bbox 检测框）+ 通道状态 + task_id
            this.lastResultPayload = {
                result: data,
                status: status,
                taskId: taskId
            };
            this.renderChannelsInto(this.resultWrap, data, status, taskId);
            this.resultWrap.classList.add('active');
            if (taskId) {
                this.updateHistoryEntry(taskId, {
                    channel_status: status
                });
                this.renderHistory();
                this.startChannelRefresh(taskId);
            }
        }

        /* 生成概率条目 HTML（统一字段：{name, prob(0-100)}） */
        generateProbabilityItem(item) {
            const percentage = (Number(item.prob) || 0).toFixed(2);
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
                            this.showResult(result, data.channel_status);
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

                // 复用统一的图片加载流程（预览 / 裁剪器刷新 / 滚动 / 选项启用）
                this.handleFile(file);
                Notify.success('图片加载完成');
            } catch (err) {
                console.error('从链接加载图片失败:', err);
                Notify.error('无法从链接加载图片: ' + err.message);
            } finally {
                this.showLoading(false);
            }
        }

        /* 开始一次新的识别：作废旧流 + 旧轮询，返回本次的 epoch */
        beginUpdate() {
            this.updateEpoch = (this.updateEpoch || 0) + 1;
            this.stopChannelRefresh();
            if (this.abortController) {
                try {
                    this.abortController.abort();
                } catch (e) {
                    // 忽略：只是作废旧请求
                }
                this.abortController = null;
            }
            return this.updateEpoch;
        }

        /* 停掉结果轮询 */
        stopChannelRefresh() {
            if (this.channelTimer) {
                clearTimeout(this.channelTimer);
            }
            this.channelTimer = null;
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
            this.stopChannelRefresh();
        }

        /* ==================== 标签页：上传识别 / 历史识别 / 能工智人 ==================== */
        initTabs() {
            this.tabs = Array.from(document.querySelectorAll('.upload-tab'));
            this.panels = {
                upload: document.getElementById('panel-upload'),
                history: document.getElementById('panel-history'),
                human: document.getElementById('panel-human'),
            };
            this.tabs.forEach((tab) => {
                tab.addEventListener('click', () => this.switchTab(tab.getAttribute('data-tab')));
            });
            const params = new URLSearchParams(window.location.search || '');
            // ?scrolldebug=1：把每一次滚动决策打到 console（排查"多滑一段 / 回弹"用）
            this.scrollDebug = params.get('scrolldebug') === '1';
            const hash = (window.location.hash || '').replace('#', '');
            const wanted = params.get('tab') || hash;
            if (wanted && this.panels[wanted]) {
                this.switchTab(wanted);
            }
            // ?task=<id>&tab=human 直达某张图去标注
            const taskParam = (params.get('task') || '').trim();
            if (taskParam) {
                this.switchTab('human');
                this.loadHumanTask(taskParam);
                this.scheduleAnnotateScroll();
            }
        }

        switchTab(name) {
            if (!this.panels || !this.panels[name]) return;
            this.currentTab = name;
            this.tabs.forEach((tab) => {
                const active = tab.getAttribute('data-tab') === name;
                tab.classList.toggle('active', active);
                tab.setAttribute('aria-selected', active ? 'true' : 'false');
            });
            Object.keys(this.panels).forEach((key) => {
                this.panels[key].classList.toggle('active', key === name);
            });
            if (name === 'history') {
                this.renderHistory();
                this.loadPublicFeed();
                this.refreshHistoryStatuses();
            }
            if (name === 'human') {
                this.renderHumanPanel();
            } else {
                this.autoScrollPending = false;
            }
        }

        /* ==================== 加载骨架（仪表盘同款流水卡片，不写字） ==================== */
        skeletonListHtml(count) {
            const one = '<div class="skeleton-card">' +
                '<span class="sk-thumb flow-empty"></span>' +
                '<span class="sk-body">' +
                '<span class="sk-line flow-empty" style="width:42%"></span>' +
                '<span class="sk-line flow-empty" style="width:72%;margin-top:.5rem"></span>' +
                '<span class="sk-chip flow-empty" style="margin-top:.5rem"></span>' +
                '</span>' +
                '<span class="sk-btn flow-empty"></span>' +
                '</div>';
            return new Array(count || 3).fill(one).join('');
        }

        skeletonChannelsHtml(count) {
            const one = '<div class="card channel-card">' +
                '<div class="channel-head"><span class="sk-line flow-empty" style="width:38%"></span></div>' +
                '<span class="sk-line flow-empty" style="width:88%"></span>' +
                '<span class="sk-line flow-empty" style="width:74%;margin-top:.55rem"></span>' +
                '<span class="sk-line flow-empty" style="width:56%;margin-top:.55rem"></span>' +
                '</div>';
            return '<div class="channel-grid">' + new Array(count || 3).fill(one).join('') + '</div>';
        }

        /* ==================== 三通道结果（37ac / 大模型 / 能工智人） ==================== */
        channelState(channelStatus, key, result) {
            if (channelStatus && channelStatus[key]) return channelStatus[key];
            const section = (result || {})[key];
            return (section && section.status) || 'missing';
        }

        stateLabel(state) {
            const map = {
                queued: '排队中',
                waiting: '等待节点',
                assigned: '已分配',
                processing: '识别中',
                completed: '已完成',
                partial: '部分完成',
                failed: '失败',
                error: '失败',
                awaiting: '等待人工',
                missing: '未请求',
                unknown: '未知',
            };
            return map[state] || state || '未知';
        }

        stateClass(state) {
            if (state === 'completed') return 'ok';
            if (state === 'failed' || state === 'error') return 'bad';
            if (state === 'missing') return '';
            return 'run';
        }

        channelCard(title, state, bodyHtml, metaHtml, key) {
            // data-channel：整张卡片可点开详情（检测框坐标就画在详情里）
            const attr = key ? ' data-channel="' + escapeHtml(key) + '" role="button" tabindex="0" title="点开看检测框与完整候选"' : '';
            let html = '<div class="card channel-card"' + attr + '>';
            html += '<div class="channel-head">';
            html += '<span class="channel-title">' + title + '</span>';
            if (key) html += '<span class="channel-detail-hint">详情</span>';
            html += '<span class="channel-chip ' + this.stateClass(state) + '">' + this.stateLabel(state) + '</span>';
            html += '</div>';
            html += bodyHtml || '<div class="channel-empty">暂无结果</div>';
            if (metaHtml) html += metaHtml;
            html += '</div>';
            return html;
        }

        /* 拆分候选：优先用后端给的 ip / name_zh，否则按 "IP/角色" 拆 */
        splitLabel(item) {
            const src = item || {};
            const raw = String(src.name || src.name_zh || '');
            const parts = raw.split('/').map((s) => s.trim()).filter(Boolean);
            const ip = src.ip || (parts.length > 1 ? parts[0] : '');
            const name = src.name_zh || (parts.length > 1 ? parts[1] : (parts[0] || ''));
            return {
                ip: ip,
                name: name,
                raw: raw
            };
        }

        /* 萌娘百科跳转（按角色名搜） */
        moegirlHtml(name) {
            if (!name || name === '未知') return '';
            return '<a class="result-link" target="_blank" rel="nofollow" href="https://zh.moegirl.org.cn/' +
                encodeURIComponent(name) + '">萌娘百科</a>';
        }

        /* 一行候选：角色名 + IP 徽章 + 概率条 + 百分比（首行附萌娘百科） */
        candidateRowHtml(item, withLink) {
            const pct = (Number(item && item.prob) || 0).toFixed(2);
            const label = this.splitLabel(item);
            let nameHtml = escapeHtml(label.name || '未知');
            if (label.ip && label.ip !== label.name) {
                nameHtml += '<span class="badge badge-neutral cand-ip">' + escapeHtml(label.ip) + '</span>';
            }
            let html = '<div class="prob-item">';
            html += '<span class="name">' + nameHtml + '</span>';
            html += '<span class="prob-bar"><i style="width:' + pct + '%"></i></span>';
            html += '<span class="pct">' + pct + '%</span>';
            html += '</div>';
            if (withLink && label.name) {
                html += '<div class="cand-link">' + this.moegirlHtml(label.name) + '</div>';
            }
            return html;
        }

        /* 候选列表（首行带萌娘百科跳转） */
        candidatesHtml(list, limit) {
            const probs = (list || []).slice(0, limit || 5);
            if (!probs.length) return '';
            let html = '';
            probs.forEach((p, i) => {
                html += this.candidateRowHtml(p, i === 0);
            });
            return html;
        }

        /* 通道内部的失败信息（后端可能 status=completed 但 success=false + error） */
        channelErrorHtml(section, state) {
            if (!section) {
                return (state === 'failed' || state === 'error') ? '<div class="channel-error">该通道识别失败</div>' : '';
            }
            const err = section.error || (section.success === false ? (section.message || '未识别出结果') : '');
            if (!err) return '';
            return '<div class="channel-error">' + escapeHtml(String(err)) + '</div>';
        }

        /* 37ac 通道：多人物 + 候选列表 */
        generate37acCard(data, status) {
            const state = this.channelState(status, '37ac', data);
            const section = (data && data['37ac']) || ((data && (data.characters || data.class_probs)) ? data : null);
            let body = '';

            if (section && Array.isArray(section.characters) && section.characters.length) {
                let meta = '检出 ' + section.characters.length + ' 个人物';
                if (section.crop_method) meta += ' · 裁剪 ' + escapeHtml(section.crop_method);
                body += '<div class="channel-meta">' + meta + '</div>';
                section.characters.slice(0, 5).forEach((c) => {
                    const top = (c.class_probs && c.class_probs[0]) || {};
                    const label = this.splitLabel(top);
                    body += '<div class="char-block" data-index="' + (Number(c.index) || 0) + '">';
                    body += '<div class="char-head">';
                    body += '<span class="char-index">#' + (Number(c.index) + 1) + '</span>';
                    body += '<span class="char-name">' + escapeHtml(label.name || '未知') + '</span>';
                    if (label.ip && label.ip !== label.name) {
                        body += '<span class="badge badge-neutral cand-ip">' + escapeHtml(label.ip) + '</span>';
                    }
                    body += '<span class="mono char-conf">' + (Number(c.confidence) || 0).toFixed(2) + '%</span>';
                    if (label.name) body += ' ' + this.moegirlHtml(label.name);
                    body += '</div>';
                    body += this.candidatesHtml(c.class_probs, 3);
                    body += '</div>';
                });
            } else if (section && Array.isArray(section.class_probs) && section.class_probs.length) {
                body += this.candidatesHtml(section.class_probs, 5);
            }
            body += this.channelErrorHtml(section, state);

            return this.channelCard('37ac 模型', state, body, null, '37ac');
        }

        /* 大模型通道：候选列表 */
        generateLlmCard(data, status) {
            const state = this.channelState(status, 'llm', data);
            const section = (data && data['llm']) || null;
            let body = '';
            if (section && Array.isArray(section.class_probs) && section.class_probs.length) {
                body += this.candidatesHtml(section.class_probs, 5);
                const features = (section.features_used && section.features_used.length) ? section.features_used : (section.tags || []);
                if (features.length) {
                    body += '<div class="channel-meta">依据：' + escapeHtml(features.slice(0, 4).join('、')) + '</div>';
                }
            }
            body += this.channelErrorHtml(section, state);
            return this.channelCard('大模型（LLM）', state, body, null, 'llm');
        }

        /* 能工智人通道：人工票列表 */
        generateHumanCard(data, status) {
            const state = this.channelState(status, 'human', data);
            const section = (data && data['human']) || {};
            const votes = section.votes || [];
            let body = '';
            if (votes.length) {
                body += this.votesHtml(votes);
            } else {
                body += '<div class="channel-empty">还没有人工票 —— 切到「能工智人」投一票</div>';
            }
            return this.channelCard('能工智人（人工）', state, body, null, 'human');
        }

        votesHtml(votes) {
            let html = '';
            (votes || []).forEach((v) => {
                const guess = v.model_guess ? (v.model_guess.name || v.model_guess) : '';
                const label = this.splitLabel({
                    name: v.name,
                    ip: v.ip,
                    name_zh: v.name_zh
                });
                html += '<div class="vote-row">';
                html += '<strong>' + escapeHtml(label.name || '?') + '</strong>';
                if (label.ip && label.ip !== label.name) {
                    html += '<span class="badge badge-neutral cand-ip">' + escapeHtml(label.ip) + '</span>';
                }
                if (v.character_index !== undefined && v.character_index !== null) {
                    html += '<span class="channel-chip">#' + (Number(v.character_index) + 1) + '</span>';
                }
                if (!v.bbox && !v.bbox_percent) {
                    html += '<span class="channel-chip">整图</span>';
                }
                if (label.name) html += this.moegirlHtml(label.name);
                if (guess) html += '<span class="model-guess">模型猜测：' + escapeHtml(guess) + '</span>';
                if (v.note) html += '<span class="who">' + escapeHtml(v.note) + '</span>';
                html += '<span class="who">' + escapeHtml(v.voter || v.source || '') + '</span>';
                html += '</div>';
            });
            return html;
        }

        /**
         * 生成三通道结果 HTML
         * @param {object} result 任务结果（含 37ac / llm / human 分段）
         * @param {object} channelStatus {通道: 状态}
         * @param {object} options {taskId}
         */
        generateChannelsHTML(result, channelStatus, options) {
            const opts = options || {};
            const data = result || {};
            const status = channelStatus || {};
            let html = '<div class="channel-grid">';
            html += this.generate37acCard(data, status);
            html += this.generateLlmCard(data, status);
            html += this.generateHumanCard(data, status);
            html += '</div>';

            if (opts.taskId) {
                html += '<div class="card result-card"><div class="result-tools">';
                html += '<span class="task-id-line">任务 ID：' + escapeHtml(opts.taskId) + '</span>';
                html += '<button type="button" class="btn btn-secondary btn-sm" data-role="goto-human" data-task="' + escapeHtml(opts.taskId) + '">去能工智人投票</button>';
                html += '</div></div>';
            }
            return html;
        }

        /* ==================== 结果详情弹层（把检测框坐标用起来） ==================== */
        /* 统一成百分比框：服务端 bbox 是 0-1，bbox_percent 是 0-100 */
        boxPercentOf(entry) {
            const src = entry || {};
            const pct = src.bbox_percent;
            if (this.validBox(pct)) {
                return {
                    x: Number(pct.x),
                    y: Number(pct.y),
                    w: Number(pct.w),
                    h: Number(pct.h)
                };
            }
            const bbox = src.bbox;
            if (this.validBox(bbox)) {
                return {
                    x: Number(bbox.x) * 100,
                    y: Number(bbox.y) * 100,
                    w: Number(bbox.w) * 100,
                    h: Number(bbox.h) * 100
                };
            }
            return null;
        }

        validBox(box) {
            if (!box || typeof box !== 'object') return false;
            const nums = ['x', 'y', 'w', 'h'].map((k) => Number(box[k]));
            if (nums.some((n) => !isFinite(n))) return false;
            return nums[2] > 0 && nums[3] > 0;
        }

        /* 摊平某个通道的结果为详情行（带框的才有 box） */
        detailEntries(key, result) {
            const section = ((result || {})[key]) || {};
            const rows = [];
            if (key === 'human') {
                ((section.votes) || []).forEach((v) => {
                    const label = this.splitLabel(v);
                    rows.push({
                        i: rows.length,
                        no: rows.length + 1,
                        title: label.name || '?',
                        ip: label.ip === label.name ? '' : label.ip,
                        prob: null,
                        box: this.boxPercentOf(v),
                        vote: true,
                        voter: v.voter || v.source || '',
                        note: v.note || '',
                        ref: (v.character_index === undefined || v.character_index === null) ? null : (Number(v.character_index) + 1),
                        cands: [],
                    });
                });
                return rows;
            }
            const chars = (key === '37ac' && Array.isArray(section.characters)) ? section.characters : [];
            if (chars.length) {
                chars.forEach((c, i) => {
                    const list = c.class_probs || [];
                    const top = list[0] || {};
                    const label = this.splitLabel(top);
                    rows.push({
                        i: rows.length,
                        no: (Number(c.index) || 0) + 1 || (i + 1),
                        title: label.name || '未知',
                        ip: label.ip === label.name ? '' : label.ip,
                        prob: Number(top.prob) || 0,
                        box: this.boxPercentOf(c),
                        detector: Number(c.detector_confidence) || 0,
                        cands: list.slice(0, 5),
                    });
                });
                return rows;
            }
            // 大模型 / 没有 characters 的 37ac：只有候选，没有框
            ((section.class_probs) || []).slice(0, 8).forEach((p) => {
                const label = this.splitLabel(p);
                rows.push({
                    i: rows.length,
                    no: rows.length + 1,
                    title: label.name || '未知',
                    ip: label.ip === label.name ? '' : label.ip,
                    prob: Number(p.prob) || 0,
                    box: null,
                    cands: [],
                });
            });
            return rows;
        }

        detailRowHtml(row) {
            let html = '<div class="detail-row" data-row="' + row.i + '">';
            html += '<div class="detail-row-head">';
            html += '<span class="detail-idx">#' + row.no + '</span>';
            html += '<strong>' + escapeHtml(row.title) + '</strong>';
            if (row.ip) html += '<span class="badge badge-neutral cand-ip">' + escapeHtml(row.ip) + '</span>';
            if (row.prob !== null && row.prob !== undefined) {
                html += '<span class="mono" style="margin-left:auto">' + row.prob.toFixed(2) + '%</span>';
            }
            html += '</div>';
            if (row.box) {
                html += '<div class="detail-bbox">框 x ' + row.box.x.toFixed(1) + '% · y ' + row.box.y.toFixed(1) +
                    '% · w ' + row.box.w.toFixed(1) + '% · h ' + row.box.h.toFixed(1) + '%</div>';
            } else {
                html += '<div class="detail-bbox">' + (row.vote ? '整图（这票没框）' : '无检测框') + '</div>';
            }
            if (row.cands && row.cands.length > 1) {
                html += '<div class="detail-sub">其它候选：' + row.cands.slice(1).map((p) => {
                    const l = this.splitLabel(p);
                    return escapeHtml((l.ip ? l.ip + '/' : '') + (l.name || '?')) + ' ' + (Number(p.prob) || 0).toFixed(1) + '%';
                }).join(' · ') + '</div>';
            }
            if (row.vote) {
                const extra = [];
                if (row.voter) extra.push(row.voter);
                if (row.note) extra.push(row.note);
                if (row.ref) extra.push('沿用模型框 #' + row.ref);
                if (extra.length) html += '<div class="detail-sub">' + escapeHtml(extra.join(' · ')) + '</div>';
            } else if (row.detector) {
                html += '<div class="detail-sub">检测器置信度 ' + row.detector.toFixed(3) + '</div>';
            }
            html += '</div>';
            return html;
        }

        ensureDetailDialog() {
            if (this.detailDialog) return this.detailDialog;
            const dialog = document.createElement('dialog');
            dialog.className = 'ac-modal detail-modal';
            dialog.setAttribute('aria-label', '识别详情');
            document.body.appendChild(dialog);
            // 点四周空白处关闭；Esc 由 <dialog> 原生处理
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) dialog.close();
            });
            dialog.addEventListener('close', () => {
                this.detailState = null;
            });
            this.detailDialog = dialog;
            return dialog;
        }

        /**
         * 打开详情弹层
         * @param {string} channelKey 37ac / llm / human
         * @param {number|null} index 聚焦第几项（点卡片里的某个角色行时传）
         * @param {Element|null} wrap 结果区元素（payload 挂在它上面）
         */
        openResultDetail(channelKey, index, wrap) {
            const payload = (wrap && wrap.__detailPayload) || this.lastResultPayload;
            if (!payload || !payload.result) {
                Notify.info('这条记录还没有结果，先识别一次');
                return;
            }
            const dialog = this.ensureDetailDialog();
            // 切通道重渲染时仍用同一份 payload（点的是哪个结果区就用哪份）
            dialog.__payload = payload;
            const fallback = payload.result['37ac'] ? '37ac' : CHANNELS[0];
            const key = CHANNELS.indexOf(channelKey) >= 0 ? channelKey : fallback;
            this.detailState = {
                key: key,
                focus: (index === null || index === undefined || isNaN(Number(index))) ? null : String(index),
                taskId: payload.taskId || '',
            };
            this.renderDetail();
            if (!dialog.open) {
                if (typeof dialog.showModal === 'function') dialog.showModal();
                else dialog.setAttribute('open', '');
            }
        }

        renderDetail() {
            const dialog = this.detailDialog;
            const state = this.detailState;
            if (!dialog || !state) return;
            const payload = (dialog.__payload || this.lastResultPayload) || {};
            const result = payload.result || {};
            const status = payload.status || {};
            const key = state.key;
            const meta = CHANNEL_META.find((m) => m.key === key) || CHANNEL_META[0];
            const stateName = this.channelState(status, key, result);
            const rows = this.detailEntries(key, result);
            const boxes = rows.filter((r) => r.box);
            const taskId = payload.taskId || state.taskId || '';

            let html = '';
            html += '<div class="detail-head">';
            html += '<div class="detail-title">' + escapeHtml(meta.label) + ' · 详情</div>';
            html += '<div class="detail-tabs">' + CHANNEL_META.map((m) =>
                '<button type="button" class="detail-tab' + (m.key === key ? ' active' : '') +
                '" data-detail-channel="' + m.key + '">' + escapeHtml(m.short) + '</button>').join('') + '</div>';
            html += '<button type="button" class="detail-close" data-detail-close aria-label="关闭">✕</button>';
            html += '</div>';

            html += '<div class="detail-meta">';
            html += '<span class="channel-chip ' + this.stateClass(stateName) + '">' + this.stateLabel(stateName) + '</span>';
            if (taskId) html += '<span class="mono">' + escapeHtml(String(taskId).slice(0, 8)) + '…</span>';
            html += '<span>' + (rows.length ? ('共 ' + rows.length + ' 项' + (boxes.length ? ' · 带检测框 ' + boxes.length + ' 个' : ' · 无检测框')) : '暂无结果') + '</span>';
            html += '</div>';

            html += '<div class="modal-body">';
            if (!rows.length) {
                html += '<div class="detail-empty">这个通道还没有结果（' + escapeHtml(this.stateLabel(stateName)) + '）</div>';
            } else {
                html += '<div class="detail-grid">';
                html += '<div class="detail-stage-wrap">';
                if (taskId) {
                    // 图片没尺寸前用占位高度撑住，否则百分比定位的框会塌在一起；加载完就交给图片本身
                    html += '<div class="detail-stage is-empty" id="detailStage">';
                    html += '<img id="detailImage" class="flow-empty" alt="原图" src="/api/tasks/' + encodeURIComponent(taskId) + '/image?max_side=1280">';
                    boxes.forEach((r) => {
                        const b = r.box;
                        const inside = b.y < 8 ? ' inside' : '';
                        html += '<span class="detail-box' + (r.vote ? ' is-vote' : '') + '" data-box="' + r.i +
                            '" style="left:' + b.x.toFixed(2) + '%;top:' + b.y.toFixed(2) + '%;width:' + b.w.toFixed(2) +
                            '%;height:' + b.h.toFixed(2) + '%">' +
                            '<i class="box-tag' + inside + '">#' + r.no + ' ' + escapeHtml(r.title) + '</i></span>';
                    });
                    html += '</div>';
                }
                if (!boxes.length) {
                    html += '<div class="detail-note">' + (key === 'llm' ?
                        '大模型通道只给候选、不给检测框；切到「37ac」看模型框，或切到「能工智人」看人工框。' :
                        '这个通道没有检测框（整图提交或没跑检测）。') + '</div>';
                }
                html += '</div>';
                html += '<div class="detail-list">' + rows.map((r) => this.detailRowHtml(r)).join('') + '</div>';
                html += '</div>';
            }
            html += '</div>';

            dialog.innerHTML = html;
            this.bindDetailEvents();
        }

        bindDetailEvents() {
            const dialog = this.detailDialog;
            if (!dialog) return;
            const stage = dialog.querySelector('#detailStage');
            const img = dialog.querySelector('#detailImage');
            if (img) {
                img.addEventListener('load', () => {
                    // 图有尺寸了：撤掉占位高度，百分比框才对得上图
                    if (stage) stage.classList.remove('is-empty');
                    img.classList.remove('flow-empty');
                });
                img.addEventListener('error', () => {
                    img.removeAttribute('src');
                    if (stage) stage.classList.add('is-empty');
                    Notify.error('原图读取失败，可能已过期或被清理');
                });
            }
            dialog.querySelectorAll('[data-detail-channel]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    this.detailState.key = btn.getAttribute('data-detail-channel');
                    this.detailState.focus = null;
                    this.renderDetail();
                });
            });
            const closer = dialog.querySelector('[data-detail-close]');
            if (closer) closer.addEventListener('click', () => dialog.close());
            dialog.querySelectorAll('[data-box]').forEach((el) => {
                const i = el.getAttribute('data-box');
                el.addEventListener('mouseenter', () => this.highlightDetail(i, true));
                el.addEventListener('mouseleave', () => this.highlightDetail(i, false));
                el.addEventListener('click', () => this.highlightDetail(i, true, true));
            });
            dialog.querySelectorAll('[data-row]').forEach((el) => {
                const i = el.getAttribute('data-row');
                el.addEventListener('mouseenter', () => this.highlightDetail(i, true));
                el.addEventListener('mouseleave', () => this.highlightDetail(i, false));
                el.addEventListener('click', () => this.highlightDetail(i, true));
            });
            // 从卡片里点具体角色进来的：直接把那一项点亮并滚到视野内
            if (this.detailState && this.detailState.focus !== null && this.detailState.focus !== undefined) {
                this.highlightDetail(String(this.detailState.focus), true, true);
            }
        }

        /* 高亮第 i 项：框和列表行一起亮 */
        highlightDetail(i, on, scrollRow) {
            const dialog = this.detailDialog;
            if (!dialog) return;
            ['[data-box="' + i + '"]', '[data-row="' + i + '"]'].forEach((sel) => {
                const el = dialog.querySelector(sel);
                if (el) el.classList.toggle('is-active', !!on);
            });
            if (on && scrollRow) {
                const row = dialog.querySelector('[data-row="' + i + '"]');
                if (row && typeof row.scrollIntoView === 'function') {
                    try {
                        row.scrollIntoView({
                            block: 'nearest',
                            behavior: 'smooth'
                        });
                    } catch (e) {
                        row.scrollIntoView();
                    }
                }
            }
        }

        /* ==================== 历史识别（保存在本机） ==================== */
        loadHistory() {
            try {
                const raw = localStorage.getItem(HISTORY_KEY);
                const list = raw ? JSON.parse(raw) : [];
                return Array.isArray(list) ? list : [];
            } catch (e) {
                return [];
            }
        }

        saveHistory(list) {
            try {
                localStorage.setItem(HISTORY_KEY, JSON.stringify((list || []).slice(0, HISTORY_MAX)));
            } catch (e) {
                console.warn('历史记录写入失败:', e);
            }
        }

        addHistoryEntry(taskId, extra) {
            if (!taskId) return;
            const entry = Object.assign({
                task_id: taskId,
                at: Date.now()
            }, extra || {});
            const list = this.loadHistory().filter((item) => item.task_id !== taskId);
            list.unshift(entry);
            this.saveHistory(list);
            if (this.currentTab === 'history') this.renderHistory();
            this.loadHumanTaskList();
        }

        updateHistoryEntry(taskId, extra) {
            const list = this.loadHistory();
            const idx = list.findIndex((item) => item.task_id === taskId);
            if (idx < 0) return this.addHistoryEntry(taskId, extra);
            list[idx] = Object.assign({}, list[idx], extra || {});
            this.saveHistory(list);
        }

        clearHistory() {
            this.saveHistory([]);
            this.renderHistory();
            this.loadHumanTaskList();
            Notify.success('已清空本机历史记录');
        }

        renderHistory() {
            const wrap = this.historyList;
            if (!wrap) return;
            const list = this.loadHistory();
            if (!list.length) {
                wrap.innerHTML = '<div class="empty"><div class="empty-icon"><i class="ph ph-clock-counter-clockwise"></i></div><p>这台设备还没有识别记录</p></div>';
                return;
            }
            wrap.innerHTML = list.map((item) => {
                const time = new Date(item.at || Date.now()).toLocaleString();
                const chips = CHANNEL_META.map((meta) => {
                    const state = (item.channel_status || {})[meta.key] || 'unknown';
                    return '<span class="channel-chip ' + this.stateClass(state) + '">' + meta.short + ' ' + this.stateLabel(state) + '</span>';
                }).join('');
                return '<div class="history-item" data-task="' + escapeHtml(item.task_id) + '">' +
                    '<img class="history-thumb" alt="" loading="lazy" src="/api/tasks/' + encodeURIComponent(item.task_id) + '/image?max_side=160" onerror="this.style.visibility=&quot;hidden&quot;">' +
                    '<div class="history-body">' +
                    '<div class="history-line"><span class="mono history-id">' + escapeHtml(String(item.task_id).slice(0, 8)) + '…</span>' +
                    '<span class="history-time">' + escapeHtml(time) + '</span></div>' +
                    '<div class="history-chips">' + chips + '</div>' +
                    '</div>' +
                    '<div class="history-actions">' +
                    '<button type="button" class="btn btn-secondary btn-sm" data-role="view">查看结果</button>' +
                    '<button type="button" class="btn btn-ghost btn-sm" data-role="vote">去投票</button>' +
                    '</div>' +
                    '</div>';
            }).join('');
        }

        async openHistoryTask(taskId) {
            if (!taskId) return;
            const wrap = this.historyResultWrap;
            if (wrap) {
                wrap.innerHTML = this.skeletonChannelsHtml(3);
                wrap.classList.add('active');
                wrap.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
            this.setBusy(true);
            try {
                const resp = await fetch('/api/tasks/' + encodeURIComponent(taskId), {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.message || ('读取失败 (' + resp.status + ')'));
                const result = data.result || {};
                const status = data.channel_status || {};
                this.updateHistoryEntry(taskId, {
                    channel_status: status
                });
                this.renderHistory();
                if (wrap) {
                    this.renderChannelsInto(wrap, result, status, taskId);
                }
            } catch (e) {
                if (wrap) {
                    wrap.innerHTML = '';
                    wrap.classList.remove('active');
                }
                Notify.error('读取任务结果失败：' + (e.message || e));
            } finally {
                this.setBusy(false);
            }
        }

        /* 结果自动刷新：多通道/人工票是陆续到的，渲染后继续轮询把卡片更新掉
         * - 节点通道（37ac/llm）还在跑：5 秒一问
         * - 节点通道都完成、但人工通道还没票：放慢到 10 秒一问，继续等人工票
         * - 人工有票 / 没有人工通道 / 超过上限 / 换任务 / 有新识别：停
         */
        startChannelRefresh(taskId) {
            if (!taskId) return;
            this.stopChannelRefresh();
            const self = this;
            const epoch = this.updateEpoch;
            let attempts = 0;
            const MAX_ATTEMPTS = 90;

            const tick = async () => {
                attempts += 1;
                if (attempts > MAX_ATTEMPTS || epoch !== self.updateEpoch || self.currentTaskId !== taskId) {
                    self.stopChannelRefresh();
                    return;
                }
                let delay = 5000;
                try {
                    const resp = await fetch('/api/tasks/' + encodeURIComponent(taskId), {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                    });
                    // 关键：请求往返期间可能已经有新的识别请求，回来后再校验一次
                    if (epoch !== self.updateEpoch) {
                        self.stopChannelRefresh();
                        return;
                    }
                    if (resp.ok) {
                        const data = await resp.json();
                        if (epoch !== self.updateEpoch) {
                            self.stopChannelRefresh();
                            return;
                        }
                        const status = data.channel_status || {};
                        const result = data.result || {};
                        self.updateHistoryEntry(taskId, {
                            channel_status: status
                        });
                        if (self.currentTab === 'history') self.renderHistory();
                        self.resultWrap.innerHTML = self.generateChannelsHTML(result, status, {
                            taskId: taskId
                        });
                        self.resultWrap.classList.add('active');

                        const pendingNode = Object.keys(status).filter((c) => c !== 'human' && status[c] !== 'completed');
                        const wantsHuman = Object.prototype.hasOwnProperty.call(status, 'human');
                        const humanVotes = ((result.human || {}).votes || []).length;
                        if (!pendingNode.length && (!wantsHuman || humanVotes > 0)) {
                            self.stopChannelRefresh();
                            return;
                        }
                        // 节点通道都好了就放慢节奏，单纯等人工票
                        delay = pendingNode.length ? 5000 : 10000;
                    }
                } catch (e) {
                    // 网络抖动忽略，等下一轮
                }
                if (epoch !== self.updateEpoch) {
                    self.stopChannelRefresh();
                    return;
                }
                self.channelTimer = setTimeout(tick, delay);
            };
            tick();
        }

        /* 进历史页时把本机记录里还没跑完的通道状态补一次（列表卡片不再是旧状态） */
        async refreshHistoryStatuses() {
            const list = this.loadHistory();
            const pending = list.filter((item) => {
                const st = item.channel_status || {};
                const keys = Object.keys(st);
                if (!keys.length) return true;
                return keys.some((k) => st[k] !== 'completed' && st[k] !== 'failed');
            }).slice(0, 6);
            if (!pending.length) return;

            this.setBusy(true);
            let changed = false;
            try {
                await Promise.all(pending.map(async (item) => {
                    try {
                        const resp = await fetch('/api/tasks/' + encodeURIComponent(item.task_id), {
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                        });
                        if (!resp.ok) return;
                        const data = await resp.json();
                        const st = data.channel_status || {};
                        if (Object.keys(st).length) {
                            this.updateHistoryEntry(item.task_id, {
                                channel_status: st
                            });
                            changed = true;
                        }
                    } catch (e) {
                        // 单条失败不影响其他
                    }
                }));
            } finally {
                this.setBusy(false);
            }
            if (changed) this.renderHistory();
        }

        /* ==================== 公共 feed：大家最近在识别 ==================== */
        async loadPublicFeed() {
            const wrap = this.publicFeed;
            if (!wrap) return;
            wrap.innerHTML = this.skeletonListHtml(4);
            this.setBusy(true);
            try {
                const resp = await fetch('/api/tasks/recent?limit=20', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                });
                const data = await resp.json();
                if (!resp.ok || data.success === false) {
                    throw new Error(data.message || ('加载失败 (' + resp.status + ')'));
                }
                const tasks = (data.data && data.data.tasks) || [];
                this.publicTasks = tasks;
                if (!tasks.length) {
                    wrap.innerHTML = '<div class="empty"><div class="empty-icon"><i class="ph ph-users-three"></i></div><p>服务端还没有识别任务</p></div>';
                    return;
                }
                wrap.innerHTML = tasks.map((t) => this.feedItemHtml(t)).join('');
            } catch (e) {
                this.publicTasks = [];
                wrap.innerHTML = '<div class="empty"><div class="empty-icon"><i class="ph ph-cloud-slash"></i></div><p>暂时拿不到列表，点「刷新」重试</p></div>';
                Notify.error('加载最近任务失败：' + (e.message || e));
            } finally {
                this.setBusy(false);
            }
        }

        feedItemHtml(task) {
            const chips = CHANNEL_META.map((meta) => {
                const state = (task.channel_status || {})[meta.key] || 'unknown';
                return '<span class="channel-chip ' + this.stateClass(state) + '">' + meta.short + ' ' + this.stateLabel(state) + '</span>';
            }).join('');
            const votes = task.human_votes ? '<span class="channel-chip ok">人工 ' + task.human_votes + ' 票</span>' : '';
            const thumb = task.image_available ?
                '<img class="history-thumb" alt="" loading="lazy" src="/api/tasks/' + encodeURIComponent(task.task_id) +
                '/image?max_side=160" onerror="this.style.visibility=&quot;hidden&quot;">' :
                '<div class="history-thumb"></div>';
            return '<div class="history-item" data-task="' + escapeHtml(task.task_id) + '">' + thumb +
                '<div class="history-body">' +
                '<div class="history-line">' +
                '<span class="mono history-id">' + escapeHtml(String(task.task_id).slice(0, 8)) + '…</span>' +
                '<span class="history-time">' + escapeHtml(task.created_at || '') + '</span>' +
                '</div>' +
                '<div class="history-chips">' + chips + votes + '</div>' +
                '</div>' +
                '<div class="history-actions">' +
                '<button type="button" class="btn btn-secondary btn-sm" data-role="view">查看结果</button>' +
                '<button type="button" class="btn btn-ghost btn-sm" data-role="vote">去投票</button>' +
                '</div>' +
                '</div>';
        }

        /* ==================== 能工智人（人工通道） ==================== */
        /* 待标注任务列表：最新的「还没有人工票」的任务，卡片样式同历史识别 */
        async loadHumanTaskList() {
            const wrap = this.humanTaskList;
            if (!wrap) return;
            // 骨架卡张数 + 最小高度都对齐上一次的真实列表：骨架态的布局高度≈真实高度，
            // 点「标注这张」时就能立刻算出准确的 Y 开始滑，不用等接口回来
            wrap.innerHTML = this.skeletonListHtml(this.lastTaskPoolSize || 3);
            const reserve = this.pinnedListHeight || this.lastListHeight || 0;
            if (reserve) wrap.style.minHeight = reserve + 'px';
            this.listLoading = true;
            this.setBusy(true);
            try {
                const resp = await fetch('/api/tasks/recent?limit=12', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                });
                const data = await resp.json();
                if (!resp.ok || data.success === false) {
                    throw new Error(data.message || ('加载失败 (' + resp.status + ')'));
                }
                const tasks = ((data.data && data.data.tasks) || []).filter((t) => t.image_available);
                this.humanTaskPool = tasks;
                this.lastTaskPoolSize = tasks.length || 1;
                if (!tasks.length) {
                    wrap.style.minHeight = '';
                    this.lastListHeight = 0;
                    wrap.innerHTML = '<div class="empty"><div class="empty-icon"><i class="ph ph-users-three"></i></div><p>暂时没有待标注的任务，等有人上传后再来</p></div>';
                    return;
                }
                wrap.innerHTML = tasks.map((t) => this.humanTaskCardHtml(t)).join('');
                wrap.style.minHeight = '';
                // 记下真实高度，下次骨架态直接占住同样的高度
                const measured = wrap.offsetHeight || wrap.getBoundingClientRect().height || 0;
                if (measured) {
                    this.lastListHeight = Math.round(measured);
                    // 正在标注时把列表高度钉住：投完票那张图会从待标注池里消失，
                    // 上面的列表一矮，下面的标注卡片就会整体上跳（看着像滚动回弹）
                    if (this.humanLoadedTask) {
                        this.pinnedListHeight = Math.max(this.pinnedListHeight || 0, this.lastListHeight);
                        wrap.style.minHeight = this.pinnedListHeight + 'px';
                    }
                }
            } catch (e) {
                this.humanTaskPool = [];
                wrap.style.minHeight = '';
                wrap.innerHTML = '<div class="empty"><div class="empty-icon"><i class="ph ph-cloud-slash"></i></div><p>暂时拿不到待标注任务，点「刷新任务」重试</p></div>';
                Notify.error('加载待标注任务失败：' + (e.message || e));
            } finally {
                this.listLoading = false;
                this.setBusy(false);
            }
        }

        humanTaskCardHtml(task) {
            const chips = CHANNEL_META.map((meta) => {
                const state = (task.channel_status || {})[meta.key] || 'unknown';
                return '<span class="channel-chip ' + this.stateClass(state) + '">' + meta.short + ' ' + this.stateLabel(state) + '</span>';
            }).join('');
            const active = task.task_id === this.humanLoadedTask ? ' active' : '';
            return '<div class="history-item' + active + '" data-task="' + escapeHtml(task.task_id) + '">' +
                '<img class="history-thumb" alt="" loading="lazy" src="/api/tasks/' + encodeURIComponent(task.task_id) +
                '/image?max_side=160" onerror="this.style.visibility=&quot;hidden&quot;">' +
                '<div class="history-body">' +
                '<div class="history-line">' +
                '<span class="mono history-id">' + escapeHtml(String(task.task_id).slice(0, 8)) + '…</span>' +
                '<span class="history-time">' + escapeHtml(task.created_at || '') + '</span>' +
                '</div>' +
                '<div class="history-chips">' + chips +
                '<span class="channel-chip' + (task.human_votes ? ' ok' : '') + '">' +
                (task.human_votes ? ('人工 ' + task.human_votes + ' 票') : '还没人工票') + '</span></div>' +
                '</div>' +
                '<div class="history-actions">' +
                '<button type="button" class="btn btn-primary btn-sm" data-role="annotate">标注这张</button>' +
                '</div>' +
                '</div>';
        }

        /* 跳到「能工智人」并选中某个任务，然后平滑滚到标注卡片 */
        selectHumanTask(taskId) {
            // 已经在「能工智人」里点「标注这张」时不要再重建列表：列表是真实的，
            // 位置直接算得准，也避免正在看的列表闪一下骨架
            if (this.currentTab !== 'human') this.switchTab('human');
            this.loadHumanTask(taskId);
            this.scheduleAnnotateScroll();
        }

        /* 算好 Y 立刻滑一次，随后在几个高度会变的节点上各校正一次 */
        scheduleAnnotateScroll() {
            this.autoScrollPending = true;
            // 列表高度已知且没在请求中（骨架已按上次真实高度占位）就立刻开滑，手感最快；
            // 否则（第一次来 / 正在重新拉列表，骨架 3 张 vs 真实可能十几张）等渲染完再滑到
            // 准确位置，免得滑到一半又改目标，长距离下就是顿挫。
            if (this.lastListHeight && !this.listLoading) this.scrollToAnnotateCard(0);
            setTimeout(() => this.scrollToAnnotateCard(0), 600);
            setTimeout(() => this.scrollToAnnotateCard(0), 1500);
            // 3s 后收工，之后不再抢滚动条
            setTimeout(() => {
                this.autoScrollPending = false;
            }, 3000);
        }

        /* 页面当前最大可滚动距离（用来判断目标是不是被页面长度卡住了） */
        maxScrollTop() {
            try {
                const doc = document.documentElement || {};
                return Math.max(0, (doc.scrollHeight || 0) - (window.innerHeight || 0));
            } catch (e) {
                return 0;
            }
        }

        /* ?scrolldebug=1 时把滚动决策打到 console，排查"多滑一段/回弹" */
        scrollLog(kind, data) {
            if (!this.scrollDebug) return;
            const line = '[scroll] ' + kind + ' ' + JSON.stringify(data || {});
            this.scrollLogLines = (this.scrollLogLines || []).concat(line).slice(-200);
            try {
                console.log(line);
            } catch (e) {
                // 忽略
            }
        }

        /* 标注卡片当前应该滚到的 Y（扣掉 sticky 导航高度） */
        annotateScrollTop() {
            const target = this.humanAnnotateCard;
            if (!target || target.hidden) return null;
            let navH = 64;
            try {
                const raw = getComputedStyle(document.documentElement).getPropertyValue('--ac-nav-h');
                const parsed = parseInt(raw, 10);
                if (!isNaN(parsed)) navH = parsed;
            } catch (e) {
                // 拿不到就用默认 64
            }
            const scrollY = window.pageYOffset || window.scrollY || 0;
            const y = target.getBoundingClientRect().top + scrollY - navH - 14;
            return Math.max(0, Math.round(y));
        }

        /**
         * 平滑滚动到标注卡片：先把 Y 算出来再滑。
         * 任务列表是异步渲染的（骨架 → 真实卡片），高度会变，所以
         * 列表渲染完（布局稳定）、图片加载完各再算一次，避免停在旧位置。
         */
        scrollToAnnotateCard(delay, force) {
            const ms = delay === undefined ? 60 : delay;
            const run = () => {
                // 用户自己滚过（wheel/touch）就放弃：连已经排队的这次也不执行
                if (!force && !this.autoScrollPending) {
                    this.scrollLog('skip', {
                        why: '用户已经自己滚了'
                    });
                    return;
                }
                const top = this.annotateScrollTop();
                if (top === null) {
                    this.scrollLog('skip', {
                        why: '标注卡片还没展开'
                    });
                    return;
                }
                const cur = window.pageYOffset || window.scrollY || 0;
                const maxScroll = this.maxScrollTop();
                const anim = this.scrollAnim;
                // 还在朝上一次的目标滑：目标只差一点点就别打断。
                // 中途改目标会让浏览器从当前位置重新起一段动画，长距离下就是"冲过去再退回来"的顿挫。
                if (anim && (Date.now() - anim.at) < 1600 && Math.abs(cur - anim.target) > 8) {
                    // 例外：上次是"页面还不够长、被浏览器卡住"，现在页面够长了，这种要立刻补上
                    const unblocked = anim.clamped && top <= maxScroll + 2;
                    if (!unblocked && Math.abs(top - anim.target) < 140) {
                        this.scrollLog('skip', {
                            why: '滑动中，目标只差 ' + Math.round(Math.abs(top - anim.target)) + 'px',
                            cur: cur,
                            top: top,
                            target: anim.target
                        });
                        return;
                    }
                }
                // 已经到位就不重复触发（多次校正时不抖）
                if (Math.abs(cur - top) < 6) {
                    this.scrollAnim = null;
                    this.scrollLog('settled', {
                        top: top
                    });
                    return;
                }
                this.scrollAnim = {
                    target: top,
                    at: Date.now(),
                    clamped: top > maxScroll + 2
                };
                this.scrollLog('go', {
                    top: top,
                    cur: cur,
                    maxScroll: maxScroll,
                    clamped: this.scrollAnim.clamped
                });
                try {
                    window.scrollTo({
                        top: top,
                        behavior: 'smooth'
                    });
                } catch (e) {
                    window.scrollTo(0, top);
                }
            };
            if (typeof requestAnimationFrame === 'function') {
                requestAnimationFrame(() => setTimeout(run, ms));
            } else {
                setTimeout(run, ms);
            }
        }

        /* 标注卡片收起后，列表不需要再钉着高度 */
        releaseListPin() {
            this.pinnedListHeight = 0;
            if (this.humanTaskList) this.humanTaskList.style.minHeight = '';
        }

        renderHumanPanel() {
            const taskId = this.humanLoadedTask;
            if (!taskId && this.humanAnnotateCard) {
                this.humanAnnotateCard.hidden = true;
                this.releaseListPin();
            }
            this.loadHumanTaskList().then(() => {
                if (taskId) this.loadHumanTask(taskId); // 刷新列表时保持当前任务高亮
                this.scrollToAnnotateCard(0); // 真实卡片渲染完，按新高度校正
            });
        }

        /* 载入待标注任务：图片 + 框选器 + 模型猜测 + 现有票（去重后未提交） */
        async loadHumanTask(taskId) {
            if (!taskId) return;
            this.humanLoadedTask = taskId;
            const image = this.humanCropImage;
            const title = this.humanTaskTitle;
            const meta = this.humanTaskMeta;

            if (title) title.textContent = '任务 ' + String(taskId).slice(0, 8) + '…';
            if (meta) meta.textContent = '';
            this.destroyHumanCropper();
            if (this.humanAnnotateCard) this.humanAnnotateCard.hidden = false;
            this.setBusy(true);
            if (this.humanCropPlaceholder) {
                this.humanCropPlaceholder.style.display = 'none';
            }
            if (this.humanCropPreview) this.humanCropPreview.innerHTML = '';
            this.pendingVotes = [];
            this.renderPending();
            if (this.humanCropCanvas) {
                this.humanCropCanvas.classList.add('is-empty', 'flow-empty');
            }
            if (this.humanCropPreview) {
                this.humanCropPreview.classList.add('flow-empty');
            }
            if (image) {
                // 注意：把 src 置空/移除会触发一次假的 error 事件，
                // 所以这里用 guard 标记"真正在加载中"，error 只认这一次加载。
                this.humanImageLoading = false;
                image.style.display = 'none';
                image.removeAttribute('src');
            }

            try {
                const resp = await fetch('/api/tasks/' + encodeURIComponent(taskId), {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.message || ('读取失败 (' + resp.status + ')'));
                this.humanTaskData = data;

                if (image) {
                    // 加时间戳避免浏览器复用上次的图
                    this.humanImageLoading = true;
                    image.src = '/api/tasks/' + encodeURIComponent(taskId) + '/image?max_side=1024&t=' + Date.now();
                }
                this.fillHumanSuggestions(data.result || {});
                this.renderHumanVotes(taskId, data.result || {});
                if (meta) {
                    const status = data.channel_status || {};
                    const parts = CHANNEL_META.map((m) => m.short + ' ' + this.stateLabel(status[m.key] || 'unknown'));
                    meta.textContent = '识别状态：' + parts.join(' · ');
                }
                this.markHumanTaskActive(taskId);
            } catch (e) {
                this.humanTaskData = null;
                this.humanLoadedTask = null;
                if (this.humanAnnotateCard) this.humanAnnotateCard.hidden = true;
                this.releaseListPin();
                if (meta) meta.textContent = '';
                if (this.humanVotes) this.humanVotes.innerHTML = '';
                Notify.error('任务读取失败：' + (e.message || e));
            } finally {
                this.setBusy(false);
            }
        }

        markHumanTaskActive(taskId) {
            if (!this.humanTaskList) return;
            this.humanTaskList.querySelectorAll('.history-item').forEach((el) => {
                el.classList.toggle('active', el.getAttribute('data-task') === taskId);
            });
        }

        /* 模型猜测：拆成 IP / 角色名，分别灌进两个 datalist + 可点选标签 */
        fillHumanSuggestions(result) {
            const ips = [];
            const names = [];
            const pairs = [];
            const push = (list) => {
                (list || []).forEach((p) => {
                    const label = this.splitLabel(p);
                    if (!label.name) return;
                    if (label.ip && ips.indexOf(label.ip) < 0) ips.push(label.ip);
                    if (names.indexOf(label.name) < 0) names.push(label.name);
                    pairs.push(label);
                });
            };
            push(result['37ac'] && result['37ac'].class_probs);
            push(result['llm'] && result['llm'].class_probs);
            ((result['37ac'] && result['37ac'].characters) || result.characters || []).forEach((c) => push(c.class_probs));

            if (this.humanIpOptions) {
                this.humanIpOptions.innerHTML = ips.map((v) => '<option value="' + escapeHtml(v) + '"></option>').join('');
            }
            if (this.humanNameOptions) {
                this.humanNameOptions.innerHTML = names.map((v) => '<option value="' + escapeHtml(v) + '"></option>').join('');
            }
            if (this.humanNameSuggest) {
                this.humanNameSuggest.innerHTML = pairs.slice(0, 6).map((p, i) =>
                    '<button type="button" data-ip="' + escapeHtml(p.ip) + '" data-name="' + escapeHtml(p.name) + '" data-i="' + i + '">' +
                    escapeHtml((p.ip ? p.ip + ' | ' : '') + p.name) + '</button>').join('');
            }
        }

        renderHumanVotes(taskId, result) {
            if (!this.humanVotes) return;
            const votes = ((result.human || {}).votes) || [];
            if (!votes.length) {
                this.humanVotes.innerHTML = '<h4>这张图还没有标注</h4><div class="channel-empty">你可以当第一个；别人标过之后这里会按人分组显示</div>';
                return;
            }
            const groups = {};
            votes.forEach((v) => {
                const key = v.voter || v.source || '匿名';
                (groups[key] = groups[key] || []).push(v);
            });
            const voters = Object.keys(groups);
            let html = '<h4>这张图上的标注（' + votes.length + ' 个角色 / ' + voters.length + ' 人）</h4>';
            voters.forEach((key) => {
                html += '<div class="vote-group">' +
                    '<div class="vote-group-head">' + escapeHtml(key) + ' · ' + groups[key].length + ' 个角色</div>' +
                    this.votesHtml(groups[key]) +
                    '</div>';
            });
            this.humanVotes.innerHTML = html;
        }

        /* 框选器：让人自己拉框，不用 YOLO 的人物序号 */
        initHumanCropper() {
            const image = this.humanCropImage;
            if (!image || typeof Cropper === 'undefined' || this.humanCropInstance) return;
            this.humanCropInstance = new Cropper(image, {
                preview: '#humanCropPreview',
                viewMode: 1,
                guides: true,
                center: true,
                highlight: false,
                background: false,
                autoCrop: false, // 不给默认框：想标谁就自己拉
                autoCropArea: 0.6,
                movable: false,
                zoomable: true,
                rotatable: false,
                scalable: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
                cropstart: () => {
                    if (this.humanCropPreview) this.humanCropPreview.classList.remove('flow-empty');
                },
            });
        }

        destroyHumanCropper() {
            if (this.humanCropInstance) {
                this.humanCropInstance.destroy();
                this.humanCropInstance = null;
            }
        }

        /* 读取当前选框并换算成归一化坐标（分母是原图尺寸） */
        readHumanBbox() {
            const image = this.humanCropImage;
            if (!this.humanCropInstance || !image || !image.naturalWidth) return null;
            const data = this.humanCropInstance.getData(); // 原图像素坐标
            const w = image.naturalWidth;
            const h = image.naturalHeight;
            if (!data || data.width < 8 || data.height < 8) return null; // 没框或框太小
            const bbox = {
                x: Number((data.x / w).toFixed(4)),
                y: Number((data.y / h).toFixed(4)),
                w: Number((data.width / w).toFixed(4)),
                h: Number((data.height / h).toFixed(4)),
            };
            const percent = {
                x: Number((bbox.x * 100).toFixed(2)),
                y: Number((bbox.y * 100).toFixed(2)),
                w: Number((bbox.w * 100).toFixed(2)),
                h: Number((bbox.h * 100).toFixed(2)),
            };
            return {
                bbox: bbox,
                percent: percent
            };
        }

        /* 把当前"选框 + 表单"收进待提交列表；silent=true 时不出提示（供提交前自动收集） */
        collectPendingVote(silent) {
            const taskId = this.humanLoadedTask;
            if (!taskId) {
                if (!silent) Notify.error('请先在上面选一张图');
                return false;
            }
            const ip = (this.humanIp && this.humanIp.value || '').trim();
            const character = (this.humanName && this.humanName.value || '').trim();
            if (!ip || !character) {
                if (!silent) Notify.error('作品和角色名都要填');
                return false;
            }
            // 不框也可以：没有选框就按整图提交（不传 bbox，服务端也不会补框）
            const box = this.readHumanBbox();
            const whole = !box;

            let thumb = '';
            if (box) {
                try {
                    const canvas = this.humanCropInstance.getCroppedCanvas({
                        width: 72,
                        height: 72,
                        fillColor: '#ffffff'
                    });
                    if (canvas) thumb = canvas.toDataURL('image/jpeg', 0.7);
                } catch (e) {
                    // 缩略图失败不影响提交
                }
            } else {
                // 整图提交：缩略图直接用这张任务图
                thumb = '/api/tasks/' + encodeURIComponent(taskId) + '/image?max_side=160';
            }

            this.pendingVotes = this.pendingVotes || [];
            this.pendingVotes.push({
                name: ip + '/' + character,
                ip: ip,
                name_zh: character,
                bbox: box ? box.bbox : null,
                bbox_percent: box ? box.percent : null,
                whole: whole,
                note: (this.humanNote && this.humanNote.value || '').trim(),
                thumb: thumb,
            });
            this.renderPending();

            // 清掉选框与角色名，方便接着标下一个
            if (this.humanCropInstance) this.humanCropInstance.clear();
            if (this.humanCropPreview) this.humanCropPreview.classList.add('flow-empty');
            if (this.humanName) this.humanName.value = '';
            if (this.humanNote) this.humanNote.value = '';
            if (!silent) Notify.success('已加入待提交（可以继续标下一个角色）');
            return true;
        }

        addPendingVote() {
            return this.collectPendingVote(false);
        }

        renderPending() {
            const wrap = this.humanPending;
            const list = this.pendingVotes || [];
            if (wrap) {
                if (!list.length) {
                    wrap.innerHTML = '';
                } else {
                    wrap.innerHTML = '<h4>待提交（' + list.length + ' 个角色）</h4>' + list.map((v, i) => {
                        const label = this.splitLabel({
                            name: v.name,
                            ip: v.ip,
                            name_zh: v.name_zh
                        });
                        const pct = v.bbox_percent || {};
                        return '<div class="pending-item" data-i="' + i + '">' +
                            (v.thumb ? '<img class="pending-thumb" src="' + v.thumb + '" alt="">' : '<span class="pending-thumb"></span>') +
                            '<div class="pending-body">' +
                            '<div class="pending-name">' + escapeHtml(label.name) +
                            (label.ip ? '<span class="badge badge-neutral cand-ip">' + escapeHtml(label.ip) + '</span>' : '') +
                            '</div>' +
                            '<div class="channel-meta">' +
                            (v.whole || !v.bbox_percent ?
                                '<span class="channel-chip">整图</span>' :
                                '框选 ' + (Number(pct.x) || 0).toFixed(0) + '%,' + (Number(pct.y) || 0).toFixed(0) +
                                '% · ' + (Number(pct.w) || 0).toFixed(0) + '%×' + (Number(pct.h) || 0).toFixed(0) + '%') +
                            (v.note ? ' · ' + escapeHtml(v.note) : '') + '</div>' +
                            '</div>' +
                            '<button type="button" class="btn btn-ghost btn-sm" data-role="remove-pending">移除</button>' +
                            '</div>';
                    }).join('');
                }
            }
            if (this.btnSubmitVotes) {
                this.btnSubmitVotes.textContent = list.length ? ('提交 ' + list.length + ' 个标注') : '提交标注';
            }
        }

        removePendingVote(index) {
            this.pendingVotes = (this.pendingVotes || []).filter((v, i) => i !== index);
            this.renderPending();
        }

        /* 提交：整批替换自己在这张图上的标注（支持多角色、多人各投各的） */
        async submitHumanVotes(event) {
            event.preventDefault();
            const taskId = this.humanLoadedTask;
            if (!taskId) {
                Notify.error('请先在上面选一张图');
                return;
            }
            // 表单里还留着内容（填了但没点"添加"）时，提交前自动收进待提交列表
            this.collectPendingVote(true);

            const list = this.pendingVotes || [];
            if (!list.length) {
                Notify.error('先框住角色、填好作品/角色名，再点「添加这个角色」或直接提交');
                return;
            }

            const payload = {
                task_id: taskId,
                votes: list.map((v) => {
                    const item = {
                        name: v.name,
                        ip: v.ip,
                        name_zh: v.name_zh,
                        note: v.note || undefined,
                    };
                    // 整图提交时不带 bbox，避免服务端收到空框
                    if (v.bbox && v.bbox_percent) {
                        item.bbox = v.bbox;
                        item.bbox_percent = v.bbox_percent;
                    }
                    return item;
                }),
            };

            const btn = this.btnSubmitVotes || this.humanForm.querySelector('button[type="submit"]');
            if (btn) btn.disabled = true;
            try {
                const resp = await fetch(window.API_BASE_URL + '/upload/human', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (!resp.ok || data.success === false) {
                    throw new Error(data.message || ('提交失败 (' + resp.status + ')'));
                }
                Notify.success('已提交 ' + list.length + ' 个角色标注，感谢投喂！');
                this.pendingVotes = [];
                this.renderPending();
                await this.loadHumanTask(taskId);
                this.loadHumanTaskList();
            } catch (e) {
                Notify.error('提交失败：' + (e.message || e));
            } finally {
                if (btn) btn.disabled = false;
            }
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