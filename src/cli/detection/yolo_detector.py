"""YOLO 人物检测器 — 快速定位图片中角色区域，裁剪后供 ResNet 分类"""

import os
import shutil
import logging

logger = logging.getLogger("yolo_detector")

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

    def detect(self, image_path: str):
        """检测图片中的人物/主体区域。

        Args:
            image_path: 图片路径

        Returns:
            list[dict]: 检测到的区域列表，每个区域包含:
                {
                    "bbox": (x1, y1, x2, y2),     # 原始图片坐标
                    "confidence": float,            # 置信度
                    "class_id": int,               # YOLO 类别 ID
                    "class_name": str,             # YOLO 类别名称
                }
            若未检测到任何目标或 YOLO 不可用，返回空列表。
        """
        if not self._load_model():
            return []

        try:
            from PIL import Image

            results = self._model(
                image_path,
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

    def detect_and_crop(self, image_path: str, target_classes=None, suffix="_yolo", output_dir=None):
        """检测并裁剪出最佳目标区域。

        Args:
            image_path: 图片路径
            target_classes: 只关注的目标类别列表（如 ["person"]），None 表示全部
            suffix: 裁剪后文件名后缀，默认 "_yolo"
            output_dir: 裁剪结果保存目录（None 表示与原图同目录）

        Returns:
            tuple: (cropped_image_path_or_none, detection_info_or_none)
                - 裁剪后的图片路径（保存为临时文件）
                - 检测信息 dict
            若未检测到目标或 YOLO 不可用，返回 (None, None)
        """
        detections = self.detect(image_path)
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
            from PIL import Image

            img = Image.open(image_path).convert("RGB")
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
def get_detector():
    """获取（缓存）YOLO 检测器实例"""
    global _detector_instance
    if _detector_instance is None:
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
        _detector_instance = YoloDetector(
            model_path=YOLO_MODEL_PATH,
            conf_threshold=YOLO_CONFIDENCE,
            device=yolo_device,
        )
    return _detector_instance


def crop_dataset(source_dir: str, output_dir: str, target_classes=None, max_images_per_role: int = 100):
    """遍历数据集目录，对每张图片执行 YOLO 检测并裁剪人物区域。

    裁剪后的图片保存到 output_dir（不覆盖原图），
    文件名为 `_yolo` 后缀。若 YOLO 未检测到目标，则在数量未超限时直接复制原图。
    每个角色最多保留 max_images_per_role 张图片，优先选择大图和 person 检测结果。

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

    detector = get_detector()
    if not detector._load_model():
        logger.error("YOLO 模型加载失败，无法裁剪数据集")
        return {"processed": 0, "skipped": 0, "failed": 0}

    from config.log_config import get_logger as _get_logger
    _logger = _get_logger("crop_dataset")

    from common.constants import IMAGE_EXTENSIONS_BASIC as image_extensions
    processed = 0
    skipped = 0
    failed = 0

    _logger.info("开始 YOLO 裁剪: %s → %s", source_dir, output_dir)

    for ip_name in sorted(os.listdir(source_dir)):
        ip_path = os.path.join(source_dir, ip_name)
        if not os.path.isdir(ip_path) or ip_name.startswith("."):
            continue

        for role_name in sorted(os.listdir(ip_path)):
            role_path = os.path.join(ip_path, role_name)
            if not os.path.isdir(role_path) or role_name.startswith("."):
                continue

            out_role_dir = os.path.join(output_dir, ip_name, role_name)
            existing_files = []
            if os.path.exists(out_role_dir):
                existing_files = [
                    f for f in os.listdir(out_role_dir)
                    if f.lower().endswith(image_extensions)
                ]

            if len(existing_files) >= max_images_per_role:
                _logger.info(
                    "角色 %s/%s 已有 %d 张图片（>= %d），跳过裁剪。",
                    ip_name, role_name, len(existing_files), max_images_per_role
                )
                skipped += len(existing_files)
                continue

            role_images = []
            for fname in os.listdir(role_path):
                if not fname.lower().endswith(image_extensions):
                    continue

                base_name, ext = os.path.splitext(fname)
                if base_name.endswith("_yolo"):
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
                yolo_fname = f"{base_name}_yolo{ext}"
                yolo_out = os.path.join(out_role_dir, yolo_fname)
                original_out = os.path.join(out_role_dir, fname)

                if os.path.exists(yolo_out) or os.path.exists(original_out):
                    skipped += 1
                    continue

                if not created_role_dir:
                    os.makedirs(out_role_dir, exist_ok=True)
                    created_role_dir = True

                try:
                    crop_path, info = detector.detect_and_crop(
                        src_img, target_classes=target_classes, suffix="_yolo"
                    )
                    if crop_path and os.path.exists(crop_path):
                        dst = yolo_out
                        shutil.move(crop_path, dst)
                        processed += 1
                        saved_count += 1
                        _logger.debug("YOLO 裁剪: %s → %s", src_img, dst)
                    else:
                        if target_classes is None and saved_count < max_images_per_role:
                            dst = original_out
                            shutil.copy2(src_img, dst)
                            processed += 1
                            saved_count += 1
                            _logger.debug("直接复制原图: %s → %s", src_img, dst)
                        else:
                            skipped += 1
                except Exception as e:
                    _logger.error("处理失败 %s: %s", src_img, e)
                    failed += 1

            if os.path.isdir(out_role_dir) and not os.listdir(out_role_dir):
                # 当前角色没有写入任何新文件，删除可能产生的空目录
                try:
                    os.rmdir(out_role_dir)
                except OSError:
                    pass

    _logger.info(
        "数据集裁剪完成: 已处理=%d, 跳过=%d, 失败=%d",
        processed, skipped, failed
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
