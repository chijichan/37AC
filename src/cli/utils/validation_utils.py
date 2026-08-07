# utils/validation_utils.py
import os
from common.constants import IMAGE_EXTENSIONS_BASIC
from .image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger(__name__)


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
        logger.error(f"数据集目录不存在: {dataset_dir}")
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
                    logger.warning(f"跳过非图片文件: {role_path}/{file}")
                    continue
                total_samples += 1
                file_path = os.path.join(role_path, file)
                if validate_image_file(file_path):
                    valid_samples += 1
                else:
                    invalid_image_paths.append(file_path)

    # 输出验证结果
    logger.info(f"发现 {len(class_names)} 个角色类别，来自 {len(ip_names)} 个作品")
    for cls in class_names:
        logger.info(f"  - {cls}")

    if invalid_image_paths:
        logger.error(f"共发现 {len(invalid_image_paths)} 个无效图像文件")
        for path in invalid_image_paths:
            logger.error(f"  - {path}")
    else:
        logger.info("未发现无效图像文件，所有图片均有效")

    return valid_samples, total_samples, class_names, invalid_image_paths
