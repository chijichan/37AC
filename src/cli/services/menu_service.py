# services/menu_service.py
import os
import sys
import argparse
from utils.validation_utils import validate_dataset_images
from utils.image_utils import validate_image_file
import logging

logger = logging.getLogger(__name__)


def verify_images_function():
    """单独的图像文件验证功能"""
    from config import DATASET_DIR

    # 检查数据集目录
    if not os.path.exists(DATASET_DIR):
        logger.error(f"数据集目录不存在: {DATASET_DIR}")
        logger.error(
            "请先创建数据集目录，并为每个角色创建一个子文件夹，子文件夹内放入对应角色的图片。"
        )
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error(f"数据集目录不可读: {DATASET_DIR}")
        return

    # 验证数据集中的图像文件
    valid_samples, total_samples, class_names, invalid_image_paths = (
        validate_dataset_images(DATASET_DIR)
    )

    if total_samples == 0:
        logger.error("数据集中没有找到任何图片文件 (jpg, jpeg, png)")
        return

    logger.info(f"数据集总计: {total_samples} 个图像文件")
    logger.info(f"有效图像: {valid_samples} 个")
    logger.info(f"无效图像: {total_samples - valid_samples} 个")

    if valid_samples == 0:
        logger.error("没有有效的图像文件")
        return

    valid_ratio = (valid_samples / total_samples) * 100
    logger.info(f"有效图像比例: {valid_ratio:.2f}%")

    if invalid_image_paths:
        logger.info(
            "\n建议: 请检查并修复或删除上述无效图像文件，然后重新尝试训练或预测。"
        )


def show_menu():
    """显示主菜单"""
    print("\n" + "=" * 80)
    print(
        """                                                                            
                                                                            
 333333333333333   77777777777777777777   AAA                  CCCCCCCCCCCCC
3:::::::::::::::33 7::::::::::::::::::7  A:::A              CCC::::::::::::C
3::::::33333::::::37::::::::::::::::::7 A:::::A           CC:::::::::::::::C
3333333     3:::::3777777777777:::::::7A:::::::A         C:::::CCCCCCCC::::C
            3:::::3           7::::::7A:::::::::A       C:::::C       CCCCCC
            3:::::3          7::::::7A:::::A:::::A     C:::::C              
    33333333:::::3          7::::::7A:::::A A:::::A    C:::::C              
    3:::::::::::3          7::::::7A:::::A   A:::::A   C:::::C              
    33333333:::::3        7::::::7A:::::A     A:::::A  C:::::C              
            3:::::3      7::::::7A:::::AAAAAAAAA:::::A C:::::C              
            3:::::3     7::::::7A:::::::::::::::::::::AC:::::C              
            3:::::3    7::::::7A:::::AAAAAAAAAAAAA:::::AC:::::C       CCCCCC
3333333     3:::::3   7::::::7A:::::A             A:::::AC:::::CCCCCCCC::::C
3::::::33333::::::3  7::::::7A:::::A               A:::::ACC:::::::::::::::C
3:::::::::::::::33  7::::::7A:::::A                 A:::::A CCC::::::::::::C
 333333333333333   77777777AAAAAAA                   AAAAAAA   CCCCCCCCCCCCC
                                                                            
                                                                             """
    )
    print("=" * 80)
    print("1. 训练模型")
    print("2. 预测角色")
    print("3. 验证图像")
    print("4. 启动节点")
    print("0. 退出程序")
    print("-" * 40)
