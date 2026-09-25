# detection/mediapipe_detector.py
"""MediaPipe 关键点裁剪（需求2 的第二种裁剪方式）。

定位：
- YOLO（COCO person）负责主要的人物检测；MediaPipe 作为**互补/兜底**：
  遮挡、奇怪姿态、半身特写、YOLO 漏检时用它估计人物区域。
- 多人：先跑 FaceDetection（可返回多张脸），每张脸按头身比外扩成「角色区域」；
  没有脸时退回 Pose（只支持单人）按可见关键点取外接框。
- ⚠️ MediaPipe 的模型是在**真人**上训练的，二次元/插画图片命中率有限，
  所以 auto 模式把它排在 YOLO 之后；不可用时静默跳过，不影响主链路。

依赖：mediapipe（可选，见 src/cli/requirements.txt）。未安装时 is_available() 返回 False。
"""

from config.log_config import get_logger
from detection.bbox import bbox_area, clamp_bbox, expand_bbox

logger = get_logger("mediapipe_detector")

_MODULE = None
_IMPORT_FAILED = False


def _load_module():
    """惰性导入 mediapipe；失败只记一次，之后直接返回 None。"""
    global _MODULE, _IMPORT_FAILED
    if _MODULE is not None or _IMPORT_FAILED:
        return _MODULE
    try:
        import mediapipe as mp  # noqa: F401  (可选依赖)
        _MODULE = mp
    except Exception as e:
        _IMPORT_FAILED = True
        logger.debug("mediapipe 不可用（可选依赖未安装）: %s", e)
    return _MODULE


def is_available() -> bool:
    """mediapipe 是否可用（可用于能力上报/自动回退）。"""
    return _load_module() is not None


def face_box_to_character(face_bbox, size, expand_w=2.4, expand_h=3.2, up_shift=0.35):
    """把「一张脸」的框扩成「角色区域」（按常见头身比估算）。

    Args:
        face_bbox: (x1, y1, x2, y2) 像素
        size: 原图 (w, h)
        expand_w / expand_h: 相对脸框宽/高的倍数
        up_shift: 角色区域向上偏移的比例（脸在角色上部，故整体上移）
    """
    x1, y1, x2, y2 = face_bbox
    face_w = max(1, x2 - x1)
    face_h = max(1, y2 - y1)
    center_x = (x1 + x2) / 2.0
    width = face_w * float(expand_w)
    height = face_h * float(expand_h)
    # 脸底往下留 (1-up_shift) 的比例，其余往上扩（头顶+上半身）
    top = y2 - height * (1.0 - float(up_shift))
    return clamp_bbox((center_x - width / 2.0, top, center_x + width / 2.0, top + height), size)


def landmarks_to_bbox(landmarks, size, visibility_threshold=0.5):
    """可见关键点的外接框；没有可用关键点时返回 None。"""
    xs, ys = [], []
    for point in landmarks:
        visibility = getattr(point, "visibility", None)
        if visibility is not None and visibility < visibility_threshold:
            continue
        xs.append(point.x)
        ys.append(point.y)
    if not xs:
        return None
    width, height = size
    return clamp_bbox((min(xs) * width, min(ys) * height, max(xs) * width, max(ys) * height), size)


def detect_persons(image_path, margin_ratio: float = 0.0, min_confidence: float = None,
                   expand_w: float = None, expand_h: float = None,
                   pose_complexity: int = None, face_model_selection: int = None):
    """用 MediaPipe 估计人物区域。

    Returns:
        dict: 与 yolo_detector.detect_all 同构：
            {"image_size", "detected_size", "detections": [{"bbox", "area", "confidence",
              "class_id", "class_name"}]}
        mediapipe 不可用/未检出时 detections 为空。
    """
    from config.base import (
        MEDIAPIPE_FACE_EXPAND_H,
        MEDIAPIPE_FACE_EXPAND_W,
        MEDIAPIPE_FACE_MODEL_SELECTION,
        MEDIAPIPE_MIN_CONFIDENCE,
        MEDIAPIPE_POSE_COMPLEXITY,
    )

    empty = {"image_size": (0, 0), "detected_size": (0, 0), "detections": []}
    mp = _load_module()
    if mp is None:
        return empty

    try:
        import numpy as np
        from PIL import Image

        with Image.open(image_path) as raw:
            image = raw.convert("RGB")
            size = image.size
            pixels = np.asarray(image)
    except Exception as e:
        logger.error("MediaPipe 检测读取图片失败: %s", e)
        return empty

    min_confidence = MEDIAPIPE_MIN_CONFIDENCE if min_confidence is None else min_confidence
    expand_w = MEDIAPIPE_FACE_EXPAND_W if expand_w is None else expand_w
    expand_h = MEDIAPIPE_FACE_EXPAND_H if expand_h is None else expand_h
    # 默认用最省的模型：姿态 lite（内存/耗时最低）、人脸全景模型（整图召回优先）
    pose_complexity = MEDIAPIPE_POSE_COMPLEXITY if pose_complexity is None else pose_complexity
    face_model_selection = (
        MEDIAPIPE_FACE_MODEL_SELECTION if face_model_selection is None else face_model_selection
    )

    detections = []

    # 1) 人脸（支持多人）
    try:
        with mp.solutions.face_detection.FaceDetection(
            model_selection=int(face_model_selection), min_detection_confidence=min_confidence
        ) as face_detector:
            face_result = face_detector.process(pixels)

        for det in (face_result.detections or []):
            box = det.location_data.relative_bounding_box
            face_bbox = clamp_bbox((
                box.xmin * size[0],
                box.ymin * size[1],
                (box.xmin + box.width) * size[0],
                (box.ymin + box.height) * size[1],
            ), size)
            character_box = face_box_to_character(face_bbox, size, expand_w, expand_h)
            character_box = expand_bbox(character_box, size, margin_ratio)
            score = None
            try:
                score = round(float(det.score[0]), 3)
            except Exception:
                score = None
            detections.append({
                "bbox": character_box,
                "area": bbox_area(character_box),
                "confidence": score,
                "class_id": -1,
                "class_name": "mediapipe_face",
                "face_bbox": face_bbox,
            })
    except Exception as e:
        logger.debug("MediaPipe 人脸检测失败: %s", e)

    # 2) 姿态兜底（单人）
    if not detections:
        try:
            with mp.solutions.pose.Pose(
                static_image_mode=True, model_complexity=int(pose_complexity)
            ) as pose:
                pose_result = pose.process(pixels)
            if getattr(pose_result, "pose_landmarks", None):
                body_box = landmarks_to_bbox(pose_result.pose_landmarks.landmark, size)
                if body_box:
                    body_box = expand_bbox(body_box, size, max(margin_ratio, 0.05))
                    detections.append({
                        "bbox": body_box,
                        "area": bbox_area(body_box),
                        "confidence": None,
                        "class_id": -1,
                        "class_name": "mediapipe_pose",
                    })
        except Exception as e:
            logger.debug("MediaPipe 姿态检测失败: %s", e)

    detections.sort(key=lambda item: item["area"], reverse=True)
    logger.info("MediaPipe 估计人物区域: %d 个", len(detections))
    return {"image_size": size, "detected_size": size, "detections": detections}
