# utils/validation_utils.py
import os
from .image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger(__name__)


def validate_dataset_images(dataset_dir: str) -> tuple:
    """验证数据集中的图像文件"""
    valid_samples = 0
    total_samples = 0
    class_names = []
    invalid_image_paths = []  # 存储无效图像路径
    invalid_classes = []  # 存储包含无效图像的类别

    try:
        # 尝试加载数据集以获取类别信息
        if os.path.exists(dataset_dir):
            from torchvision import datasets

            temp_dataset = datasets.ImageFolder(root=dataset_dir)
            class_names = temp_dataset.classes
            logger.info(f"发现 {len(class_names)} 个角色类别: {class_names}")
        else:
            logger.error(f"数据集目录不存在: {dataset_dir}")
            return 0, 0, [], []

        # 验证数据集中的每个图像文件
        logger.info("正在验证数据集中的图像文件...")
        for root, _, files in os.walk(dataset_dir):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    total_samples += 1
                    file_path = os.path.join(root, file)
                    if validate_image_file(file_path):
                        valid_samples += 1
                    else:
                        invalid_image_paths.append(file_path)
                        # 获取相对路径以确定所属类别
                        rel_path = os.path.relpath(file_path, dataset_dir)
                        class_name = rel_path.split(os.sep)[0]
                        if class_name not in invalid_classes:
                            invalid_classes.append(class_name)

        # 输出验证结果
        if invalid_image_paths:
            logger.error(
                f"共发现 {len(invalid_image_paths)} 个无效图像文件，来自以下 {len(invalid_classes)} 个类别: {invalid_classes}"
            )
            for path in invalid_image_paths:
                logger.error(f"  - {path}")
        else:
            logger.info("未发现无效图像文件，所有图片均有效。")

        return valid_samples, total_samples, class_names, invalid_image_paths

    except Exception as e:
        logger.error(f"验证图像文件时出现错误: {str(e)}", exc_info=True)
        return 0, 0, [], []
