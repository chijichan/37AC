# 计划：人工票回流（人机不一致样本自动沉淀为训练数据）

> 现状：/www 的 \`POST /upload/human\` 已经是匿名可投票（IP 限流），结果只用于展示。
> 目标：把"**人工票 ≠ 模型预测**"的样本自动收集为待标注数据 → 下一轮训练加入 → 形成效果闭环。
> 这是当前投入产出比最高的涨点手段（无需新标注工具、无需外部数据）。

## 1. 触发与分流（服务端）

人工票落库时（human 段完成），拿它与 37ac / llm 的最佳结论比对：

| 情况 | 判定 | 处理 |
|------|------|------|
| 人工票 ≠ 模型 top-1 | \`disagree\` | **高价值**：进待标注队列 |
| 人工票 = top-1 但模型置信度 < 阈值（如 0.6） | \`low_conf\` | 中等价值：进队列（可选） |
| 人工票 = top-1 且高置信 | \`agree\` | 丢弃（无信息量） |
| 人工票指向不在 classes.json 的角色 | \`unknown_class\` | 高价值：既补数据又暴露**缺失类别** |

## 2. 存储布局

@@text
src/server/saves/pending/
  index.json                     ← 队列索引（task_id、图片、模型预测、人工票、状态、时间、投票指纹）
  <IP>/<角色>/<task_id>.jpg      ← 图片（优先从 saves/tmp|cache 复制；已过期则先走 /tasks/<id>/image 补拉）
  <IP>/<角色>/<task_id>.json     ← 该样本的元数据（与索引同结构）
@@

- 图片沿用它原有的所有清理策略（tmp/cache 回收）——**进 pending 即视为已回收保护**，不受 TTL 影响；
- 元数据里带 \`source\`（37ac/llm/人工）、\`model_pred\`、\`human_label\`、\`confidence\`、\`ip_hash\`、\`created_at\`。

## 3. 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | \`/admin/pending\` | 列表（按 IP/角色/状态筛选，分页） |
| POST | \`/admin/pending/<id>/accept\` | 接受 → 移到 \`saves/dataset_incoming/<IP>/<角色>/\` |
| POST | \`/admin/pending/<id>/reject\` | 拒绝（记录原因，避免重复进队列） |
| GET | \`/admin/pending/stats\` | 各 IP/角色的贡献量、accept 率（长尾优先排序用） |

## 4. 训练集成

@@powershell
# CLI：把已接受的样本并入数据集（保留原始文件名，不动已有数据）
python main.py dataset merge-pending            # 预览 + 确认
python main.py dataset merge-pending --apply    # 实际合并（会写入 saves/dataset/<IP>/<角色>/）
@@

- 合并后走既有 "指定角色裁剪"（only_roles）与质量门控，不会污染其它类；
- 合并记录写 \`saves/reports/merge-<时间戳>.json\`，并在训练报告里显示"本次新增样本 N 张"。

## 5. 防污染（必做）

1. **配额**：同一 IP 每天最多贡献 N 张（默认 20），同一任务只进一次；
2. **二次确认**：同一 (角色, 图片 pHash) 需要 **≥2 个独立投票**一致才进队列（防恶意单点投毒）；
3. **去重**：与现有数据集做 pHash 去重（阈值 0.95），避免把训练集原图又加一遍；
4. **上限保护**：单个类每天最多吸收 M 张（默认 50），防止某一类被灌爆；
5. **可回滚**：合并前把 classes 与数据集清单快照到 \`saves/reports/\`，支持按 merge 批次回滚。

## 6. 度量（闭环是否有效）

- \`pending → accept\` 比例（低于 30% 说明采集规则太宽）；
- 新增样本的**类分布**：长尾类（现有 <100 张）占比应 > 50%；
- 下一轮训练后**真实口径评估**（scripts/eval_pipeline.py）的 top-1 变化 —— 这是唯一验收标准。

## 7. 分步实施

| 步骤 | 内容 | 依赖 |
|------|------|------|
| ① | 服务端：比对 + 落盘 + \`index.json\` + 列表接口 | 现有 human 通道 ✔ |
| ② | CLI：\`dataset merge-pending\`（预览/合并/记录） | ① |
| ③ | 二次确认（≥2 票）+ pHash 去重 + 配额 | ①② |
| ④ | 后台页面展示队列与统计（/www） | ① |
