# 模型管理 / 检查点系统 / 训练基模 设计

> 目标：把"训练模型"升级为**模型管理**；用**检查点系统**取代现在分散的保存方式；支持选择**训练基模**（首先落地 animetimm/resnet18.dbv4-full）。

## 1. 现状与问题

现在一次训练会往 saves/models/ 里散落写入：

`text
saves/models/
  37ac-v0.0.1.pth        ← 权重（文件名由 MODEL_FILENAME 决定）
  classes.json           ← 类别表（训练中/收尾/LLM 补全都可能改）
  config.json            ← 版本 + 权重/类别 SHA-256（节点同步靠它比对）
  _bak/37ac-v0.0.1_bak_YYYYmmdd_HHMMSS.pth
  _bak/classes_bak_*.json
`

问题：① 三者是"同一份模型状态"却被分别保存，任何一处漏写就出现"权重新、config 旧"（**已经真实发生过**：config.json 停在 9/27 而权重是 10/1）② 没有回滚概念，只能靠 _bak 手工捞 ③ 没有"基模"概念，预训练来源写死在代码里 ④ 备份无限增长。

## 2. 菜单改造

`text
主菜单
  [1] 模型管理           ← 原"训练模型"
      [1] 训练 / 继续训练
      [2] 检查点管理（列表 / 回滚 / 删除 / 清理）
      [3] 训练基模（查看 / 切换 / 校验）
      [4] 当前模型信息（版本、类别数、SHA、来源基模、最佳正确率）
      [0] 返回主菜单
  [2] 识别角色
  [3] 数据集管理
  [4] 节点服务
  [0] 退出程序
`

命令行兼容：`main.py train ...` 不变；新增 `main.py model list|rollback|base` 子命令（脚本化用）。

## 3. 检查点系统

### 3.1 布局（**不动现行文件布局**，节点同步零影响）

`text
saves/models/                     ← 保持现状：current 的权重/classes/config（节点从这里读）
  checkpoints/
    index.json                    ← 检查点索引（按时间倒序，含 kind/accuracy/备注/体积）
    0.0.12-20261003_041530-final/
      model.pth  classes.json  config.json  meta.json
    0.0.12-20261003_033012-best/            ← 训练中 val 提升时
    0.0.11-20261002_235900-interrupt/
    pre-restore-20261003_050000/            ← 回滚前自动保存当前状态
`

关键：检查点是**子目录里的完整快照**，current 仍然是 saves/models 根下的老位置 → 服务端/节点的模型同步逻辑（读 config.json 推导下载地址）**完全不用改** ✔

### 3.2 何时创建（三种 kind）

| kind | 触发 | 说明 |
|------|------|------|
| `best` | 训练中验证集提升（现"保存最佳模型"处） | 与 185 行那段逻辑合并，顺带写 config.json |
| `interrupt` | ESC/Ctrl+C 中断保存 | 现在那段也写 config.json，一并收进检查点 |
| `final` | 训练收尾（含 LLM 补全之后） | 保证 classes.json 哈希最新 |

### 3.3 接口（services/checkpoint_service.py）

`python
create_checkpoint(kind, version, accuracy=None, note="")  -> dict   # 快照 current → checkpoints/
list_checkpoints()                                        -> list[dict]
restore_checkpoint(name, backup_current=True)             -> dict   # 回滚（先存 pre-restore）
delete_checkpoint(name) / prune(keep=10, max_total_mb=2000) -> dict
current_info()                                            -> dict   # 版本/类别数/SHA/基模/最佳正确率
`

- 索引写 `index.json`（原子写：临时文件 + os.replace）
- `prune`：按时间保留最近 N 个 + 总体积上限；`baseline`/`pre-restore` 永不自动删
- 首进入模型管理时，若还没有任何检查点 → 为**当前状态**自动建一个 `baseline`（迁移，无痛）

## 4. 训练基模（base model）

### 4.1 布局与元数据

`text
saves/models/pretrained/
  imagenet-resnet18/    model.pth    meta.json   ← 现有行为（torchvision IMAGENET1K_V1）
  dbv4-resnet18/        model.pth    meta.json   ← animetimm/resnet18.dbv4-full
`

`meta.json` 字段（**必须**，否则域不匹配会掉点）：

`json
{ "id": "dbv4-resnet18", "arch": "resnet18", "source": "animetimm/resnet18.dbv4-full",
  "input_size": 224, "mean": [0.5,0.5,0.5], "std": [0.5,0.5,0.5],
  "state_dict_prefix": "", "license": "待确认", "downloaded_at": "..." }
`

### 4.2 代码改动

1. `config/base.py`：`PRETRAINED_BASE = os.getenv("PRETRAINED_BASE", "imagenet-resnet18")`；
   `MODEL_MEAN/MODEL_STD/IMAGE_SIZE` 由基模 meta 提供（缺省回落 ImageNet 常量）。
2. `models/character_model.py`：把"预训练初始化"从 `_build_model()` 解耦成
   `load_pretrained_backbone(model, base_id)`，顺序改为
   **建裸 resnet18(weights=None) → 载入基模 state_dict(strict=False) → 插 CBAM → 换 fc**。
3. `prediction/predictor.py`：`PREDICT_TRANSFORMS` 里写死的 ImageNet 均值改为读配置
   （**训练与推理必须同一套**，否则直接掉点）。
4. 模型管理菜单：列出 `pretrained/` 下的基模、显示 meta、切换 `PRETRAINED_BASE`（写回 .env）、校验文件与 SHA。

### 4.3 dbv4 落地步骤（需要你先在能联网的机器上做一次）

`powershell
pip install timm huggingface_hub
python -c "import timm; print(len(timm.create_model('resnet18', pretrained=False).state_dict()))"
huggingface-cli download animetimm/resnet18.dbv4-full --local-dir saves/models/pretrained/dbv4-resnet18
# 国内可加：set HF_ENDPOINT=https://hf-mirror.com
`

然后把 **①权重文件名 ②state_dict 前 10 个 key ③config 里的 mean/std/输入尺寸 ④license** 贴给我 → 我写 `meta.json` 与 key 映射（timm↔torchvision 差异），并跑一次"同一批图、两种基模"的 A/B 评估（用现有三档口径：数据集裁剪图 / 原图整图 / 原图+检测）。

## 5. 兼容与迁移

- **现行文件布局不变** → 服务端/节点同步、`_sync_local_model`、模型下载 URL 推导全部零改动；
- 现有 `_bak/` 保留只读，由 `prune` 选择性清理；新检查点写入 `checkpoints/`；
- `MODEL_FILENAME` 继续生效（权重文件名），检查点目录名另用 `<version>-<时间>-<kind>`。

## 6. 实施顺序（建议）

| 步骤 | 内容 | 风险 |
|------|------|------|
| ① | `checkpoint_service.py` + 单测（不动训练） | 低 |
| ② | 训练三处保存点改调 `create_checkpoint()`；主菜单改"模型管理"+ 检查点子菜单 | 中（训练路径） |
| ③ | 基模管理（pretrained/ + meta + 菜单切换 + 初始化解耦 + mean/std 配置化） | 中 |
| ④ | dbv4 接入 + A/B 评估（依赖你提供的下载产物） | 低（有回退：切回 imagenet 基模即可） |

## 7. 风险清单

1. **归一化不匹配**：dbv4 若用 0.5 均值而推理仍用 ImageNet 均值 → 精度崩；本设计用 `meta.json` 统一。
2. **key 不匹配**：timm 与 torchvision 的 stem/命名差异 → `strict=False` + 显式映射表 + 加载后打印未命中/多余 key 数量。
3. **许可**：dbv4 底座模型许可需确认（是否允许商用/再分发），文档与 `meta.json` 里记录。
4. **权重不入 git**：`saves/models/pretrained/**` 必须在 `.gitignore`（刚清过一次历史，别再犯）。
5. **回滚语义**：`restore` 会把 current 覆盖为历史快照，因此**先自动建 pre-restore 检查点**；恢复后 config.json 的哈希同步刷新（否则节点又会对不上）。
