# detection/bbox.py
"""检测框坐标工具：外扩、跨坐标系映射、归一化与百分比。

坐标约定：bbox = (x1, y1, x2, y2) 像素，左上 / 右下。

⚠️ 关键坑：YOLO 检测前的预处理可能把图片缩放（见 yolo_detector.detect_and_crop 的 max_size），
此时检测框属于**缩放后**坐标系；而对外返回的百分比坐标必须以**原图**尺寸为分母。
本模块的 scale_bbox / normalize_bbox 就是为这两个坐标系服务的。
"""


def clamp_bbox(bbox, size):
    """把框夹到图片范围内，并保证 x2>x1、y2>y1。"""
    width, height = size
    x1, y1, x2, y2 = [int(round(float(v))) for v in bbox]
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    return (x1, y1, x2, y2)


def expand_bbox(bbox, size, ratio=0.0):
    """按框宽高的比例向四周外扩（0.08 = 各方向扩 8%），再夹回图片内。"""
    if not ratio:
        return clamp_bbox(bbox, size)
    x1, y1, x2, y2 = bbox
    dx = (x2 - x1) * float(ratio)
    dy = (y2 - y1) * float(ratio)
    return clamp_bbox((x1 - dx, y1 - dy, x2 + dx, y2 + dy), size)


def scale_bbox(bbox, from_size, to_size):
    """把 from_size 坐标系里的框映射到 to_size 坐标系。"""
    fw, fh = from_size
    tw, th = to_size
    if not fw or not fh:
        return clamp_bbox(bbox, to_size)
    sx, sy = tw / float(fw), th / float(fh)
    x1, y1, x2, y2 = bbox
    return clamp_bbox((x1 * sx, y1 * sy, x2 * sx, y2 * sy), to_size)


def normalize_bbox(bbox, size):
    """转 0-1 归一化坐标（4 位小数）：{x, y, w, h}。"""
    width, height = size
    x1, y1, x2, y2 = bbox
    return {
        "x": round(x1 / float(width), 4),
        "y": round(y1 / float(height), 4),
        "w": round((x2 - x1) / float(width), 4),
        "h": round((y2 - y1) / float(height), 4),
    }


def percent_bbox(bbox, size):
    """转 0-100 百分比坐标（2 位小数）：{x, y, w, h}。"""
    width, height = size
    x1, y1, x2, y2 = bbox
    return {
        "x": round(x1 / float(width) * 100, 2),
        "y": round(y1 / float(height) * 100, 2),
        "w": round((x2 - x1) / float(width) * 100, 2),
        "h": round((y2 - y1) / float(height) * 100, 2),
    }


def bbox_area(bbox):
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def bbox_iou(a, b):
    """两个框的 IoU（多目标去重可用）。"""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = bbox_area(a) + bbox_area(b) - inter
    return (inter / union) if union else 0.0
