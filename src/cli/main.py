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

    # 判断训练方式优先级：命令行 --resume > 交互选择
    from config.base import MODEL_PATH
    resume_model = None

    if args and args.resume:
        # 命令行模式：--resume 已指定
        if args.resume == "auto":
            resume_model = str(MODEL_PATH)
            logger.info("继续训练模式（命令行），使用当前模型: %s", resume_model)
        else:
            resume_model = args.resume
            logger.info("继续训练模式（命令行），使用指定权重: %s", resume_model)
    elif args and args.mode:
        # 命令行模式：--mode 1 不带 --resume，从头训练
        logger.info("从头训练模式（命令行），使用 ImageNet 预训练")
    else:
        # 交互模式：弹出子菜单让用户选择
        print()
        print("=" * 40)
        print("  选择训练方式")
        print("=" * 40)
        print("  [1] 从头训练（ImageNet 预训练）")
        print(f"  [2] 继续训练（基于已有权重: {MODEL_PATH.name}）")
        print("-" * 40)

        while True:
            mode_choice = input("请选择 (1/2): ").strip()
            if mode_choice == "1":
                resume_model = None
                break
            elif mode_choice == "2":
                resume_model = str(MODEL_PATH)
                logger.info("继续训练模式，使用当前模型: %s", resume_model)
                break
            else:
                print("无效选择，请输入 1 或 2")

    if args and args.dataset:
        train_model(dataset_dir=args.dataset, use_yolo_crop=args.yolo_crop,
                    resume_model=resume_model)
    else:
        dataset_dir, use_yolo = ask_dataset_choice()
        train_model(dataset_dir=dataset_dir, use_yolo_crop=use_yolo,
                    resume_model=resume_model)


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
    parser.add_argument("--resume", type=str, default=None, nargs="?",
                        const="auto", metavar="MODEL_PATH",
                        help="从已有模型权重继续训练（指定 .pth 路径，或留空自动使用当前模型）")
    args = parser.parse_args()
    logger.debug("命令行参数: mode=%s, gpu=%s, yolo_crop=%s, dataset=%s, resume=%s",
                 args.mode, args.gpu, args.yolo_crop, args.dataset, args.resume)

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
