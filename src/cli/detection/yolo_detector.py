"""YOLO 人物检测器 — 快速定位图片中角色区域，裁剪后供 ResNet 分类"""

import os
from pathlib import Path
import shutil
import threading
import traceback

from config.log_config import get_logger
from detection.bbox import (
    bbox_area,
    expand_bbox,
    normalize_bbox,
    percent_bbox,
    scale_bbox,
)

logger = get_logger("yolo_detector")

# 裁剪产物后缀（新标识；兼容旧的 "_yolo" 输入跳过判断）
CROP_SUFFIX = "_37ac"
LEGACY_CROP_SUFFIXES = ("_37ac", "_yolo")

# 全局缓存
_detector_instance = None

# ultralytics / opencv 可用性探测结果（只探一次，失败原因缓存下来）
_AVAILABILITY = {
    "checked": False,
    "ok": False,
    "reason": "",
}

# 服务器上最常见的两种失败：ultralytics 真的没装；装了但 opencv 缺系统库
# （opencv-python 的预编译包依赖 libGL / libglib，纯命令行服务器上常常没有）
_SYSTEM_LIB_HINTS = (
    ("libGL.so.1", "libGL.so.1"),
    ("libGL.so", "libGL.so"),
    ("libglib-2.0.so.0", "libglib-2.0.so.0"),
    ("libgthread-2.0.so.0", "libgthread-2.0.so.0"),
)


def _describe_import_error(exc):
    """把导入异常翻译成"能直接照做"的一句话。

    生产上出现过：ultralytics 明明装了，却因为 opencv 缺 libGL 而 import 失败，
    旧代码统一报"ultralytics 未安装"，把人带偏。
    """
    name = getattr(exc, "name", None) or ""
    text = str(exc)
    missing = name
    if not missing and "'" in text:
        missing = text.split("'")[1]

    for key, shown in _SYSTEM_LIB_HINTS:
        if key in text:
            return ("缺少系统库 %s（opencv 需要）：apt-get install -y libgl1 libglib2.0-0，"
                    "或装无界面版 pip install opencv-python-headless" % shown)

    if missing and missing not in ("cv2", "ultralytics", "opencv"):
        return "缺少依赖 %s：pip install %s" % (missing, missing)

    if missing == "cv2" or "cv2" in text:
        return "opencv 不可用（YOLO 依赖 cv2）：检查 opencv-python 安装，服务器建议 opencv-python-headless"

    if isinstance(exc, ImportError):
        return "ultralytics 未安装或依赖不全：pip install -r src/cli/requirements.txt"

    return "%s: %s" % (type(exc).__name__, exc)


def check_yolo_available(force=False):
    """探测 YOLO 是否可用，返回 (ok, 原因)。

    只探一次（force=True 可重探）；结果缓存在模块级，避免"每张图 import 一次、
    每张图刷一遍同样的 warning"。原因同时供注册消息 / 识别结果使用。
    """
    if _AVAILABILITY["checked"] and not force:
        return _AVAILABILITY["ok"], _AVAILABILITY["reason"]

    _AVAILABILITY.update({"checked": True, "ok": False, "reason": ""})

    # 1) opencv：ultralytics 的硬依赖，也是服务器上最容易缺系统库的一环
    try:
        import cv2  # noqa: F401
    except Exception as exc:
        reason = "opencv 不可用（YOLO 依赖）：" + _describe_import_error(exc)
        _AVAILABILITY["reason"] = reason
        logger.warning("YOLO 不可用：%s", reason)
        logger.debug("opencv 导入堆栈：\n%s", traceback.format_exc())
        return False, reason

    # 2) ultralytics 本体
    try:
        import ultralytics  # noqa: F401
    except Exception as exc:
        reason = "ultralytics 不可用：" + _describe_import_error(exc)
        _AVAILABILITY["reason"] = reason
        logger.warning("YOLO 不可用：%s", reason)
        logger.debug("ultralytics 导入堆栈：\n%s", traceback.format_exc())
        return False, reason

    _AVAILABILITY["ok"] = True
    return True, ""


def yolo_available():
    """给外部用：YOLO 能不能用 + 不能用是为什么（注册消息 / 识别结果里带上）。"""
    return check_yolo_available()


class YoloDetector:
    """基于 Ultralytics YOLOv8 的目标检测器。

    使用预训练模型（yolov8n.pt）快速定位图片中的人物/角色区域，
    返回裁剪后的区域，供 ResNet 进一步分类识别。
    """

    def __init__(self, model_path=None, conf_threshold=None, device=None):
        self.model_path = model_path
        self.conf_threshold = conf_threshold or 0.25
        self.device = device
        self._model = None
        self._loaded = False
        # 失败过就不再重试：既不刷日志，也不重复付 import 的代价
        self._load_failed = False
        self.load_error = ""

    def _load_model(self):
        """加载 YOLO 模型（首次使用时延迟加载）"""
        if self._loaded:
            return True
        if self._load_failed:
            return False

        ok, reason = check_yolo_available()
        if not ok:
            self._load_failed = True
            self.load_error = reason
            return False

        try:
            from ultralytics import YOLO

            model_path = self.model_path or "yolov8n.pt"
            # 统一成绝对路径：相对名（含空值退化出来的 "yolov8n.pt"）一律落到 saves/models，
            # 否则 Ultralytics 会在**当前工作目录**下载一份，多线程并发下载还会卡死
            try:
                from config.base import MODEL_DIR as _MODEL_DIR
                _p = Path(model_path)
                if not _p.is_absolute():
                    model_path = str(_MODEL_DIR / _p.name)
            except Exception:
                pass

            # 如果指定路径存在，直接加载；否则交给 Ultralytics 自动下载
            if os.path.exists(model_path):
                logger.info("加载 YOLO 模型: %s", model_path)
            else:
                logger.info("YOLO 模型文件不存在: %s（将使用 Ultralytics 自动下载）", model_path)

            self._model = YOLO(model_path)
            self._loaded = True
            logger.info("YOLO 模型加载成功")
            return True

        except ImportError as e:
            # 注意：这里不是"没装"的同义词 —— cv2 缺系统库、子依赖缺失都会走这里
            self._load_failed = True
            self.load_error = _describe_import_error(e)
            logger.warning("YOLO 检测不可用：%s", self.load_error)
            logger.debug("YOLO 导入堆栈：\n%s", traceback.format_exc())
            return False
        except Exception as e:
            self._load_failed = True
            self.load_error = "YOLO 模型加载失败：%s: %s" % (type(e).__name__, e)
            logger.error("%s", self.load_error)
            logger.debug("YOLO 加载堆栈：\n%s", traceback.format_exc())
            return False

    def detect(self, image):
        """检测图片中的人物/主体区域。

        Args:
            image: 图片路径，或已加载（可缩放后）的 PIL.Image

        Returns:
            list[dict]: 检测到的区域列表，每个区域包含:
                {
                    "bbox": (x1, y1, x2, y2),     # 图片坐标
                    "confidence": float,            # 置信度
                    "class_id": int,               # YOLO 类别 ID
                    "class_name": str,             # YOLO 类别名称
                }
            若未检测到任何目标或 YOLO 不可用，返回空列表。
        """
        if not self._load_model():
            return []
        if getattr(self, "_model_broken", False):
            # 上一次推理抛过异常：模型可能残留了坏状态（DML 下尤其明显），重建再跑
            logger.warning("上次推理异常，重建 YOLO 模型实例")
            self._loaded = False
            self._model = None
            self._model_broken = False
            if not self._load_model():
                return []

        try:
            results = self._model(
                image,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )

            detections = []
            if not results or len(results) == 0:
                return detections

            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return detections

            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].tolist()
                conf = float(boxes.conf[i])
                cls_id = int(boxes.cls[i])
                cls_name = results[0].names[cls_id] if results[0].names else str(cls_id)

                detections.append({
                    "bbox": tuple(int(v) for v in xyxy),
                    "confidence": round(conf, 3),
                    "class_id": cls_id,
                    "class_name": cls_name,
                })

            # 按置信度降序排列
            detections.sort(key=lambda d: d["confidence"], reverse=True)
            logger.debug("YOLO 检测到 %d 个目标: %s", len(detections),
                         [d["class_name"] for d in detections])
            return detections

        except Exception as e:
            # 标记为损坏：下一次调用会重建模型，避免"一次异常之后再也不用不了/卡死"
            self._model_broken = True
            logger.error("YOLO 检测失败（本图已跳过，模型将在下次调用时重建）: %s", e)
            return []

        finally:
            # 每次检测后清掉 ultralytics 的预测器缓存。
            # 它内部在 torch.inference_mode() 下跑推理，缓存里的 inference tensor 一旦被
            # 后续原地操作就会报 "Cannot set version_counter for inference tensor"，
            # 而且**从此每张图都失败**（状态被污染）；清掉缓存即恢复。
            try:
                if self._model is not None:
                    self._model.predictor = None
            except Exception:
                pass

    def detect_and_crop(self, image_path: str, target_classes=None, suffix=CROP_SUFFIX,
                        output_dir=None, max_size: int = 0):
        """检测并裁剪出最佳目标区域。

        先压缩再裁剪：max_size>0 时，先把图片最长边缩到 max_size 以内再做检测，
        这样 YOLO 处理的是小图，速度快很多；裁剪结果也已经是压缩后的尺寸。

        Args:
            image_path: 图片路径
            target_classes: 只关注的目标类别列表（如 ["person"]），None 表示全部
            suffix: 裁剪后文件名后缀，默认 "_37ac"
            output_dir: 裁剪结果保存目录（None 表示与原图同目录）
            max_size: 图片最长边上限（0=不压缩）

        Returns:
            tuple: (cropped_image_path_or_none, detection_info_or_none)
                - 裁剪后的图片路径（保存为临时文件）
                - 检测信息 dict
            若未检测到目标或 YOLO 不可用，返回 (None, None)
        """
        from PIL import Image

        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:
            logger.error("YOLO 裁剪失败（图片无法读取）: %s", e)
            return None, None

        # 先压缩：最长边缩到 max_size 以内
        if max_size and max_size > 0 and max(img.size) > max_size:
            width, height = img.size
            ratio = max_size / float(max(width, height))
            img = img.resize(
                (max(1, int(width * ratio)), max(1, int(height * ratio))),
                Image.LANCZOS,
            )

        detections = self.detect(img)
        if not detections:
            return None, None

        # 按目标类别过滤
        if target_classes:
            filtered = [d for d in detections if d["class_name"] in target_classes]
            if not filtered:
                logger.debug(
                    "目标类别 %s 未检测到，跳过 %s", target_classes, image_path
                )
                return None, None
            detections = filtered

        if not detections:
            return None, None

        best = detections[0]
        bbox = best["bbox"]

        try:
            cropped = img.crop(bbox)

            # 确定输出路径：优先 output_dir，否则与原图同目录
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                crop_path = os.path.join(output_dir, f"{name}{suffix}{ext}")
            else:
                base, ext = os.path.splitext(image_path)
                crop_path = f"{base}{suffix}{ext}"

            cropped.save(crop_path)
            logger.info("YOLO 裁剪区域: %s, 类别=%s, 置信度=%.2f → %s",
                        bbox, best["class_name"], best["confidence"], crop_path)
            return crop_path, best

        except Exception as e:
            logger.error("YOLO 裁剪失败: %s", e)
            return None, None


    def detect_and_crop_bytes(self, image_path, target_classes=None, max_size: int = 0,
                              quality: int = 90, margin_ratio: float = 0.0,
                              detect_max_size: int = 0):
        """内存内一次完成：缩略图检测 → 坐标映射回原图 → 从原图裁剪 → 压缩编码。

        与 detect_and_crop 的区别（也是它存在的理由）：
        - 检测在**缩略副本**上做（快），框按比例映射回**原图**坐标；
        - 裁剪从**原图**取像素（而不是从缩略图），细节不丢；
        - 结果以压缩后的字节返回，**不落任何临时文件**，调用方可直接写数据集目录。

        Args:
            image_path: 原图路径
            target_classes: 只关注的目标类别（默认 ["person"]）
            max_size: 输出最长边上限（0=不缩放），即"压缩"的尺寸
            quality: JPEG 质量（1-100）
            margin_ratio: 裁剪框外扩比例
            detect_max_size: 检测用缩略图的最长边（0=用 YOLO_DETECT_MAX_SIZE）

        Returns:
            (image_bytes, info)：info 含 bbox(原图坐标)/confidence/class_name/image_size/ext；
            未检出目标或失败返回 (None, None)
        """
        from PIL import Image

        from utils.image_utils import encode_image_bytes

        if target_classes is None:
            target_classes = ["person"]

        try:
            with Image.open(image_path) as raw:
                original = raw.convert("RGB")
                original_size = original.size
        except Exception as e:
            logger.error("YOLO 裁剪失败（图片无法读取）: %s", e)
            return None, None

        limit = int(detect_max_size or 0)
        if limit <= 0:
            try:
                from config.base import YOLO_DETECT_MAX_SIZE
                limit = int(YOLO_DETECT_MAX_SIZE or 0)
            except Exception:
                limit = 0

        # ① 检测用小图（只在内存里缩小；下面仍从原图裁剪）
        work = original
        if limit and max(original_size) > limit:
            ratio = limit / float(max(original_size))
            work = original.resize(
                (max(1, int(original_size[0] * ratio)), max(1, int(original_size[1] * ratio))),
                Image.LANCZOS,
            )
        try:
            # 传"干净的像素数组"而不是 PIL 对象：
            # 图片若带 GBK 等非 UTF-8 元数据（iCCP/tEXt 块），ultralytics 读取 PIL 的
            # info/filename 时会抛 'utf-8' codec can't decode...，这里从源头绕开
            try:
                import numpy as _np
                detections = self.detect(_np.asarray(work.convert("RGB")))
            except ImportError:
                detections = self.detect(work)
            detected_size = work.size
        finally:
            if work is not original:
                work.close()

        if target_classes:
            detections = [d for d in detections if d.get("class_name") in target_classes]
        if not detections:
            return None, None

        # ② 坐标映射回原图 → 质量门控 → 面积大者优先
        candidates = []
        for det in detections:
            box = scale_bbox(det["bbox"], detected_size, original_size)
            candidates.append({
                "bbox": box,
                "detector_confidence": det.get("confidence"),
                "_det": det,
            })

        try:
            from detection.cropper import gate_detections
            # 数据集裁剪：源图常常本身就是紧裁剪的立绘，"框几乎占满整图"是正常的，
            # 因此只按置信度 / 面积下限 / 长宽比过滤，不套用识别路径的"最大面积"规则
            gated = gate_detections(candidates, original_size, dataset=True)
        except Exception as gate_err:
            logger.debug("裁剪质量门控不可用，跳过: %s", gate_err)
            gated = candidates

        if not gated:
            logger.debug("候选框全部被裁剪质量门控过滤: %s", image_path)
            return None, None

        best_item = max(gated, key=lambda item: bbox_area(item["bbox"]))
        best = dict(best_item["_det"], bbox=best_item["bbox"])

        box = expand_bbox(best["bbox"], original_size, margin_ratio)

        # ③ 从原图裁剪 → 压缩编码（全在内存里完成）
        try:
            crop = original.crop(box)
            data, ext = encode_image_bytes(crop, max_size=max_size, quality=quality)
            crop.close()
        except Exception as e:
            logger.error("YOLO 裁剪失败（内存裁剪）: %s", e)
            return None, None
        finally:
            original.close()

        if not data:
            return None, None

        info = {
            "bbox": box,
            "detector_bbox": best["bbox"],
            "confidence": best.get("confidence"),
            "class_id": best.get("class_id"),
            "class_name": best.get("class_name"),
            "image_size": original_size,
            "detected_size": detected_size,
            "ext": ext,
            "bytes": len(data),
        }
        logger.debug("内存裁剪: %s bbox=%s 置信度=%.2f → %d 字节 %s",
                     image_path, box, best.get("confidence") or 0.0, len(data), ext)
        return data, info

    def detect_all(self, image_path, max_size: int = 0, target_classes=("person",)):
        """多目标检测，并把检测框映射回**原图**坐标系（需求1）。

        与 detect() 的区别：
        - 检测前可选缩放（max_size）加速；返回的坐标已换算回原图
          （detect() 返回的是缩放后坐标系，直接用会让百分比坐标全错）
        - 只保留 target_classes（默认 person），按检测框**面积降序**（大的人物优先）

        Returns:
            dict: {
                "image_size": (w, h),      # 原图尺寸（百分比坐标的分母）
                "detected_size": (w, h),   # 实际送入 YOLO 的尺寸
                "detections": [{"bbox": (x1,y1,x2,y2) 原图坐标, "area", "confidence",
                                "class_id", "class_name"}, ...],
            }
        """
        from PIL import Image

        empty = {"image_size": (0, 0), "detected_size": (0, 0), "detections": []}
        try:
            with Image.open(image_path) as raw:
                original_size = raw.size
                work = raw.convert("RGB")
        except Exception as e:
            logger.error("多目标检测失败（图片无法读取）: %s", e)
            return empty

        if max_size and max(work.size) > max_size:
            width, height = work.size
            ratio = max_size / float(max(width, height))
            work = work.resize(
                (max(1, int(width * ratio)), max(1, int(height * ratio))),
                Image.LANCZOS,
            )

        detections = self.detect(work)
        if target_classes:
            detections = [d for d in detections if d.get("class_name") in target_classes]
        if not detections:
            return {"image_size": original_size, "detected_size": work.size, "detections": []}

        results = []
        for det in detections:
            box = scale_bbox(det["bbox"], work.size, original_size)
            results.append({
                "bbox": box,
                "area": bbox_area(box),
                "confidence": det["confidence"],
                "class_id": det["class_id"],
                "class_name": det["class_name"],
            })
        results.sort(key=lambda item: item["area"], reverse=True)
        logger.info(
            "多目标检测: %d 个目标（原图 %s，检测用图 %s）",
            len(results), original_size, work.size,
        )
        return {"image_size": original_size, "detected_size": work.size, "detections": results}

    def crop_all(self, image_path, detections, output_dir, margin_ratio: float = 0.0,
                 suffix: str = CROP_SUFFIX, ext: str = ".jpg"):
        """按原图坐标逐个裁剪并保存，返回 [{"index", "crop_path", "bbox", ...}]。"""
        from PIL import Image

        crops = []
        try:
            with Image.open(image_path) as raw:
                img = raw.convert("RGB")
                size = img.size
        except Exception as e:
            logger.error("多目标裁剪失败（图片无法读取）: %s", e)
            return crops

        os.makedirs(output_dir, exist_ok=True)
        name = os.path.splitext(os.path.basename(image_path))[0]
        for index, det in enumerate(detections):
            box = expand_bbox(det["bbox"], size, margin_ratio)
            try:
                crop = img.crop(box)
                path = os.path.join(output_dir, f"{name}_{index}{suffix}{ext}")
                crop.save(path)
                crops.append({
                    "index": index,
                    "crop_path": path,
                    "bbox": box,
                    "detector_confidence": det.get("confidence"),
                    "class_name": det.get("class_name"),
                })
            except Exception as e:
                logger.warning("裁剪第 %d 个目标失败: %s", index, e)
        return crops


def _role_matches(key: str, patterns) -> bool:
    """角色是否命中指定模式。

    支持：完整 "IP/角色"、只用角色名（"白子"）、带通配符（"蔚蓝档案/*"、"*白子*"）。
    匹配不区分大小写，忽略首尾空白。
    """
    import fnmatch

    key_l = key.strip().lower()
    role_l = key_l.split("/")[-1]
    for raw in patterns:
        pat = str(raw).strip().lower()
        if not pat:
            continue
        if pat == key_l or pat == role_l:
            return True
        if "*" in pat or "?" in pat:
            if fnmatch.fnmatch(key_l, pat) or fnmatch.fnmatch(role_l, pat):
                return True
        elif pat in key_l:          # 子串匹配：输入"白子"也能命中"蔚蓝档案/白子"
            return True
    return False


def _tmp_root() -> Path:
    """临时根目录：固定在 saves/tmp 下。

    为什么不用默认的 tempfile.gettempdir()：当 TMPDIR/TEMP 等候选目录都不可用时，
    tempfile 会**退回到当前工作目录**，于是 mkdtemp 会在仓库根留下 37ac_yolo_* 目录
    （而且 mkdtemp 用 0o700 建目录，沙箱/普通权限下连删除都困难）。
    """
    from config.base import ROOT_PATH

    root = Path(ROOT_PATH) / "saves" / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


# 模块级便捷函数
def _new_detector() -> YoloDetector:
    """创建一个新的 YOLO 检测器（供线程独立使用）。"""
    from config.base import YOLO_MODEL_PATH, YOLO_CONFIDENCE, YOLO_DEVICE, get_device

    # YOLO 检测设备与训练设备解耦（见 YOLO_DEVICE 注释）：
    #   cpu（默认）→ 稳定；dml → 走 DirectML（有卡死风险）；cuda → N 卡；auto → 交给 YOLO 自选
    if YOLO_DEVICE == "cpu":
        yolo_device = "cpu"
    elif YOLO_DEVICE == "cuda":
        yolo_device = "cuda"
    elif YOLO_DEVICE == "dml":
        yolo_device = get_device()
    else:
        yolo_device = None
    return YoloDetector(
        model_path=YOLO_MODEL_PATH,
        conf_threshold=YOLO_CONFIDENCE,
        device=yolo_device,
    )


def get_detector():
    """获取（缓存）YOLO 检测器实例（单线程场景）"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _new_detector()
    return _detector_instance


# 线程本地检测器：每个裁剪线程独立一个 YOLO 模型，避免共享模型导致线程安全问题
_thread_local = threading.local()


def _get_thread_detector() -> YoloDetector:
    """获取当前线程的 YOLO 检测器（不存在则创建并加载模型）。"""
    detector = getattr(_thread_local, "detector", None)
    if detector is None:
        detector = _new_detector()
        detector._load_model()
        _thread_local.detector = detector
    return detector


def crop_dataset(source_dir: str, output_dir: str, target_classes=None,
                 max_images_per_role: int = 100, cancel_event=None,
                 only_roles=None, reset_roles=False):
    """遍历数据集目录，对每张图片执行 YOLO 检测并裁剪人物区域。

    裁剪全程在内存里完成（缩略图检测 → 坐标映射回原图 → 从原图裁剪 → 压缩编码），
    结果**直接写入 output_dir**，不再产生临时文件；文件名为 `_37ac` 后缀（统一 JPEG）。
    未检测到目标的图不复制，而是留到最后的「整图补足」阶段（见 DATASET_FILL_UNCROPPED）。
    每个角色最多保留 max_images_per_role 张图片，优先选择大图和 person 检测结果。
    若配置 DATASET_COMPRESS_SIZE>0，裁剪完成后会自动压缩数据集图片。

    Args:
        source_dir: 原始数据集根目录（IP/角色/图片.jpg）
        output_dir: 输出目录（saves/dataset），目录结构自动镜像 source_dir
        target_classes: 只关注的目标类别，默认 ["person"]
        max_images_per_role: 单个角色最大保存图片数量

    Returns:
        dict: { "processed": int, "skipped": int, "failed": int }
    """
    if target_classes is None:
        target_classes = ["person"]

    ok, reason = check_yolo_available()
    if not ok:
        logger.warning("无法用 YOLO 裁剪数据集：%s", reason)
        return {"processed": 0, "skipped": 0, "failed": 0}

    from config.log_config import get_logger as _get_logger
    _logger = _get_logger("crop_dataset")

    from common.constants import IMAGE_EXTENSIONS_BASIC as image_extensions
    from config.base import (
        YOLO_CROP_WORKERS,
        DATASET_COMPRESS_SIZE,
        DATASET_COMPRESS_QUALITY,
        DATASET_FILL_UNCROPPED,
        DATASET_IGNORE_CLEAN,
        DATASET_CROP_MARGIN_RATIO,
        is_in_ignore_list,
    )
    from utils.concurrency import CancelToken, interruptible_map

    _logger.info("开始 YOLO 裁剪: %s → %s", source_dir, output_dir)

    # 收集所有角色任务，按角色并行
    role_tasks = []
    for ip_name in sorted(os.listdir(source_dir)):
        ip_path = os.path.join(source_dir, ip_name)
        if not os.path.isdir(ip_path) or ip_name.startswith("."):
            continue
        for role_name in sorted(os.listdir(ip_path)):
            role_path = os.path.join(ip_path, role_name)
            if not os.path.isdir(role_path) or role_name.startswith("."):
                continue
            role_tasks.append((ip_name, role_name, role_path))

    # 「不处理列表」：命中的源目录**完全不管**（不进数据集），并从任务里剔除
    ignored_tasks = [t for t in role_tasks if is_in_ignore_list(t[2])]
    role_tasks = [t for t in role_tasks if not is_in_ignore_list(t[2])]
    if ignored_tasks:
        _logger.info(
            "「不处理列表」命中 %d 个目录，已完全跳过（不进数据集）: %s",
            len(ignored_tasks), ", ".join("%s/%s" % (i, r) for i, r, _p in ignored_tasks),
        )
        if DATASET_IGNORE_CLEAN:
            for ip_name_i, role_name_i, _p in ignored_tasks:
                stale_dir = os.path.join(output_dir, ip_name_i, role_name_i)
                if os.path.isdir(stale_dir) and os.listdir(stale_dir):
                    stale_count = len(os.listdir(stale_dir))
                    shutil.rmtree(stale_dir, ignore_errors=True)
                    _logger.warning(
                        "已清理该目录在数据集中的旧产物: %s/%s（%d 个文件）",
                        ip_name_i, role_name_i, stale_count,
                    )

    # ==================== 指定角色裁剪 ====================
    # only_roles 为空 = 全部裁剪；否则只裁剪匹配到的角色（避免每次全局重裁产生脏数据）
    if only_roles:
        patterns = [str(p).strip() for p in only_roles if str(p).strip()]
        matched, unmatched = [], []
        for task in role_tasks:
            key = "%s/%s" % (task[0], task[1])
            if _role_matches(key, patterns):
                matched.append(task)
            else:
                unmatched.append(key)
        role_tasks = matched
        _logger.info("指定裁剪：匹配到 %d 个角色/%d 个模式：%s",
                     len(role_tasks), len(patterns),
                     ", ".join("%s/%s" % (i, r) for i, r, _p in role_tasks[:20]) or "无")
        if not role_tasks:
            _logger.warning("没有角色匹配这些模式: %s", ", ".join(patterns))
            return {"processed": 0, "skipped": 0, "failed": 0, "whole": 0,
                    "ignored": len(ignored_tasks), "interrupted": False,
                    "matched_roles": 0}

        if reset_roles:
            cleared = 0
            for ip_name_c, role_name_c, _p in role_tasks:
                stale = os.path.join(output_dir, ip_name_c, role_name_c)
                if os.path.isdir(stale) and os.listdir(stale):
                    cleared += len(os.listdir(stale))
                    shutil.rmtree(stale, ignore_errors=True)
            _logger.warning("已清空 %d 个角色的旧产物（共 %d 个文件），将重新裁剪",
                            len(role_tasks), cleared)

    def process_role(ip_name, role_name, role_path, token=None):
        """处理单个角色（在线程内执行，使用线程本地 detector）。

        token（CancelToken）用于协作式取消：每个角色/每张图前检查一次，
        收到 Ctrl+C 后能马上停下来，而不是把整个角色跑完。
        """
        local = {"processed": 0, "skipped": 0, "failed": 0, "whole": 0}
        if token is not None and token.cancelled():
            return local
        detector = _get_thread_detector()

        out_role_dir = os.path.join(output_dir, ip_name, role_name)
        existing_files = []
        if os.path.exists(out_role_dir):
            existing_files = [
                f for f in os.listdir(out_role_dir)
                if f.lower().endswith(image_extensions)
            ]

        if len(existing_files) >= max_images_per_role:
            _logger.info(
                "角色 %s/%s 已有 %d 张图片（>= %d），跳过裁剪",
                ip_name, role_name, len(existing_files), max_images_per_role
            )
            local["skipped"] += len(existing_files)
            return local

        role_images = []
        for fname in os.listdir(role_path):
            if not fname.lower().endswith(image_extensions):
                continue

            base_name, ext = os.path.splitext(fname)
            if base_name.endswith(LEGACY_CROP_SUFFIXES):
                continue

            src_img = os.path.join(role_path, fname)
            try:
                file_size = os.path.getsize(src_img)
            except OSError:
                file_size = 0
            role_images.append((src_img, fname, file_size))

        # 先按文件大小降序处理，优先保留高质量大图
        role_images.sort(key=lambda item: item[2], reverse=True)

        saved_count = len(existing_files)
        created_role_dir = False
        # 裁剪不出人物的图先攒着：等裁剪全部跑完，若仍不足 MAX_IMAGES_PER_ROLE 再用整图补足
        uncropped_candidates = []
        for src_img, fname, file_size in role_images:
            if saved_count >= max_images_per_role:
                break
            if token is not None and token.cancelled():
                break

            base_name, ext = os.path.splitext(fname)
            # 新流程统一输出 JPEG；同时检查旧命名的产物，避免续跑时重复处理
            yolo_out = os.path.join(out_role_dir, f"{base_name}{CROP_SUFFIX}.jpg")
            yolo_out_legacy = os.path.join(out_role_dir, f"{base_name}{CROP_SUFFIX}{ext}")
            original_out = os.path.join(out_role_dir, fname)

            if (os.path.exists(yolo_out) or os.path.exists(yolo_out_legacy)
                    or os.path.exists(original_out)):
                local["skipped"] += 1
                continue

            if not created_role_dir:
                os.makedirs(out_role_dir, exist_ok=True)
                created_role_dir = True

            try:
                # 内存内完成：缩略图检测 → 坐标映射回原图 → 从原图裁剪 → 压缩编码；
                # 拿到字节后**直写数据集目录**，不再经过临时文件（少一次写+读+move）
                data, info = detector.detect_and_crop_bytes(
                    src_img, target_classes=target_classes,
                    max_size=DATASET_COMPRESS_SIZE, quality=DATASET_COMPRESS_QUALITY,
                    margin_ratio=DATASET_CROP_MARGIN_RATIO,
                )
                if data:
                    out_ext = (info or {}).get("ext") or ".jpg"
                    out_path = os.path.join(out_role_dir, f"{base_name}{CROP_SUFFIX}{out_ext}")
                    with open(out_path, "wb") as fh:
                        fh.write(data)
                    local["processed"] += 1
                    saved_count += 1
                    _logger.debug("YOLO 裁剪(内存直出): %s → %s（%d 字节）",
                                  src_img, out_path, len(data))
                else:
                    # 未裁剪出人物：留到「整图补足」阶段（见下），此处只登记候选
                    uncropped_candidates.append((src_img, fname))
                    _logger.debug("未裁剪出人物（待整图补足）: %s", src_img)
            except Exception as e:
                _logger.error("处理失败 %s: %s", src_img, e)
                local["failed"] += 1

        # ==================== 整图补足 ====================
        # 裁剪成功数不足 MAX_IMAGES_PER_ROLE 时，用「未裁剪出人物」的原图（压缩后）补齐；
        # 因为整图永远是兜底，不会挤掉本可以裁出人物的样本。
        filled = 0
        if DATASET_FILL_UNCROPPED and saved_count < max_images_per_role and uncropped_candidates:
            need = max_images_per_role - saved_count
            _logger.info(
                "角色 %s/%s 裁剪后 %d 张（上限 %d），用整图压缩补足 %d 张",
                ip_name, role_name, saved_count, max_images_per_role,
                min(need, len(uncropped_candidates)),
            )
            from utils.image_utils import compress_image_file
            for src_img, fname in uncropped_candidates:
                if need <= 0 or (token is not None and token.cancelled()):
                    break
                # 整图补足：命名与裁剪产物统一（_37ac + JPEG），
                # 同样走内存压缩（缩放 + JPEG 质量），不再原样复制大体积 PNG
                fill_base, _fill_ext = os.path.splitext(fname)
                original_out = os.path.join(out_role_dir, f"{fill_base}{CROP_SUFFIX}.jpg")
                if os.path.exists(original_out):
                    local["skipped"] += 1
                    continue
                try:
                    if not created_role_dir:
                        os.makedirs(out_role_dir, exist_ok=True)
                        created_role_dir = True
                    from PIL import Image as _Image
                    from utils.image_utils import encode_image_bytes
                    with _Image.open(src_img) as _raw:
                        _rgb = _raw.convert("RGB")
                    _data, _ = encode_image_bytes(
                        _rgb, max_size=DATASET_COMPRESS_SIZE,
                        quality=DATASET_COMPRESS_QUALITY,
                    )
                    _rgb.close()
                    if not _data:
                        raise ValueError("整图编码失败")
                    with open(original_out, "wb") as _fh:
                        _fh.write(_data)
                    local["processed"] += 1
                    local["whole"] += 1
                    saved_count += 1
                    filled += 1
                    need -= 1
                    _logger.debug("整图补足: %s → %s", src_img, original_out)
                except Exception as e:
                    _logger.error("整图补足失败 %s: %s", src_img, e)
                    local["failed"] += 1
        # 没被用上的候选（上限已满 / 开关关闭）按旧口径记为 skipped
        local["skipped"] += max(0, len(uncropped_candidates) - filled)

        if os.path.isdir(out_role_dir) and not os.listdir(out_role_dir):
            # 当前角色没有写入任何新文件，删除可能产生的空目录
            try:
                os.rmdir(out_role_dir)
            except OSError:
                pass
        return local

    workers = max(1, int(YOLO_CROP_WORKERS or 1))
    _logger.info("YOLO 裁剪并发线程数: %d（共 %d 个角色）", workers, len(role_tasks))

    counters = {"processed": 0, "skipped": 0, "failed": 0, "whole": 0}
    counters_lock = threading.Lock()

    def _accumulate(task, result):
        with counters_lock:
            if isinstance(result, dict):
                for key in counters:
                    counters[key] += result.get(key, 0) or 0
            else:
                counters["failed"] += 1

    # 线程池启动前先在本线程把权重准备好：
    # ① Ultralytics 需要下载时只发生一次（多线程同时下载会卡死）
    # ② 权重不可用就立刻失败退出，而不是让每个角色都报一次同样的错
    _warmup = _new_detector()
    if not _warmup._load_model():
        _logger.error("YOLO 权重不可用，已中止裁剪: %s", _warmup.load_error or "未知原因")
        return {"processed": 0, "skipped": 0, "failed": 0, "whole": 0, "ignored": 0,
                "interrupted": False}

    token = cancel_event if cancel_event is not None else CancelToken()
    interrupted = False
    if role_tasks:
        interrupted, _ = interruptible_map(
            lambda task, tok: process_role(task[0], task[1], task[2], tok),
            role_tasks,
            max_workers=workers,
            cancel_token=token,
            desc=f"YOLO裁剪({workers}线程)",
            unit="角色",
            on_done=_accumulate,
        )

    processed = counters["processed"]
    skipped = counters["skipped"]
    failed = counters["failed"]
    whole = counters["whole"]
    interrupted = interrupted or token.cancelled()
    _logger.info(
        "数据集裁剪%s: 已处理=%d（其中裁剪不足用整图补足 %d）, 跳过=%d, 失败=%d, 忽略目录=%d"
        "（输出已按最长边 %d 压缩）",
        "已中断" if interrupted else "完成",
        processed, whole, skipped, failed, len(ignored_tasks), DATASET_COMPRESS_SIZE,
    )
    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "whole": whole,
        "ignored": len(ignored_tasks),
        "interrupted": interrupted,
        "matched_roles": len(role_tasks),
    }


def detect_characters(image_path: str) -> list:
    """检测图片中的人物区域（快捷入口）"""
    return get_detector().detect(image_path)


def crop_characters(image_path: str, max_characters: int = None, max_size: int = None,
                    margin_ratio: float = None, output_dir: str = None) -> dict:
    """多人物检测 + 逐个裁剪（需求1 的节点侧入口）。

    Returns:
        dict: {
            "image_size": (w, h), "detected_size": (w, h),
            "characters": [{"index", "crop_path", "bbox"(原图像素),
                            "bbox_norm"(0-1), "bbox_percent"(0-100),
                            "detector_confidence", "class_name"}, ...],
        }
    调用方负责清理 crop_path 所在的临时目录。
    """
    import tempfile

    from config.base import CROP_MARGIN_RATIO, MAX_CHARACTERS, YOLO_DETECT_MAX_SIZE

    max_characters = MAX_CHARACTERS if max_characters is None else max_characters
    margin_ratio = CROP_MARGIN_RATIO if margin_ratio is None else margin_ratio
    max_size = YOLO_DETECT_MAX_SIZE if max_size is None else max_size

    detector = get_detector()
    found = detector.detect_all(image_path, max_size=max_size, target_classes=["person"])
    detections = found["detections"][:max(1, int(max_characters))]
    if not detections:
        # 人物类别没命中时放宽一次（兼容非人物主体的老用例）
        found = detector.detect_all(image_path, max_size=max_size, target_classes=None)
        detections = found["detections"][:max(1, int(max_characters))]

    tmp_dir = output_dir or tempfile.mkdtemp(prefix="37ac_multi_", dir=str(_tmp_root()))
    crops = detector.crop_all(image_path, detections, tmp_dir, margin_ratio=margin_ratio)
    size = found["image_size"]
    for item in crops:
        item["bbox_norm"] = normalize_bbox(item["bbox"], size)
        item["bbox_percent"] = percent_bbox(item["bbox"], size)
    return {
        "image_size": size,
        "detected_size": found["detected_size"],
        "characters": crops,
        "tmp_dir": tmp_dir,      # 调用方用完请 rmtree 清理
    }


def crop_best_character(image_path: str) -> tuple:
    """检测并裁剪最佳人物区域（快捷入口），结果保存到系统临时目录。
    注意：调用方负责在使用完毕后清理返回的裁剪文件。
    """
    import tempfile
    import shutil
    tmp_dir = tempfile.mkdtemp(prefix="37ac_yolo_", dir=str(_tmp_root()))
    try:
        detector = get_detector()
        crop_path, info = detector.detect_and_crop(
            image_path, target_classes=["person"], output_dir=tmp_dir
        )
        if crop_path:
            return crop_path, info
        # 降级：不限制类别
        crop_path, info = detector.detect_and_crop(image_path, output_dir=tmp_dir)
        if crop_path:
            return crop_path, info
        # 未检测到任何内容，清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None, None
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
