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

from config.base import (
    CROP_MARGIN_RATIO,
    CROP_MAX_AREA_RATIO,
    CROP_METHOD,
    CROP_MIN_AREA_RATIO,
    CROP_MIN_CONFIDENCE,
    CROP_MAX_ASPECT_RATIO,
    CROP_MIN_ASPECT_RATIO,
    CROP_QUALITY_GATE,
    DATASET_CROP_MAX_AREA_RATIO,
    DATASET_CROP_MAX_ASPECT_RATIO,
    DATASET_CROP_MIN_AREA_RATIO,
    DATASET_CROP_MIN_ASPECT_RATIO,
    DATASET_CROP_MIN_CONFIDENCE,
    DATASET_CROP_QUALITY_GATE,
    MAX_CHARACTERS,
    YOLO_DETECT_MAX_SIZE,
)
from config.log_config import get_logger
from detection.bbox import normalize_bbox, percent_bbox

logger = get_logger("cropper")


def available_methods() -> list:
    """当前环境下可用的裁剪方式（供能力上报/文档/前端展示）。

    MEDIAPIPE_ENABLED=false 时直接返回 ["yolo"]，**不会 import mediapipe**
    （省 10~67MB 常驻内存）。
    """
    methods = ["yolo"]
    try:
        from config.base import MEDIAPIPE_ENABLED
        if not MEDIAPIPE_ENABLED:
            return methods
        from detection import mediapipe_detector
        if mediapipe_detector.is_available():
            methods.append("mediapipe")
    except Exception:
        pass
    return methods


def gate_thresholds(dataset: bool = False) -> dict:
    """取一套门控阈值：dataset=True 用数据集裁剪专用参数（DATASET_CROP_*），否则用识别参数。"""
    if dataset:
        return {
            "enabled": DATASET_CROP_QUALITY_GATE,
            "min_confidence": DATASET_CROP_MIN_CONFIDENCE,
            "min_area": DATASET_CROP_MIN_AREA_RATIO,
            "max_area": DATASET_CROP_MAX_AREA_RATIO,
            "min_aspect": DATASET_CROP_MIN_ASPECT_RATIO,
            "max_aspect": DATASET_CROP_MAX_ASPECT_RATIO,
        }
    return {
        "enabled": CROP_QUALITY_GATE,
        "min_confidence": CROP_MIN_CONFIDENCE,
        "min_area": CROP_MIN_AREA_RATIO,
        "max_area": CROP_MAX_AREA_RATIO,
        "min_aspect": CROP_MIN_ASPECT_RATIO,
        "max_aspect": CROP_MAX_ASPECT_RATIO,
    }


def gate_detections(items, image_size, dataset: bool = False):
    """裁剪质量门控：按检测置信度、框面积占比、长宽比过滤候选框。

    check_max_area=False 用于**数据集裁剪**：源图本身常常就是紧裁剪的立绘，
    "框几乎占满整张图"完全正常（识别路径才把它当可疑信号）。

    实测背景（91 类原始网图抽样）：直接裁剪 71.3% vs 不裁剪 79.0%，
    因为 COCO 模型在二次元图上会误检/多检，裁出的框常常不是角色主体。
    返回通过门控的候选；CROP_QUALITY_GATE=false 时原样返回（旧行为）。
    """
    items = list(items or [])
    th = gate_thresholds(dataset)
    if not th["enabled"] or not items:
        return items

    width, height = image_size or (0, 0)
    total_area = float(width) * float(height) if width and height else 0.0
    passed = []
    for item in items:
        confidence = item.get("detector_confidence")
        if confidence is not None and th["min_confidence"] > 0 and float(confidence) < th["min_confidence"]:
            continue

        box = item.get("bbox_norm") or {}
        ratio = float(box.get("w") or 0) * float(box.get("h") or 0)
        if not ratio and total_area:
            raw = item.get("bbox") or ()
            if len(raw) == 4:
                ratio = max(0.0, (raw[2] - raw[0]) * (raw[3] - raw[1]) / total_area)
        if th["min_area"] > 0 and ratio and ratio < th["min_area"]:
            continue
        if th["max_area"] > 0 and ratio > th["max_area"]:
            continue

        aspect = _box_aspect_ratio(item)
        if aspect:
            if th["min_aspect"] > 0 and aspect < th["min_aspect"]:
                continue
            if th["max_aspect"] > 0 and aspect > th["max_aspect"]:
                continue
        passed.append(item)
    return passed


def _box_aspect_ratio(item):
    """框的长宽比 w/h（优先用归一化框，缺失则用像素框）；拿不到返回 0。"""
    box = item.get("bbox_norm") or {}
    width, height = float(box.get("w") or 0), float(box.get("h") or 0)
    if not (width and height):
        raw = item.get("bbox") or ()
        if len(raw) == 4:
            width = max(0.0, float(raw[2]) - float(raw[0]))
            height = max(0.0, float(raw[3]) - float(raw[1]))
    if not (width and height):
        return 0.0
    return width / float(height)


def crop_quality_ok(crop_path, image_path, confidence=None):
    """单框路径的质量门控：裁图面积占原图比例 + 检测置信度都要达标。"""
    if not CROP_QUALITY_GATE:
        return True
    if confidence is not None and CROP_MIN_CONFIDENCE > 0 and float(confidence) < CROP_MIN_CONFIDENCE:
        return False
    if CROP_MIN_AREA_RATIO <= 0 and CROP_MAX_AREA_RATIO <= 0 \
            and CROP_MIN_ASPECT_RATIO <= 0 and CROP_MAX_ASPECT_RATIO <= 0:
        return True
    # 长宽比过滤：直接看裁图本身的比例（它就是框本身，可能带外扩）
    if CROP_MIN_ASPECT_RATIO > 0 or CROP_MAX_ASPECT_RATIO > 0:
        try:
            from PIL import Image as _Image
            with _Image.open(crop_path) as _crop:
                crop_w, crop_h = _crop.size
            if crop_h:
                crop_aspect = crop_w / float(crop_h)
                if CROP_MIN_ASPECT_RATIO > 0 and crop_aspect < CROP_MIN_ASPECT_RATIO:
                    return False
                if CROP_MAX_ASPECT_RATIO > 0 and crop_aspect > CROP_MAX_ASPECT_RATIO:
                    return False
        except Exception:
            pass
    try:
        from PIL import Image
        with Image.open(crop_path) as crop:
            crop_area = crop.size[0] * crop.size[1]
        with Image.open(image_path) as original:
            orig_area = original.size[0] * original.size[1]
    except Exception:
        return True                     # 读不到尺寸时不拦（宁可裁剪也不要整图）
    if orig_area <= 0:
        return True
    ratio = crop_area / float(orig_area)
    if CROP_MIN_AREA_RATIO > 0 and ratio < CROP_MIN_AREA_RATIO:
        return False
    if CROP_MAX_AREA_RATIO > 0 and ratio > CROP_MAX_AREA_RATIO:
        return False
    return True


def _image_size(image_path):
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return (0, 0)


def _mediapipe_characters(image_path, tmp_dir, max_characters, margin_ratio):
    """MediaPipe 候选框 -> 裁剪文件 + 归一化坐标。"""
    from config.base import MEDIAPIPE_ENABLED

    if not MEDIAPIPE_ENABLED:
        # 关掉后不 import mediapipe（省内存），直接返回空让调用方回退整图
        return {"image_size": _image_size(image_path), "detected_size": None, "characters": []}

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
    tmp_dir = output_dir or tempfile.mkdtemp(prefix="37ac_crop_", dir=str(_tmp_root()))

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
            gated = gate_detections(characters, size)
            if len(gated) != len(characters):
                logger.info(
                    "裁剪门控过滤: %d -> %d 个候选（置信度<%.2f 或面积占比<%.2f）",
                    len(characters), len(gated), CROP_MIN_CONFIDENCE, CROP_MIN_AREA_RATIO,
            # 长宽比阈值也一并打印，便于核对门控行为
                )
            characters = gated
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
