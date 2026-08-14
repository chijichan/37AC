# main.py
import os
import sys
import logging
import argparse

from PIL import Image, ImageFile

from config.log_config import init_logging, get_logger

logger = get_logger(__name__)

# 允许PIL加载截断的图像文件，增强健壮性
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 导入各个模块
# 注意：torch/torchvision 相关模块（training.trainer、prediction.predictor、
# services.node_service）改为在对应动作函数内延迟导入，避免启动时加载
# PyTorch 导致菜单出现缓慢；菜单本身只依赖轻量模块。
from services.menu_service import (
    show_menu,
    ask_dataset_choice,
    run_dataset_settings,
    drain_pending_input,
)


# 菜单操作映射：菜单编号 → (处理函数)
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
    elif args and getattr(args, "command", None) == "train":
        # train 子命令：命令行模式，不带 --resume 即从头训练
        logger.info("从头训练模式（命令行），使用 ImageNet 预训练")
    else:
        # 交互模式：弹出子菜单让用户选择
        print()
        print("=" * 40)
        print("  选择训练方式")
        print("=" * 40)
        print("  [1] 从头训练（ImageNet 预训练）")
        print(f"  [2] 继续训练（基于已有权重: {MODEL_PATH.name}）")
        print("  [0] 返回主菜单")
        print("-" * 40)

        while True:
            try:
                mode_choice = input("请选择 (1/2/0): ").strip().strip("\x1a")
            except (KeyboardInterrupt, EOFError):
                print()
                return
            if mode_choice == "0" or mode_choice == "":
                logger.info("返回主菜单~")
                return
            elif mode_choice == "1":
                resume_model = None
                break
            elif mode_choice == "2":
                resume_model = str(MODEL_PATH)
                logger.info("继续训练模式，使用当前模型: %s", resume_model)
                break
            else:
                print("无效选择，请输入 1、2 或 0")

    # 训练方式和数据集都确定后才加载训练模块（PyTorch 加载较慢，菜单/选择过程不受影响）
    logger.info("正在加载训练模块（首次加载 PyTorch 较慢，请稍候）...")
    from training.trainer import train_model  # 延迟导入（PyTorch 加载较慢）

    if args and args.dataset:
        train_model(dataset_dir=args.dataset, use_yolo_crop=args.yolo_crop,
                    resume_model=resume_model)
    else:
        dataset_dir, use_yolo = ask_dataset_choice()
        if dataset_dir is None:
            return  # 用户选择返回主菜单
        train_model(dataset_dir=dataset_dir, use_yolo_crop=use_yolo,
                    resume_model=resume_model)


def _action_predict(args=None):
    """识别角色（交互菜单 [2] 弹出识别方式子菜单；predict 子命令用 --llm/--image）"""
    from prediction.predictor import predict_character  # 延迟导入（PyTorch 加载较慢）
    from services.menu_service import ask_recognition_method

    # 识别方式：命令行 predict 子命令由 --llm 决定；交互菜单弹出子菜单选择
    if args is not None and getattr(args, "command", None) == "predict":
        method = "llm" if getattr(args, "llm", False) else "local"
    else:
        method = ask_recognition_method()
    if method is None:
        return

    logger.info("\n=== 2. 识别角色 ===")
    logger.info("正在加载识别模块（首次加载 PyTorch 较慢，请稍候）...")
    predict_character(
        recognition_method=method,
        image_path=getattr(args, "image", None) if args is not None else None,
    )


def _action_dataset(args=None):
    logger.info("\n=== 3. 数据集管理 ===")
    if args is not None and getattr(args, "command", None) == "dataset":
        # dataset 子命令：verify / crop 直接执行；无操作参数时进入交互子菜单
        from services.menu_service import verify_images_function, crop_dataset_function

        action = getattr(args, "dataset_action", None)
        if action == "verify":
            verify_images_function()
            return
        if action == "crop":
            crop_dataset_function()
            return
    run_dataset_settings()


def _action_node(args=None):
    from services.node_service import start_node_service  # 延迟导入（内部会加载 predictor/torch）

    logger.info("\n=== 4. 节点服务 ===")
    logger.info("正在加载节点服务模块（首次加载 PyTorch 较慢，请稍候）...")
    start_node_service()


MENU_ACTIONS = {
    "1": _action_train,
    "2": _action_predict,
    "3": _action_dataset,
    "4": _action_node,
}

# 命令行子命令 → 处理函数
COMMAND_ACTIONS = {
    "train": _action_train,
    "predict": _action_predict,
    "dataset": _action_dataset,
    "node": _action_node,
}


def _force_exit(code: int = 0):
    """立即退出，绕过解释器的线程关闭流程。

    原因：torch 在启动时留有非 daemon 后台线程，正常退出时 Python 会执行
    threading._shutdown() 去 join 它们；若此时刚好有 Ctrl+C 信号到达，会
    中断 shutdown 并打印 "Exception ignored in: <module 'threading'>" 的
    干扰性堆栈（CPython gh-112301）。

    这里先冲刷日志与标准输出，再用 os._exit 直接终止，跳过该竞态。
    """
    try:
        logging.shutdown()
    except Exception:
        pass
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(code)


def main():
    # 初始化统一日志系统（必须在 main 内，避免 DataLoader 子进程重复触发）
    init_logging()

    parser = argparse.ArgumentParser(
        prog="main.py",
        description="37AC 动漫角色识别命令行工具",
        epilog="示例:\n"
               "  python main.py                         # 进入交互菜单（默认）\n"
               "  python main.py train                   # 训练模型（从头，ImageNet 预训练）\n"
               "  python main.py train --resume          # 继续训练（自动使用当前模型）\n"
               "  python main.py train --resume w.pth --dataset ./data --yolo-crop\n"
               "  python main.py predict                 # 识别角色（本地模型，交互输入图片）\n"
               "  python main.py predict --llm           # 识别角色（LLM 大模型）\n"
               "  python main.py predict --llm --image x.jpg   # 直接识别单张图片\n"
               "  python main.py dataset verify          # 验证数据集图像\n"
               "  python main.py dataset crop            # YOLO 裁剪数据集\n"
               "  python main.py node                    # 启动节点服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="命令", help="要执行的操作")

    # 交互菜单（默认，也可显式指定）
    subparsers.add_parser("menu", help="进入交互菜单（默认行为）")

    # train：训练模型
    p_train = subparsers.add_parser("train", help="训练角色识别模型")
    p_train.add_argument("--dataset", type=str, default=None,
                         help="数据集路径（默认使用 .env 的 DATASET_DIR 或交互选择）")
    p_train.add_argument("--resume", type=str, default=None, nargs="?",
                         const="auto", metavar="PATH",
                         help="继续训练：指定 .pth 权重路径，或留空自动使用当前模型")
    p_train.add_argument("--yolo-crop", action="store_true",
                         help="训练前先用 YOLO 裁剪原始数据集")

    # predict：识别角色
    p_predict = subparsers.add_parser("predict", help="识别图片中的角色")
    p_predict.add_argument("--llm", action="store_true",
                           help="使用 LLM 大模型识别（默认使用本地 37ac 模型）")
    p_predict.add_argument("--image", type=str, default=None,
                           help="直接识别指定图片后退出（默认交互输入图片路径）")

    # dataset：数据集管理
    p_dataset = subparsers.add_parser("dataset", help="数据集管理（验证/裁剪，无操作参数时进入交互菜单）")
    ds_sub = p_dataset.add_subparsers(dest="dataset_action", metavar="操作", help="数据集操作")
    ds_sub.add_parser("verify", help="验证数据集图像有效性")
    ds_sub.add_parser("crop", help="使用 YOLO 裁剪数据集")

    # node：节点服务
    subparsers.add_parser("node", help="启动分布式识别节点服务")

    args = parser.parse_args()

    # 交互模式（未使用子命令）时，子命令专属参数不存在于 Namespace，
    # 统一补默认值，避免动作函数访问 args.resume / args.dataset 等抛 AttributeError
    for _attr, _default in (
        ("resume", None),
        ("dataset", None),
        ("yolo_crop", False),
        ("llm", False),
        ("image", None),
        ("dataset_action", None),
    ):
        if not hasattr(args, _attr):
            setattr(args, _attr, _default)

    logger.debug("命令行参数: %s", vars(args))

    # 命令行子命令模式
    if args.command in COMMAND_ACTIONS:
        COMMAND_ACTIONS[args.command](args)
        return

    # 交互模式（无参数或 menu 子命令）
    while True:
        try:
            # 丢弃训练/识别等长任务期间残留的按键，避免结束后主菜单被逐条消费重复打印
            drain_pending_input()
            show_menu()
            choice = input("请输入你的选择 (1/2/3/4/0): ").strip().strip("\x1a")

            if choice == "0":
                logger.info("退出程序，再见~")
                break

            handler = MENU_ACTIONS.get(choice)
            if handler:
                handler(args)
            else:
                logger.info("请输入 1、2、3、4 或 0 哦")
        except KeyboardInterrupt:
            print()  # 换行，避免 ^C 糊在输入行
            logger.info("\n按 Ctrl+C 退出程序，再见~")
            _force_exit(0)
        except EOFError:
            print()
            logger.info("收到 EOF，退出程序")
            _force_exit(0)
        except Exception as e:
            logger.error(f"主程序出现错误: {str(e)}", exc_info=True)
            logger.info("程序出现未知错误，请重启程序")


if __name__ == "__main__":
    main()
