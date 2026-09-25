# 图片流水线设计（多人物识别 / 缓存与临时文件 / 取图接口）

> 2026-09-13 冻结。决策来自用户确认的 6 个问题；实现分阶段，见文末。
> 相关代码：`src/server/services/storage_service.py`（新增）、`src/cli/detection/yolo_detector.py`、`src/cli/prediction/predictor.py`

## 0. 决策记录

| # | 议题 | 决定 |
|---|---|---|
| 1 | 检测/裁剪放在哪 | **节点侧（CLI）**做 YOLO 检测 + 逐人裁剪 + 识别；服务端只透传结果结构，保持**零 ML 依赖** |
| 1 | 结果结构 | 新增 **`characters[]`**（数组）；**旧顶层 `class_probs` 保留 = 置信度最高人物**的结果 |
| 2 | 第二种裁剪方式 | **mediapipe 关键点**（脸部/人体框），与 YOLO **可配置二选一 + 自动回退** |
| 2 | 依赖与资产 | 依赖只加在 **CLI 侧**；权重文件**不入 git**（.gitignore）；服务端保持纯 IO |
| 3/4 | 参数落点 | **`.env` 定默认值 + 后台 settings 表可覆盖**（tmp/cache 上限、压缩阈值、TTL…） |
| 3/4 | 取图接口 | `GET /tasks/<task_id>/image` **返回二进制** |
| 3 | 清理后取图 | 主路径 **410 + 任务元数据**；**同时**支持向处理该任务的节点**补拉**（节点需短期保留图片） |

### 关于 Upants 的分析结论（重要修正）

Upants 是「反网络美颜鉴伪 + 逆向还原」工具（MIT 徽章但仓库无 LICENSE 文件），**不是角色识别项目**：
它的 YOLO（`src/detector.py:847-884`，`classes=[0]`、`conf=0.25`、按面积降序）只在
**MediaPipe Pose 完全失败时**兜底；`max_num_faces=1`，**不做人物裁剪**（唯一裁剪是磨皮人脸 ROI，±2px 外扩、<20px 跳过），
bbox 是绝对像素 `(x,y,w,h)` 且**被 webui 丢弃**，无百分比坐标。

**真正"YOLO 检测→裁剪→识别"的实现在 37AC 自己仓库里**：
`src/cli/detection/yolo_detector.py:61-196`（`detect()` 返回 `{bbox:(x1,y1,x2,y2), confidence, class_id, class_name}`，按置信度降序）
与 `src/cli/prediction/predictor.py:274-297`（裁剪成功用裁剪图，失败回落整图）。→ **复用 37AC 的实现，只从 Upants 借工具函数**。

可借鉴（低耦合）：`src/pipeline.py:129-163` 的 `_imread_unicode`/`_save_image`（Windows 中文路径）、
`webui.py:45-71` 的 `_read_image_from_upload`（IMREAD_UNCHANGED 回退 + 灰度/BGRA 归一化 + finally 删除）。

**踩坑提醒**：`detect_and_crop` 在检测前会 `Image.LANCZOS` 缩放（`yolo_detector.py:147-154`），
**返回的 bbox 属于缩放后坐标系**；而需求要求"原图百分比坐标"，必须用**原图尺寸**换算（本次实现统一在 yolo_detector 里同时带出原图尺寸与缩放系数）。

### 依赖现状（实测 37AC .venv，Python 3.12.9）

| 包 | 状态 |
|---|---|
| torch 2.13.0+cpu、torchvision 0.28.0 | 已装 |
| ultralytics 8.4.93（AGPL-3.0） | 已装，`from ultralytics import YOLO` 可用 |
| opencv-python 5.0.0.93、numpy 2.5.1、Pillow 12.3.0 | 已装 |
| onnxruntime、mediapipe、scipy、skimage | **未装**（mediapipe 是需求2要新增的可选依赖） |
| 权重 | `src/cli/saves/models/yolov8n.pt`（6.25 MB，不入 git） |

⚠️ 许可：ultralytics + yolov8n.pt 是 AGPL-3.0，而 37AC 是 MIT；对外提供网络服务时需评估合规（本次按用户决定：依赖只在节点侧、权重不入库）。

## 1. 识别结果契约（存于 `task_results.result`）

```json
{
  "success": true,
  "recognition_type": "local",
  "crop_method": "yolo",
  "image": {"width": 1024, "height": 1536},
  "characters": [
    {
      "index": 0,
      "bbox":         {"x": 0.3125, "y": 0.1042, "w": 0.2100, "h": 0.6320},
      "bbox_percent": {"x": 31.25,  "y": 10.42,  "w": 21.00,  "h": 63.20},
      "detector_confidence": 0.91,
      "confidence": 96.06,
      "class_probs": [{"name": "原神/荧", "prob": 96.06}]
    }
  ],
  "class_probs": [{"name": "原神/荧", "prob": 96.06}]
}
```

- `bbox`：**归一化 0–1**（小数，4 位）；`bbox_percent`：**百分比 0–100**（2 位）。两种都给，避免"百分比（小数）"的歧义。
- 分母是**原图**宽高（不是缩放/裁剪后的坐标系）。
- `class_probs`（顶层）＝ `characters` 中置信度最高者的候选列表 → **老前端零改动**。
- 无人物时：`characters: []`、`crop_method: "full"`、顶层 `class_probs` 为整图识别结果（沿用现有回落）。
- 排序：按检测框面积降序；最多 `MAX_CHARACTERS`（默认 10）。

## 2. 服务端存储布局与参数

```text
src/server/saves/
├── tmp/      在途与短期：上传原图（任务完成/超时后按 TTL 清理）
└── cache/    留存副本：压缩后的 JPEG（供前端回看，默认 7 天）
```

文件命名：tmp → `<task_id><ext>`（原格式）；cache → `<task_id>.jpg`（压缩后）。

| `.env` 键（后台 settings 同名键可覆盖） | 默认 | 说明 |
|---|---|---|
| `IMAGE_TMP_DIR` / `IMAGE_CACHE_DIR` | `saves/tmp`、`saves/cache` | 目录 |
| `IMAGE_TMP_MAX_MB` / `IMAGE_CACHE_MAX_MB` | 2048 / 2048 | 各自容量上限 |
| `IMAGE_TMP_TTL_SEC` / `IMAGE_CACHE_TTL_SEC` | 3600 / 604800 | 保留时长 |
| `IMAGE_COMPRESS_MAX_SIDE` | 512 | 最长边大于它才压缩 |
| `IMAGE_COMPRESS_QUALITY` | 85 | JPEG 质量 |
| `IMAGE_CLEAN_INTERVAL_SEC` | 300 | 回收线程扫描间隔 |
| `IMAGE_TMP_PROTECT_SEC` | 300 | 该时长内的 tmp 文件**不删**（保护在途任务） |
| `IMAGE_NODE_REFETCH` | true | 清理后是否允许向节点补拉 |

## 3. 回收算法（每个目录独立）

1. **过期清理**：`mtime` 早于 TTL → 删除（tmp 中受保护窗口内的文件除外）。
2. **优先压缩**：仍超限 → 取「最长边 > `IMAGE_COMPRESS_MAX_SIDE`」的**最大**文件压缩（JPEG，覆盖写；PNG 带 alpha 时白底铺平）。
3. **按权重淘汰**：仍超限 → 计算权重升序删除，直到低于上限：
   ```text
   weight = size_bytes × exp(-age_sec / half_life),  half_life = max(60, TTL / 2)
   ```
   语义：**越老权重越低**（优先删旧文件）、同等年龄下**大文件权重更高**（保护大文件不被优先删，先靠压缩解决）。
   tmp 目录跳过保护窗口内的文件。
4. 触发：后台线程每 `IMAGE_CLEAN_INTERVAL_SEC` 一次；每次写入后若已超限立即触发一次（加锁，避免并发重入）。

## 4. 取图接口（需求4）

`GET /tasks/<task_id>/image`

| 项 | 设计 |
|---|---|
| 鉴权 | `X-API-Key`（与 `GET /tasks/<id>` 一致）；同时接受 Bearer JWT（前端用） |
| 命中顺序 | cache（压缩图）→ tmp（原图）→ 节点补拉（若开启且节点仍持有）→ **410 已清理** |
| 查询参数 | `?original=1` 优先原图；`?max_side=N` 服务端即时缩放（不落盘） |
| 响应头 | `Content-Type`、`Content-Length`、`X-Image-Source: cache\|tmp\|node`、`Cache-Control: private, max-age=...` |
| 410 响应 | `{success:false, code:"IMAGE_EXPIRED", message:"图片已过期", task_id, image:{...元数据}}`（元数据来自 task_results，便于前端显示占位） |

## 5. 节点侧（CLI）

- **多人物**（需求1）：`detect()` 取全部 person 框 → 逐框裁剪（可配外扩比例 `CROP_MARGIN_RATIO`，默认 0.08）→ 逐个分类 → 组装 `characters[]`（含原图归一化 bbox）。
- **裁剪方式**（需求2）：`CROP_METHOD=yolo|mediapipe|auto`（默认 auto）；auto = YOLO 有框用 YOLO，否则 mediapipe，再否则整图；mediapipe 未安装时静默降级。
- **节点保留图片**：`IMAGE_RETAIN_SEC`（默认 900）内不删本地图片，供服务端补拉（新增协议消息 `image_request` / `image_response`）。

## 6. 兼容性

- 老前端：`/upload`、`/tasks/<id>` 响应**只加字段不改字段**（沿用已定的灰度策略），顶层 `class_probs` 语义不变。
- `/www` 本轮不改（用户明确）。
- 服务端新增依赖：**无**（只用 Pillow，已装）。

## 7. 分阶段实施

| 阶段 | 内容 | 状态 |
|---|---|---|
| A | 配置项 + `storage_service`（tmp/cache 读写、压缩、回收、统计）+ 单测 | ✅ 完成（15 个单测） |
| B | 上传落盘 + `GET /tasks/<id>/image`（含 410 语义）+ 单测 | ✅ 完成（10 个单测 + 端到端 9/9） |
| C | CLI 多人物检测/裁剪/识别 + `characters[]` 契约（需求1） | ✅ 完成（13 个单测） |
| D | mediapipe 裁剪方式 + 可配置/回退（需求2） | ✅ 完成（11 个单测；mediapipe 未装时自动跳过） |
| E | 节点补拉图片（协议 `image_request`/`image_response` + 节点保留期） | ✅ 完成（服务端 10 个单测 + 节点侧 4 个） |

## 8.5 图片补拉（需求3 后半，2026-09-25 完成）

服务端临时文件被回收后，前端仍可来取图——此时向**处理过该任务的节点**要一份：

    GET /tasks/<id>/image
      -> 本地 cache/tmp 都没有
      -> 查 task_results.node_id（该任务由谁完成）
      -> TCP 发 image_request {request_id, task_id}
      <- 节点回 image_response {request_id, image_data(base64), image_size, image_filename}
      -> 写回 tmp + cache，再按原参数（含 max_side）读一次
    节点离线 / 已过保留期 / 超时(8s) -> 410 + code=IMAGE_EXPIRED

| 位置 | 内容 |
|---|---|
| `src/server/services/image_refetch.py` | 请求/应答配对（request_id → Event），超时 8s，并发上限 64 |
| `src/server/services/listen_service.py` | 新增 `image_response` 分支（要求连接已认证） |
| `src/server/services/message_handlers.py` | `async_handle_image_response`；任务结果写入 `task_results.node_id`（列缺失时 1054 兜底退回旧 SQL） |
| `src/server/routes/upload_routes.py` | `_task_node_id()` + `_try_refetch()`，命中后写回本地 |
| `src/cli/services/node_service.py` | `retained_images` 保留 `IMAGE_RETAIN_SEC`（默认 900s）+ 过期清扫 + `build_image_response_payload()` 应答 |
| 数据库 | `task_results.node_id INT NULL`（`scripts/alter_tables.sql` / `install.sql`，已应用到线上库） |
| 开关 | `IMAGE_NODE_REFETCH`（服务端，默认 true）、`IMAGE_RETAIN_SEC`（节点侧，0 = 恢复"推理完即删"旧行为） |

## 8.6 mediapipe 安装与内存（2026-09-25）

pip 在本机走不通（PyPI TCP 可达但 pip 一直挂），因此**从同机 Upants 的 venv 本地搬运**（同为 Python 3.12.9）：

| 项 | 大小 |
|---|---|
| mediapipe 0.10.14 包 | 98.5 MB（其中 .tflite 模型 27.8 MB） |
| 依赖：protobuf 4.25.9 / absl-py 2.5.0 / attrs 26.1.0 / flatbuffers 25.12.19 / sounddevice 0.5.5 | 4.6 MB |
| **合计新增** | **103.1 MB** |
| **跳过** | jax 26.7 MB + jaxlib **240.5 MB**（仅 genai 转换器用到，`import mediapipe` 实测不需要，未打补丁） |

运行时内存（.venv, Windows）：基线 14 MB → `import mediapipe` 后 **81 MB** → 人脸检测后 **85 MB** → 姿态（lite）**91 MB**。
会话每次调用创建并释放（不常驻）；省内存旋钮：`MEDIAPIPE_POSE_COMPLEXITY`（默认 **0=lite**）、`MEDIAPIPE_FACE_MODEL_SELECTION`（默认 1=全景模型）。
若换机器用 `pip install -r src/cli/requirements.txt` 正常安装，会一并装上 jax/jaxlib（多 267 MB）；只要人脸/姿态检测可加 `--no-deps` 后手装上表 5 个小依赖。

## 8.7 实现落点与验收（2026-09-13）

| 需求 | 代码 | 验收 |
|---|---|---|
| 1 多人物 | `src/cli/detection/bbox.py`、`yolo_detector.detect_all/crop_all/crop_characters`、`predictor.predict_image` 的多人物分支 | `tests/cli/test_multi_character.py` 13 通过（含"缩放坐标系 → 原图"映射断言） |
| 2 第二种裁剪 | `src/cli/detection/mediapipe_detector.py`、`src/cli/detection/cropper.py`、`CROP_METHOD`/`MEDIAPIPE_*` 配置 | `tests/cli/test_cropper_fallback.py` 11 通过（auto 三条回退链、mediapipe 缺失不炸） |
| 3 缓存/临时文件 | `src/server/services/storage_service.py`、`config/base.py` 的 9 个 IMAGE_* 配置、`settings_service` 的 6 个可覆盖键、`runserver` 启动回收线程 | `tests/server/test_storage_service.py` 15 通过（压缩、TTL、权重淘汰、保护窗口、目录穿越） |
| 4 取图接口 | `GET /tasks/<task_id>/image`（`upload_routes.get_task_image`）+ `GET /tasks/<id>` 的 `image` 元数据 | `tests/server/test_task_image_endpoint.py` 10 通过；真实实例端到端 9/9（2.88MB 原图 → cache 81KB JPEG） |

环境注意：受限文件沙箱下 `tempfile.mkdtemp()` 出来的目录**不可再写**（WinError 5），
测试统一改用仓库内 `.tmp-tests/`（已 gitignore）；`tests/cli` 里既有的 `tmp_path` 用例在本沙箱会报 PermissionError（与本需求无关）。
