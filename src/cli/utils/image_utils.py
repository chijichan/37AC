# utils/image_utils.py
import warnings
from PIL import Image
from config.log_config import get_logger

logger = get_logger(__name__)

def validate_image_file(file_path: str) -> bool:
    """
    终极版图片验证：可检测以下问题：
    - 图片文件是否损坏（基础验证）
    - 图片尺寸是否合法
    - 是否能转为 RGB
    - 是否存在 EXIF 数据异常（如 Corrupt EXIF data...）
    """
    try:
        # 新增：用 warnings 捕获该图片打开过程中产生的所有 UserWarning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # 确保所有警告都被捕获

            # 1. 打开图片（可能触发 EXIF 相关的 Warning）
            with Image.open(file_path) as img:
                img.verify()  # 基础验证：检测是否为有效图片数据

            # 2. 重新打开，进一步检测
            with Image.open(file_path) as img:
                # 检查尺寸
                width, height = img.size
                if width <= 0 or height <= 0:
                    logger.warning(
                        f"图片尺寸异常（宽或高 <= 0） {file_path}: {width}x{height}"
                    )
                    return False

                # 尝试转为 RGB
                try:
                    rgb_img = img.convert("RGB")
                except Exception as e:
                    logger.warning(
                        f"图片色彩模式异常，无法转为 RGB {file_path}: {str(e)}"
                    )
                    return False

                # 检查是否在打开过程中捕获到了 EXIF 相关的 Warning
                exif_warning_detected = any(
                    "Corrupt EXIF data" in str(warn.message)
                    or "Expecting to read 4 bytes but only got 0" in str(warn.message)
                    for warn in w
                    if warn.category == UserWarning
                )

                if exif_warning_detected:
                    logger.warning(f"图片因 EXIF 异常视为无效: {file_path}")
                    return False

                # 如果没有 EXIF 警告，认为图片有效
                return True

    except (
        IOError,
        OSError,
        Image.DecompressionBombError,
        Image.UnidentifiedImageError,
        ValueError,
        IndexError,
    ) as e:
        logger.warning(f"图片文件验证失败（数据/格式错误） {file_path}: {str(e)}")
        return False
    except Exception as e:
        logger.warning(f"图片文件发生未知错误 {file_path}: {str(e)}")
        return False
