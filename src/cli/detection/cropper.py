# detection/cropper.py
"""裁剪方式统一入口（需求2）：yolo / mediapipe / auto。

auto 的回退链：
    1) YOLO 检测到人物       -> crop_method = "yolo"
    2) MediaPipe 估计到区域  -> crop_method = "mediapipe"（未安装则自动跳过）
    3) 都没有                -> characters = [], crop_method = "full"（调用方回落整图识别）

统一返回结构：
    {
      "image_size": (w, h),            # 原图尺寸，百分比坐标的分母
      "detected_size": (w, h) | None,  # 实际送入检测器的尺寸
      "crop_method": "yolo|mediapipe|full",
      "characters": [{"index", "crop_path", "bbox", "bbox_norm", "bbox_percent",
                      "detector_confidence", "class_name"}],
      "tmp_dir": "<裁剪临时目录，调用方负责 rmtree 清理>",
    }
"""

import tempfile

from config.base import CROP_MARGIN_RATIO, CROP_METHOD, MAX_CHARACTERS, YOLO_DETECT_MAX_SIZE
from config.log_config import get_logger
from detection.bbox import normalize_bbox, percent_bbox

logger = get_logger("cropper")


def available_methods() -> list:
    """当前环境下可用的裁剪方式（供能力上报/文档/前端展示）。"""
    methods = ["yolo"]
    try:
        from detection import mediapipe_detector
        if mediapipe_detector.is_available():
            methods.append("mediapipe")
    except Exception:
        pass
    return methods


def _image_size(image_path):
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return (0, 0)


def _mediapipe_characters(image_path, tmp_dir, max_characters, margin_ratio):
    """MediaPipe 候选框 -> 裁剪文件 + 归一化坐标。"""
    from detection import mediapipe_detector
    from detection.yolo_detector import YoloDetector

    found = mediapipe_detector.detect_persons(image_path, margin_ratio=margin_ratio)
    detections = found.get("detections") or []
    size = found.get("image_size") or _image_size(image_path)
    if not detections:
        return {"image_size": size, "detected_size": found.get("detected_size"), "characters": []}

    # 人脸框在 mediapipe_detector 里已经外扩过，这里不再叠加 margin
    detector = YoloDetector()          # 仅用其 crop_all（纯 PIL，不会加载 YOLO 权重）
    crops = detector.crop_all(
        image_path, detections[:max(1, int(max_characters))], tmp_dir, margin_ratio=0.0,
    )
    for item in crops:
        item["bbox_norm"] = normalize_bbox(item["bbox"], size)
        item["bbox_percent"] = percent_bbox(item["bbox"], size)
    return {"image_size": size, "detected_size": found.get("detected_size"), "characters": crops}


def _finalize(items, image_size):
    for item in items:
        item["bbox_norm"] = normalize_bbox(item["bbox"], image_size)
        item["bbox_percent"] = percent_bbox(item["bbox"], image_size)
    return items


def crop_characters_by_method(image_path, method=None, max_characters=None, margin_ratio=None,
                              max_size=None, output_dir=None):
    """按指定/配置的裁剪方式检测并裁剪人物（需求1+2 的节点侧统一入口）。"""
    from detection.yolo_detector import crop_characters as yolo_crop_characters

    method = (method or CROP_METHOD or "auto").strip().lower()
    max_characters = MAX_CHARACTERS if max_characters is None else max_characters
    margin_ratio = CROP_MARGIN_RATIO if margin_ratio is None else margin_ratio
    max_size = YOLO_DETECT_MAX_SIZE if max_size is None else max_size

    chain = {
        "auto": ["yolo", "mediapipe"],
        "yolo": ["yolo"],
        "mediapipe": ["mediapipe"],
    }.get(method, ["yolo"])
    image_size = _image_size(image_path)
    tmp_dir = output_dir or tempfile.mkdtemp(prefix="37ac_crop_")

    for name in chain:
        try:
            if name == "yolo":
                found = yolo_crop_characters(
                    image_path, max_characters=max_characters, max_size=max_size,
                    margin_ratio=margin_ratio, output_dir=tmp_dir,
                )
            else:
                found = _mediapipe_characters(image_path, tmp_dir, max_characters, margin_ratio)
        except Exception as e:
            logger.warning("%s 裁剪失败，尝试下一种方式: %s", name, e)
            continue

        characters = found.get("characters") or []
        if characters:
            size = found.get("image_size") or image_size
            logger.info("裁剪方式=%s，检出人物=%d", name, len(characters))
            return {
                "image_size": size,
                "detected_size": found.get("detected_size"),
                "characters": characters,
                "crop_method": name,
                "tmp_dir": tmp_dir,
            }
        logger.debug("%s 未检出人物", name)

    return {
        "image_size": image_size,
        "detected_size": None,
        "characters": [],
        "crop_method": "full",
        "tmp_dir": tmp_dir,
    }
