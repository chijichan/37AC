"""YOLO 人物检测器 — 快速定位图片中角色区域，裁剪后供 ResNet 分类"""

import os
import shutil
import threading

from config.log_config import get_logger

logger = get_logger("yolo_detector")

# 裁剪产物后缀（新标识；兼容旧的 "_yolo" 输入跳过判断）
CROP_SUFFIX = "_37ac"
LEGACY_CROP_SUFFIXES = ("_37ac", "_yolo")

# 全局缓存
_detector_instance = None


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

    def _load_model(self):
        """加载 YOLO 模型（首次使用时延迟加载）"""
        if self._loaded:
            return True

        try:
            from ultralytics import YOLO

            model_path = self.model_path or "yolov8n.pt"

            # 如果指定路径存在，直接加载；否则交给 Ultralytics 自动下载
            if os.path.exists(model_path):
                logger.info("加载 YOLO 模型: %s", model_path)
            else:
                logger.info("YOLO 模型文件不存在: %s（将使用 Ultralytics 自动下载）", model_path)

            self._model = YOLO(model_path)
            self._loaded = True
            logger.info("YOLO 模型加载成功")
            return True

        except ImportError:
            logger.warning("ultralytics 未安装，YOLO 检测不可用 (pip install ultralytics)")
            return False
        except Exception as e:
            logger.error("YOLO 模型加载失败: %s", e)
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
            logger.error("YOLO 检测失败: %s", e)
            return []

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


# 模块级便捷函数
def _new_detector() -> YoloDetector:
    """创建一个新的 YOLO 检测器（供线程独立使用）。"""
    from config.base import YOLO_MODEL_PATH, YOLO_CONFIDENCE, USE_DIRECTML, get_device
    device = get_device()
    # YOLO 设备传递规则：
    # - DirectML 模式：传 DirectML 设备（torch_directml device）
    # - CUDA 可用：传 "cuda" 或 None（让 YOLO 自动选择）
    # - 否则：传 None（YOLO 自动使用 CPU）
    if USE_DIRECTML:
        yolo_device = device  # DirectML device
    elif str(device) != "cpu":
        yolo_device = device  # CUDA device
    else:
        yolo_device = None    # 让 YOLO 自动选择（CPU）
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


def crop_dataset(source_dir: str, output_dir: str, target_classes=None, max_images_per_role: int = 100):
    """遍历数据集目录，对每张图片执行 YOLO 检测并裁剪人物区域。

    裁剪后的图片保存到 output_dir（不覆盖原图），
    文件名为 `_37ac` 后缀。若 YOLO 未检测到目标，则在数量未超限时直接复制原图。
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

    try:
        import ultralytics  # noqa: F401
    except ImportError:
        logger.warning("ultralytics 未安装，无法裁剪数据集")
        return {"processed": 0, "skipped": 0, "failed": 0}

    from config.log_config import get_logger as _get_logger
    _logger = _get_logger("crop_dataset")

    from common.constants import IMAGE_EXTENSIONS_BASIC as image_extensions
    from config.base import YOLO_CROP_WORKERS, DATASET_COMPRESS_SIZE
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

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

    def process_role(ip_name, role_name, role_path):
        """处理单个角色（在线程内执行，使用线程本地 detector）。"""
        local = {"processed": 0, "skipped": 0, "failed": 0}
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
        for src_img, fname, file_size in role_images:
            if saved_count >= max_images_per_role:
                break

            base_name, ext = os.path.splitext(fname)
            yolo_fname = f"{base_name}{CROP_SUFFIX}{ext}"
            yolo_out = os.path.join(out_role_dir, yolo_fname)
            original_out = os.path.join(out_role_dir, fname)

            if os.path.exists(yolo_out) or os.path.exists(original_out):
                local["skipped"] += 1
                continue

            if not created_role_dir:
                os.makedirs(out_role_dir, exist_ok=True)
                created_role_dir = True

            try:
                crop_path, info = detector.detect_and_crop(
                    src_img, target_classes=target_classes, suffix=CROP_SUFFIX,
                    max_size=DATASET_COMPRESS_SIZE,
                )
                if crop_path and os.path.exists(crop_path):
                    shutil.move(crop_path, yolo_out)
                    local["processed"] += 1
                    saved_count += 1
                    _logger.debug("YOLO 裁剪: %s → %s", src_img, yolo_out)
                else:
                    if target_classes is None and saved_count < max_images_per_role:
                        # 未检测到目标时也先压缩再保存
                        from utils.image_utils import compress_image_file
                        shutil.copy2(src_img, original_out)
                        compress_image_file(original_out, max_size=DATASET_COMPRESS_SIZE)
                        local["processed"] += 1
                        saved_count += 1
                        _logger.debug("直接复制原图: %s → %s", src_img, original_out)
                    else:
                        local["skipped"] += 1
            except Exception as e:
                _logger.error("处理失败 %s: %s", src_img, e)
                local["failed"] += 1

        if os.path.isdir(out_role_dir) and not os.listdir(out_role_dir):
            # 当前角色没有写入任何新文件，删除可能产生的空目录
            try:
                os.rmdir(out_role_dir)
            except OSError:
                pass
        return local

    workers = max(1, int(YOLO_CROP_WORKERS or 1))
    _logger.info("YOLO 裁剪并发线程数: %d（共 %d 个角色）", workers, len(role_tasks))

    counters = {"processed": 0, "skipped": 0, "failed": 0}
    counters_lock = threading.Lock()

    if role_tasks:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(process_role, ip_name, role_name, role_path)
                for ip_name, role_name, role_path in role_tasks
            ]
            for future in tqdm(
                as_completed(futures), total=len(futures),
                desc=f"YOLO裁剪({workers}线程)", unit="角色", ncols=100,
            ):
                try:
                    r = future.result()
                except Exception as e:
                    _logger.error("角色处理异常: %s", e)
                    r = {"processed": 0, "skipped": 0, "failed": 1}
                with counters_lock:
                    for key in counters:
                        counters[key] += r.get(key, 0)

    processed = counters["processed"]
    skipped = counters["skipped"]
    failed = counters["failed"]
    _logger.info(
        "数据集裁剪完成: 已处理=%d, 跳过=%d, 失败=%d（输出已按最长边 %d 压缩）",
        processed, skipped, failed, DATASET_COMPRESS_SIZE,
    )
    return {"processed": processed, "skipped": skipped, "failed": failed}


def detect_characters(image_path: str) -> list:
    """检测图片中的人物区域（快捷入口）"""
    return get_detector().detect(image_path)


def crop_best_character(image_path: str) -> tuple:
    """检测并裁剪最佳人物区域（快捷入口），结果保存到系统临时目录。
    注意：调用方负责在使用完毕后清理返回的裁剪文件。
    """
    import tempfile
    import shutil
    tmp_dir = tempfile.mkdtemp(prefix="37ac_yolo_")
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
