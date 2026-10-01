# utils/image_utils.py
import os
import warnings
from PIL import Image
from config.log_config import get_logger

logger = get_logger("image_utils")

# 数据集压缩支持的图片扩展名
_COMPRESS_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

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
                        "图片尺寸异常（宽或高 <= 0） %s: %sx%s",
                        file_path, width, height,
                    )
                    return False

                # 尝试转为 RGB
                try:
                    rgb_img = img.convert("RGB")
                except Exception as e:
                    logger.warning(
                        "图片色彩模式异常，无法转为 RGB %s: %s",
                        file_path, e,
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
                    logger.warning("图片因 EXIF 异常视为无效: %s", file_path)
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
        logger.warning("图片文件验证失败（数据/格式错误） %s: %s", file_path, e)
        return False
    except Exception as e:
        logger.warning("图片文件发生未知错误 %s: %s", file_path, e)
        return False


def encode_image_bytes(image, max_size: int = 512, quality: int = 90, fmt: str = "JPEG"):
    """把内存里的 PIL.Image 缩放（最长边 <= max_size，0=不缩放）并编码为字节。

    与 compress_image_file 的区别：**不落盘、不读盘**，直接给内存中的图用，
    适合"裁剪 → 压缩 → 直接写目标文件"的直连流程（省一次临时文件中转）。

    Returns:
        (data, ext)：编码后的字节与建议后缀（如 (b"...", ".jpg")）；失败返回 (None, "")
    """
    import io

    try:
        img = image if image.mode == "RGB" else image.convert("RGB")
        if max_size and max_size > 0:
            width, height = img.size
            if max(width, height) > max_size:
                ratio = max_size / float(max(width, height))
                resized = img.resize(
                    (max(1, int(width * ratio)), max(1, int(height * ratio))), Image.LANCZOS
                )
                if resized is not img:
                    img = resized
        buf = io.BytesIO()
        suffix = ".jpg" if fmt.upper() in ("JPEG", "JPG") else "." + fmt.lower()
        save_kwargs = {"quality": int(quality), "optimize": True} if suffix == ".jpg" else {}
        img.save(buf, format=fmt.upper(), **save_kwargs)
        return buf.getvalue(), suffix
    except Exception as e:
        logger.debug("图片内存编码失败: %s", e)
        return None, ""


def compress_image_file(file_path: str, max_size: int = 512, quality: int = 90) -> bool:
    """把图片最长边压到 max_size 以内（保持宽高比）。

    Returns:
        bool: True=实际压缩并保存；False=无需压缩或失败
    """
    if max_size <= 0:
        return False
    try:
        with Image.open(file_path) as img:
            img.load()
            fmt = (img.format or "").upper()
            width, height = img.size
            if max(width, height) <= max_size:
                return False
            ratio = max_size / float(max(width, height))
            new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
            resized = img.resize(new_size, Image.LANCZOS)

        save_kwargs = {}
        if fmt in ("JPEG", "JPG", "MPO"):
            if resized.mode not in ("RGB", "L"):
                resized = resized.convert("RGB")
            save_kwargs = {"quality": quality, "optimize": True}
            fmt = "JPEG"
        elif fmt == "PNG":
            save_kwargs = {"optimize": True}
        elif fmt == "WEBP":
            save_kwargs = {"quality": quality}
        else:
            return False

        tmp_path = f"{file_path}.37ac_tmp"
        resized.save(tmp_path, format=fmt, **save_kwargs)
        resized.close()
        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        logger.debug("压缩图片失败 %s: %s", file_path, e)
        return False


def compress_dataset_images(dataset_dir: str, max_size: int = 512,
                            quality: int = 90, workers: int = 4) -> dict:
    """并发压缩数据集图片（最长边 <= max_size），带 tqdm 进度条。

    Returns:
        dict: {"total", "compressed", "skipped", "failed"}
    """
    result = {"total": 0, "compressed": 0, "skipped": 0, "failed": 0}
    if max_size <= 0:
        logger.info("数据集压缩已禁用（DATASET_COMPRESS_SIZE=0）")
        return result
    if not os.path.isdir(dataset_dir):
        logger.error("数据集目录不存在，无法压缩: %s", dataset_dir)
        return result

    targets = []
    for root, dirs, files in os.walk(dataset_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.lower().endswith(_COMPRESS_EXTENSIONS):
                targets.append(os.path.join(root, name))

    result["total"] = len(targets)
    if not targets:
        logger.warning("数据集中没有可压缩的图片: %s", dataset_dir)
        return result

    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    max_workers = max(1, int(workers or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(compress_image_file, path, max_size, quality): path
            for path in targets
        }
        for future in tqdm(
            as_completed(futures), total=len(futures),
            desc=f"压缩数据集(最长边{max_size})", unit="张", ncols=100,
        ):
            try:
                if future.result():
                    result["compressed"] += 1
                else:
                    result["skipped"] += 1
            except Exception:
                result["failed"] += 1

    logger.info(
        "数据集压缩完成: 总计 %d, 已压缩 %d, 跳过 %d, 失败 %d",
        result["total"], result["compressed"], result["skipped"], result["failed"],
    )
    return result
