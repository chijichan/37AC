<?php
// 检查是否是 AJAX 请求
$isAjax = isset($_GET['ajax']) && $_GET['ajax'] == '1';

if (!$isAjax) {
    require_once ROOT_PATH . '/views/admin/layout.php';
    exit;
}
?>

<style>
    .dash-page-head {
        margin-bottom: 1.6rem;
    }

    .dash-page-head h2 {
        margin-bottom: .2rem;
    }

    .settings-card {
        max-width: 720px;
    }

    .settings-card .field {
        margin-bottom: 1.1rem;
    }

    .checkbox-row {
        display: flex;
        align-items: center;
        gap: .5rem;
        font-size: .95rem;
        font-weight: 600;
        color: var(--ac-ink-900);
        cursor: pointer;
        padding: .35rem 0;
        width: fit-content;
    }

    .checkbox-row input[type="checkbox"] {
        width: 18px;
        height: 18px;
        accent-color: var(--ac-pink-600);
        cursor: pointer;
    }
</style>

<header class="dash-page-head">
    <h2>系统设置</h2>
    <p>修改会立即保存到服务端 settings 表。</p>
</header>

<div class="card settings-card" style="padding:1.5rem 1.6rem;">
    <form id="form-admin-settings">
        <div class="field">
            <label>自动分流比例（37ac 占比 %）</label>
            <input type="number" name="auto_split_ratio" class="input" min="0" max="100" value="55" />
            <span class="hint">model=auto 时：该比例走 37ac，剩余走 LLM；无 LLM 节点时全走 37ac。</span>
        </div>
        <div class="field">
            <label>任务最大重试次数</label>
            <input type="number" name="task_max_retries" class="input" min="0" max="20" value="3" />
            <span class="hint">仅记录到设置表，供后续任务管理器读取。</span>
        </div>
        <div class="field">
            <label class="checkbox-row" for="rate-limit-enabled">
                <input type="checkbox" id="rate-limit-enabled" name="rate_limit_enabled" />
                <span>开启接口限流</span>
            </label>
        </div>
        <div class="field">
            <label class="checkbox-row" for="maintenance-mode">
                <input type="checkbox" id="maintenance-mode" name="maintenance_mode" />
                <span>维护模式（仅记录，暂不拦截请求）</span>
            </label>
        </div>
        <div class="field" style="margin-bottom:0;">
            <button type="submit" class="btn btn-primary"><i class="ph ph-floppy-disk"></i> 保存设置</button>
        </div>
    </form>
</div>

<script>
    async function loadSettings() {
        try {
            const result = await Auth.get(`${window.API_BASE_URL}/admin/settings`);
            const data = result.data || {};
            const form = document.getElementById('form-admin-settings');
            if (!form) return;
            form.auto_split_ratio.value = data.auto_split_ratio ?? '55';
            form.task_max_retries.value = data.task_max_retries ?? '3';
            document.getElementById('rate-limit-enabled').checked = String(data.rate_limit_enabled ?? '1') === '1';
            document.getElementById('maintenance-mode').checked = String(data.maintenance_mode ?? '0') === '1';
        } catch (e) {
            Notify.error('读取设置失败');
        }
    }

    document.getElementById('form-admin-settings').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            auto_split_ratio: form.auto_split_ratio.value.trim(),
            task_max_retries: form.task_max_retries.value.trim(),
            rate_limit_enabled: document.getElementById('rate-limit-enabled').checked ? '1' : '0',
            maintenance_mode: document.getElementById('maintenance-mode').checked ? '1' : '0',
        };
        try {
            const result = await Auth.put(`${window.API_BASE_URL}/admin/settings`, data);
            if (result.success) {
                Notify.success('设置已保存');
            } else {
                Notify.error(result.message || '保存失败');
            }
        } catch (e) {
            Notify.error('网络错误');
        }
    });

    window.dashboardPageInit = function() {
        window.__pageLoadPromise = loadSettings();
    };
</script>
