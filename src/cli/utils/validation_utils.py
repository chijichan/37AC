# utils/validation_utils.py
import os
from common.constants import IMAGE_EXTENSIONS_BASIC
from .image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger("validation_utils")


def validate_dataset_images(dataset_dir: str) -> tuple:
    """验证数据集中的图像文件（适配 IP/角色 两级目录结构）

    目录结构：
        dataset/
        ├── 作品A/
        │   ├── 角色1/
        │   │   ├── img1.jpg
        │   │   └── img2.jpg
        │   └── 角色2/
        │       └── img3.jpg
        └── 作品B/
            └── 角色3/
                └── img4.jpg
    """
    valid_samples = 0
    total_samples = 0
    class_names = []
    invalid_image_paths = []

    # 检查数据集目录
    if not os.path.exists(dataset_dir):
        logger.error("数据集目录不存在: %s", dataset_dir)
        return 0, 0, [], []

    # 遍历 IP 目录 → 角色目录 → 图片文件
    ip_names = sorted(
        d for d in os.listdir(dataset_dir)
        if os.path.isdir(os.path.join(dataset_dir, d)) and not d.startswith(".")
    )

    if not ip_names:
        logger.error("数据集中未找到任何作品（IP）目录")
        return 0, 0, [], []

    for ip_name in ip_names:
        ip_path = os.path.join(dataset_dir, ip_name)
        role_names = sorted(
            r for r in os.listdir(ip_path)
            if os.path.isdir(os.path.join(ip_path, r))
        )
        for role_name in role_names:
            role_path = os.path.join(ip_path, role_name)
            class_name = f"{ip_name}/{role_name}"
            class_names.append(class_name)

            # 验证该角色目录下的所有图片文件
            for file in sorted(os.listdir(role_path)):
                if not file.lower().endswith(IMAGE_EXTENSIONS_BASIC):
                    logger.warning("跳过非图片文件: %s/%s", role_path, file)
                    continue
                total_samples += 1
                file_path = os.path.join(role_path, file)
                if validate_image_file(file_path):
                    valid_samples += 1
                else:
                    invalid_image_paths.append(file_path)

    # 输出验证结果
    logger.info("发现 %d 个角色类别，来自 %d 个作品", len(class_names), len(ip_names))
    for cls in class_names:
        logger.info("  - %s", cls)

    if invalid_image_paths:
        logger.error("共发现 %d 个无效图像文件", len(invalid_image_paths))
        for path in invalid_image_paths:
            logger.error("  - %s", path)
    else:
        logger.info("未发现无效图像文件，所有图片均有效")

    return valid_samples, total_samples, class_names, invalid_image_paths


def filter_missing_or_corrupt_images(dataset_dir: str) -> dict:
    """训练前过滤数据集中的缺失/损坏图片，并清理空目录。

    策略（避免每次全量校验拖慢训练）：
      - 所有图片：只做廉价检查（存在 + 非空）
      - 只对“新裁剪（_37ac/_yolo）”或“可疑（空文件）”做完整 PIL 校验
      - 通过数据集根目录的 `.37ac_image_filter_marker` 记录上次过滤时间，
        之后再出现的非裁剪新文件也会被完整校验

    Returns:
        dict: {"removed": int, "missing": int, "corrupt": int, "empty_dirs": int}
    """
    import time

    from tqdm import tqdm

    result = {"removed": 0, "missing": 0, "corrupt": 0, "empty_dirs": 0}

    if not os.path.isdir(dataset_dir):
        logger.error("数据集目录不存在，跳过图片过滤: %s", dataset_dir)
        return result

    marker_path = os.path.join(dataset_dir, ".37ac_image_filter_marker")
    first_run = not os.path.exists(marker_path)
    last_filter = 0.0
    if not first_run:
        try:
            last_filter = float(open(marker_path, "r", encoding="utf-8").read().strip() or 0)
        except Exception:
            last_filter = 0.0

    # 收集所有图片（用于统一 tqdm 进度）
    all_images = []
    ip_names = sorted(
        d for d in os.listdir(dataset_dir)
        if os.path.isdir(os.path.join(dataset_dir, d)) and not d.startswith(".")
    )
    for ip_name in ip_names:
        ip_path = os.path.join(dataset_dir, ip_name)
        role_names = sorted(
            r for r in os.listdir(ip_path)
            if os.path.isdir(os.path.join(ip_path, r))
        )
        for role_name in role_names:
            role_path = os.path.join(ip_path, role_name)
            for fname in os.listdir(role_path):
                if fname.lower().endswith(IMAGE_EXTENSIONS_BASIC):
                    all_images.append(os.path.join(role_path, fname))

    for file_path in tqdm(all_images, desc="训练前图片过滤", unit="张", ncols=100):
        if not os.path.exists(file_path):
            result["missing"] += 1
            continue

        size = os.path.getsize(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        base = os.path.basename(file_path).lower()
        # 新裁剪后缀 _37ac（兼容旧的 _yolo）
        is_yolo = base.endswith("_37ac" + ext) or base.endswith("_yolo" + ext)
        is_new = os.path.getmtime(file_path) > last_filter
        suspicious = size == 0

        if suspicious:
            # 空文件：直接按损坏处理并删除
            result["corrupt"] += 1
            try:
                os.remove(file_path)
                result["removed"] += 1
            except OSError:
                pass
            continue

        # 只对“新出现 / 首次运行的新裁剪 / 可疑”文件做完整校验
        need_full = is_new or (first_run and is_yolo)
        if need_full:
            if not validate_image_file(file_path):
                result["corrupt"] += 1
                try:
                    os.remove(file_path)
                    result["removed"] += 1
                except OSError:
                    pass

    # 清理空角色/IP 目录
    for ip_name in ip_names:
        ip_path = os.path.join(dataset_dir, ip_name)
        for role_name in list(os.listdir(ip_path)):
            role_path = os.path.join(ip_path, role_name)
            if os.path.isdir(role_path) and not os.listdir(role_path):
                try:
                    os.rmdir(role_path)
                    result["empty_dirs"] += 1
                except OSError:
                    pass
        if os.path.isdir(ip_path) and not os.listdir(ip_path):
            try:
                os.rmdir(ip_path)
                result["empty_dirs"] += 1
            except OSError:
                pass

    # 记录本次过滤时间，下次只校验新文件
    try:
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(str(int(time.time())))
    except OSError:
        pass

    if result["removed"] or result["missing"] or result["corrupt"]:
        logger.warning(
            "训练前图片过滤完成：移除 %d 张，缺失 %d 张，损坏 %d 张，清理空目录 %d 个",
            result["removed"], result["missing"], result["corrupt"], result["empty_dirs"],
        )
    else:
        logger.info("训练前图片过滤：未发现缺失或损坏图片")

    return result
