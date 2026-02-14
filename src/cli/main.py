# main.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from torchvision.models import resnet18
from PIL import Image, ImageFile
import os
import sys
import logging
import hashlib
from typing import List, Optional, Tuple, Dict, Any
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# 允许PIL加载截断的图像文件，增强健壮性
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 导入配置
from config import *

# 导入各个模块
from training.trainer import train_model
from prediction.predictor import predict_character
from services.menu_service import verify_images_function, show_menu
from services.node_service import start_node_service


def main():
    parser = argparse.ArgumentParser(description="mode")
    parser.add_argument("--mode", type=int, help="模式", default=None)
    parser.add_argument("--gpu", type=bool, default=False)
    args = parser.parse_args()
    print(args)
    print(args.mode)
    print(args.gpu)

    if args.mode == 1:
        logger.info("\n=== 1. 训练模型 ===")
        train_model()
        return
    elif args.mode == 2:
        logger.info("\n=== 2. 预测角色 ===")
        predict_character()
        return
    elif args.mode == 3:
        logger.info("\n=== 3. 验证图像文件 ===")
        verify_images_function()
        return
    elif args.mode == 4:
        logger.info("\n=== 4. 启动节点服务 ===")
        start_node_service()
        return

    while True:
        try:
            show_menu()
            choice = input("请输入你的选择 (1/2/3/4/0): ").strip()

            if choice == "1":
                logger.info("\n=== 1. 训练模型 ===")
                train_model()
            elif choice == "2":
                logger.info("\n=== 2. 预测角色 ===")
                predict_character()
            elif choice == "3":
                logger.info("\n=== 3. 验证图像文件 ===")
                verify_images_function()
            elif choice == "4":
                logger.info("\n=== 4. 启动节点服务 ===")
                start_node_service()
            elif choice == "0":
                logger.info("再见啦！期待下次见面~")
                break
            else:
                logger.info("请输入 1、2、3、4 或 0 哦")
        except KeyboardInterrupt:
            logger.info("\n程序被用户中断，再见！")
            break
        except Exception as e:
            logger.error(f"主程序出现错误: {str(e)}", exc_info=True)
            logger.info("(⊙ˍ⊙) 程序出现未知错误，请重启程序")


if __name__ == "__main__":
    main()
