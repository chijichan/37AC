# 训练报告（HTML）设计

> 目标：训练过程中生成**可实时查看**的 HTML 报告，随进度更新；UI 复用 /www 的「樱花拿铁」设计令牌；产物落在 `src/cli/saves/reports/`。
> 约束：**零第三方依赖**（只用标准库）、**file:// 直接双击可看**（不需要起服务）、纯本地不联网。

## 1. 目录与产物

`text
src/cli/saves/reports/
  index.html                       ← 汇总页：最近 N 次 run 一览（可选，阶段③）
  <run-id>/                        ← run-id = <模型版本>-<YYYYmmdd_HHMMSS>，如 0.0.17-20261003_115632
    index.html                     ← 主报告（自包含：内联 CSS + 内联 SVG 折线图）
    progress.json                  ← 机读进度（唯一数据源，训练端原子写）
    events.log                     ← 事件流（阶段切换/保存/早停/中断，纯文本追加）
`

- 报告体积很小（单 run 几十 KB，图表是内联 SVG 而非图片）；
- `saves/reports/` 加入 .gitignore（训练产物不入库）。

## 2. 同步机制（怎么"跟着训练走"）

1. 训练端在**每轮结束**、**每 N 步**（默认 40 步）、**保存检查点**、**阶段切换**、**结束/中断**时：
   - 原子写 `progress.json`（临时文件 + `os.replace`，复用 checkpoint_service 的写法）；
   - 重新渲染 `index.html`（纯字符串模板，成本 ~1ms）。
2. 页面里放 `&lt;meta http-equiv="refresh" content="10"&gt;`：浏览器每 10 秒整页重载 → 看到最新一次渲染；`file://` 与 `http://` 均使用相同的整页刷新，不使用软刷新。
  **为什么不用 fetch + JS 轮询**：file:// 下 fetch 本地文件会被浏览器 CORS 拦掉，双击打开就失效；meta refresh 在 file:// 与 http:// 下都工作。
3. 进度粒度取舍：每次渲染都拿到"截至上一次写入"的数据，最坏滞后一轮（约 3.5 分钟）。若想要秒级，可选项③提供 `python -m http.server` 实时模式（文档末尾）。

## 3. 页面结构（单页、卡片式）

`text
┌─ 顶栏 ────────────────────────────────────────────────┐
│ 37AC 训练报告   0.0.17       [● 训练中]  已用时 01:23:45 │
└──────────────────────────────────────────────────────┘
┌─ 概览卡 ×6 ───────────────────────────────────────────┐
│ 基模 dbv4-resnet18 │ 类别 181 │ 训练/验证 15061/1673   │
│ batch 32 │ 分辨率 224 │ 设备 privateuseone:0           │
└──────────────────────────────────────────────────────┘
┌─ 进度 ────────────────────────────────────────────────┐
│ 阶段2 解冻精调   ████████░░░░░░  18/40 轮              │
│ 当前 best val 42.31%   │  预计剩余 01:12:00            │
└──────────────────────────────────────────────────────┘
┌─ 指标曲线（内联 SVG）─────────────────────────────────┐
│  loss ↓ 折线（每轮）      val/train acc ↑ 折线（每轮） │
└──────────────────────────────────────────────────────┘
┌─ 每轮明细表 ──────────────────────────────────────────┐
│ 轮次 | 阶段 | loss | train% | val% | lr | 耗时 | 时间   │
└──────────────────────────────────────────────────────┘
┌─ 检查点 ──────────────────────────────────────────────┐
│ kind | 名称 | 正确率 | 体积 | 时间                      │
└──────────────────────────────────────────────────────┘
┌─ 事件 ────────────────────────────────────────────────┐
│ 12:00:20 保存最佳模型 6.04% → 检查点 best               │
└──────────────────────────────────────────────────────┘
页脚：数据源 progress.json ｜ 生成于 2026-10-03 12:03:20 ｜ 每 10s 自动刷新
`

## 4. UI 复用「樱花拿铁」令牌（内联到报告里）

`css
:root{
  --ac-bg:#FDF9FB; --ac-surface:#FFFFFF; --ac-surface-2:#FBF3F7;
  --ac-ink-900:#322931; --ac-ink-700:#574B54; --ac-ink-500:#8A7C85; --ac-ink-300:#C9BDC5;
  --ac-pink-50:#FDF0F6; --ac-pink-100:#FBE0EE; --ac-pink-200:#F6C2DC; --ac-pink-300:#F09CC3;
  --ac-pink-400:#E86FA6; --ac-pink-500:#DE4F8D; --ac-pink-600:#C93470; --ac-pink-700:#A82A5C;
  --ac-mint:#3DBDB4;
  --ac-success:#2FA36B; --ac-success-bg:#E5F5ED;
  --ac-warning:#E08A1E; --ac-warning-bg:#FCF0DE;
  --ac-danger:#D64545;  --ac-danger-bg:#FBE7E7;
  --ac-info:#3E8FD9;    --ac-info-bg:#E5F1FB;
  --ac-radius-pill:999px; --ac-radius-input:12px; --ac-radius-card:16px; --ac-radius-modal:20px;
  --ac-shadow-card:0 2px 12px rgba(50,41,49,.05);
}
`

落地细节：

| 元素 | 规则 |
|---|---|
| 字体 | Nunito 无法从 saves/reports 访问 `/static/fonts` → 用系统栈：`-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei'`；数字/表格用 `JetBrains Mono` → 回退 `Consolas` |
| 卡片 | 白底 + `--ac-radius-card` + `--ac-shadow-card` |
| 状态徽章 | pill 形状：训练中=粉、完成=success、中断=warning、失败=danger |
| 进度条 | 粉色渐变 `--ac-pink-400 → --ac-pink-600`，轨道 `--ac-ink-100` |
| 折线图 | 内联 `<svg viewBox>`，val=粉、train=薄荷、loss=info 蓝；坐标由 Python 端算好（零 JS 依赖） |
| 强调色 | 全站**只用樱花粉**，语义色仅用于状态与图表 |

## 5. 代码结构

`text
src/cli/services/report_service.py      ← 全部逻辑（~250 行）
    start_run(meta) -> run_dir
    record_epoch(epoch, phase, loss, train_acc, val_acc, lr, secs)
    record_step(step, total, loss_hint=None)      # 每 N 步轻量写（只更新进度条）
    add_checkpoint(name, kind, accuracy, size_mb)
    add_event(text)
    set_status(status, note="")
    render()                                       # 渲染 index.html（模板内联在模块里）

src/cli/config/base.py
    REPORT_ENABLED = True          # 总开关
    REPORT_DIR = ROOT_PATH/"saves"/"reports"
    REPORT_REFRESH_SEC = 10        # 页面自动刷新间隔
    REPORT_EVERY_STEPS = 40        # 每多少步轻量更新一次

trainer.py 调用点
    训练开始      → start_run({version, base, dataset, classes, batch, image_size, device})
    每轮结束      → record_epoch(...) + render()
    每 N 步       → record_step(...) + render()（含 train_acc/loss 摘要）
    保存检查点    → add_checkpoint(...) + add_event(...) + render()
    阶段切换/早停 → add_event(...) + render()
    正常结束/中断 → set_status("finished"/"interrupted") + render()
`

## 6. progress.json 结构（契约）

`json
{
  "run_id": "0.0.17-20261003_115632",
  "status": "running",                      // running|finished|interrupted|failed
  "started_at": "2026-10-03 11:56:32",
  "updated_at": "2026-10-03 12:03:20",
  "elapsed_sec": 408,
  "meta": {"version":"0.0.17","base":"dbv4-resnet18","dataset":"saves/dataset",
           "classes":181,"train":15061,"val":1673,"batch":32,"image_size":224,
           "device":"privateuseone:0","epochs_total":50},
  "phase": {"name":"P2","label":"解冻精调","epoch":18,"total":40},
  "progress": {"step":167,"steps_total":471,"epochs_done":11,"epochs_total":50,
               "eta_sec":4320},
  "epochs": [{"epoch":1,"phase":"P1","loss":5.0567,"train_acc":2.68,"val_acc":6.04,
              "lr":0.001,"secs":225,"at":"2026-10-03 12:00:19"}, ...],
  "checkpoints": [{"name":"0.0.17-...-best","kind":"best","accuracy":6.04,
                   "size_mb":43.2,"at":"..."}],
  "events": [{"at":"...","text":"保存最佳模型 (正确率: 6.04%)"}, ...]
}
`

## 7. 实施顺序

| 步骤 | 内容 | 依赖 |
|---|---|---|
| ① | `report_service.py` + 内联模板 + 单测（用假数据渲染，断言关键片段） | 无 |
| ② | 接入 `trainer.py`（开始/每轮/每 N 步/检查点/结束与中断） | ① |
| ③ | 汇总页 `reports/index.html`（最近 N 个 run）+ `main.py model report` 打开最近报告 | ①② |
| ④（可选） | 实时模式：`python -m http.server -d saves/reports` + 报告里 `fetch` 轮询（仅 http:// 下生效） | ③ |

## 8. 风险与取舍

1. **file:// 限制**：不能用 fetch/外链资源 → 报告必须自包含（内联 CSS/SVG），自动刷新用 meta refresh ✔；
2. **写盘频率**：每 40 步渲染一次，单次 <5ms，且只写一个几 KB 的文件 → 对训练吞吐影响可忽略；若担心，可把 `REPORT_EVERY_STEPS=0` 关掉步级更新（只按轮更新）；
3. **多 run 并存**：目录按 run-id 隔离，互不覆盖；汇总页按 mtime 倒序取最近 N 个；
4. **中断/崩溃**：`progress.json` 原子写，最新一次渲染始终可读；进程被杀时最后一次状态为 running，页面会显示"上次更新于 X 分钟前"以便识别僵死；
5. **不引入图表库**：折线用内联 SVG（Python 端算坐标），避免 CDN（离线/内网不可用）与体积。
