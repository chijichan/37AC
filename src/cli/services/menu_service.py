# services/menu_service.py
import os
import sys
import argparse
from utils.validation_utils import validate_dataset_images
from utils.image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger(__name__)


def verify_images_function():
    """单独的图像文件验证功能"""
    from config.base import DATASET_DIR

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


def ask_dataset_choice():
    """询问用户选择数据集：原始数据集 或 已裁剪数据集 或 裁剪新数据集"""
    from config.base import DATASET_DIR, CROPPED_DATASET_DIR

    print()
    print("=" * 40)
    print("  选择训练数据集")
    print("=" * 40)
    print(f"  [1] 原始数据集: {DATASET_DIR}")
    print(f"  [2] 已裁剪数据集: {CROPPED_DATASET_DIR}（使用已存在的 _yolo 裁剪结果）")
    print(f"  [3] 使用 YOLO 裁剪原始数据集后训练（从头裁剪，保存到 saves/dataset/）")
    print("-" * 40)

    while True:
        choice = input("请选择 (1/2/3): ").strip()
        if choice == "1":
            return str(DATASET_DIR), False
        elif choice == "2":
            return str(CROPPED_DATASET_DIR), False
        elif choice == "3":
            return str(DATASET_DIR), True
        else:
            print("无效选择，请输入 1、2 或 3")
