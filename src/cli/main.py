# main.py
from PIL import Image, ImageFile
import sys
import argparse

from config.log_config import init_logging, get_logger

logger = get_logger(__name__)

# 允许PIL加载截断的图像文件，增强健壮性
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 导入各个模块
from training.trainer import train_model
from prediction.predictor import predict_character
from services.menu_service import verify_images_function, show_menu, ask_dataset_choice
from services.node_service import start_node_service


# 菜单操作映射：mode → (名称, 处理函数)
def _action_train(args):
    """训练模型"""
    logger.info("\n=== 1. 训练模型 ===")
    if args and args.dataset:
        train_model(dataset_dir=args.dataset, use_yolo_crop=args.yolo_crop)
    else:
        dataset_dir, use_yolo = ask_dataset_choice()
        train_model(dataset_dir=dataset_dir, use_yolo_crop=use_yolo)


def _action_predict(_args=None):
    logger.info("\n=== 2. 预测角色 ===")
    predict_character()


def _action_verify(_args=None):
    logger.info("\n=== 3. 验证图像文件 ===")
    verify_images_function()


def _action_node(_args=None):
    logger.info("\n=== 4. 启动节点服务 ===")
    start_node_service()


MENU_ACTIONS = {
    "1": _action_train,
    "2": _action_predict,
    "3": _action_verify,
    "4": _action_node,
}


def main():
    # 初始化统一日志系统（必须在 main 内，避免 DataLoader 子进程重复触发）
    init_logging()

    parser = argparse.ArgumentParser(description="mode")
    parser.add_argument("--mode", type=int, help="模式", default=None)
    parser.add_argument("--gpu", type=bool, default=False)
    parser.add_argument("--yolo-crop", action="store_true", help="使用 YOLO 裁剪原始数据集并训练")
    parser.add_argument("--dataset", type=str, default=None, help="训练数据集路径（默认使用 .env 配置或交互选择）")
    args = parser.parse_args()
    logger.debug("命令行参数: mode=%s, gpu=%s, yolo_crop=%s, dataset=%s",
                 args.mode, args.gpu, args.yolo_crop, args.dataset)

    # 命令行模式
    if args.mode and str(args.mode) in MENU_ACTIONS:
        handler = MENU_ACTIONS[str(args.mode)]
        handler(args)
        return

    # 交互模式
    while True:
        try:
            show_menu()
            choice = input("请输入你的选择 (1/2/3/4/0): ").strip()

            if choice == "0":
                logger.info("再见啦！期待下次见面~")
                break

            handler = MENU_ACTIONS.get(choice)
            if handler:
                handler(args)
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
