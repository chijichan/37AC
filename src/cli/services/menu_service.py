# services/menu_service.py
import os
import sys
import argparse
from utils.validation_utils import validate_dataset_images
from utils.image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger(__name__)


def drain_pending_input():
    """丢弃 stdin 中残留的输入（如训练/识别等长任务期间用户按下的回车）。

    长任务执行时用户按下的按键会积压在输入缓冲区，任务结束后会被主菜单的
    input() 逐条当作选择消费（空输入不会退出，但会反复重绘主菜单）。
    在每次重新提示前调用本函数清空缓冲区，即可避免主菜单重复打印。
    """
    # Windows 控制台：msvcrt 非阻塞探测并读取按键
    if sys.platform == "win32":
        try:
            import msvcrt
            while msvcrt.kbhit():
                try:
                    msvcrt.getwch()
                except Exception:
                    break
            return
        except (ImportError, OSError):
            pass
    # 其他平台 / 管道输入：select 非阻塞读取
    try:
        import select
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                break
            try:
                sys.stdin.readline()
            except Exception:
                break
    except (ImportError, OSError, ValueError):
        pass


def verify_images_function():
    """验证数据集中的图像文件（适配 IP/角色 两级目录结构）"""
    from config.base import DATASET_DIR

    print()
    print("=" * 50)
    print("  验证图像文件")
    print("=" * 50)

    # 检查数据集目录
    if not os.path.exists(DATASET_DIR):
        logger.error(f"数据集目录不存在: {DATASET_DIR}")
        logger.error(
            "请先创建数据集目录，结构为: 作品文件夹/角色文件夹/图片"
        )
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error(f"数据集目录不可读: {DATASET_DIR}")
        return

    logger.info("数据集目录: %s", DATASET_DIR)
    print("-" * 50)

    # 遍历 IP/角色 结构
    valid_samples, total_samples, class_names, invalid_image_paths = (
        validate_dataset_images(DATASET_DIR)
    )

    print("-" * 50)

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
    print("=" * 50)

    if invalid_image_paths:
        logger.info(
            "建议: 请检查并修复或删除上述无效图像文件，然后重新尝试训练或预测"
        )


def crop_dataset_function():
    """使用 YOLO 对原始数据集进行裁剪，输出到 saves/dataset（IP/角色 结构镜像）"""
    from config.base import DATASET_DIR, CROPPED_DATASET_DIR, MAX_IMAGES_PER_ROLE

    print()
    print("=" * 50)
    print("  裁剪数据集（YOLO）")
    print("=" * 50)

    if not os.path.exists(DATASET_DIR):
        logger.error(f"数据集目录不存在: {DATASET_DIR}")
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error(f"数据集目录不可读: {DATASET_DIR}")
        return

    try:
        from detection.yolo_detector import crop_dataset
    except ImportError:
        logger.warning("YOLO 模块未安装 (ultralytics)，无法裁剪数据集")
        return

    logger.info("开始裁剪原始数据集: %s → %s", DATASET_DIR, CROPPED_DATASET_DIR)
    result = crop_dataset(
        str(DATASET_DIR),
        str(CROPPED_DATASET_DIR),
        max_images_per_role=MAX_IMAGES_PER_ROLE,
    )
    logger.info(
        "裁剪完成: 处理 %d 张, 跳过 %d 张, 失败 %d 张",
        result["processed"], result["skipped"], result["failed"],
    )
    print("=" * 50)


def show_dataset_menu():
    """显示数据集管理子菜单"""
    print()
    print("=" * 40)
    print("  数据集管理")
    print("=" * 40)
    print("  [1] 验证图像（检查数据集目录与图片有效性）")
    print("  [2] 裁剪数据集（YOLO 裁剪原始数据集）")
    print("  [0] 返回主菜单")
    print("-" * 40)


def run_dataset_settings():
    """数据集管理子菜单交互循环"""
    while True:
        drain_pending_input()
        show_dataset_menu()
        try:
            choice = input("请选择 (1/2/0): ").strip().strip("\x1a")
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if choice == "0" or choice == "":
            return
        elif choice == "1":
            verify_images_function()
        elif choice == "2":
            crop_dataset_function()
        else:
            print("无效选择，请输入 1、2 或 0")


def _cjk_display_width(text: str) -> int:
    """计算字符串的显示宽度（中文等全角字符按 2 个宽度计算）。"""
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 0x2E7F else 1
    return width


def _pad_display(text: str, width: int) -> str:
    """按显示宽度左对齐补齐空格（兼容中文全角字符）。"""
    return text + " " * max(0, width - _cjk_display_width(text))


# 主菜单项: (编号, 名称, 功能说明)
_MENU_ITEMS = [
    ("1", "训练模型", "训练或继续训练角色识别模型"),
    ("2", "识别角色", "识别图片中的动漫角色"),
    ("3", "数据集管理", "验证图像、YOLO 裁剪数据集"),
    ("4", "节点服务", "启动分布式识别节点"),
    ("0", "退出程序", "结束程序并退出"),
]


def ask_recognition_method():
    """询问用户选择识别方式：本地模型 或 LLM 大模型。
    返回 "local" / "llm"，或 None 表示返回主菜单。
    """
    print()
    print("=" * 40)
    print("  选择识别方式")
    print("=" * 40)
    print("  [1] 本地模型（37ac ResNet，离线快速）")
    print("  [2] LLM 大模型（多模态识别，需配置 API）")
    print("  [0] 返回主菜单")
    print("-" * 40)

    while True:
        try:
            choice = input("请选择 (1/2/0): ").strip().strip("\x1a")
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        if choice == "0" or choice == "":
            return None
        elif choice == "1":
            return "local"
        elif choice == "2":
            return "llm"
        else:
            print("无效选择，请输入 1、2 或 0")


def show_menu():
    """显示主菜单"""
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
    print()
    print("=" * 48)
    for key, name, desc in _MENU_ITEMS:
        print(_pad_display(f"  [{key}] {name}", 19) + desc)
    print("=" * 48)


def ask_dataset_choice():
    """询问用户选择数据集：原始数据集 或 已裁剪数据集 或 裁剪新数据集
    返回 (dataset_dir, use_yolo) 或 (None, None) 表示返回主菜单
    """
    from config.base import DATASET_DIR, CROPPED_DATASET_DIR

    print()
    print("=" * 40)
    print("  选择训练数据集")
    print("=" * 40)
    print(f"  [1] 原始数据集: {DATASET_DIR}")
    print(f"  [2] 已裁剪数据集: {CROPPED_DATASET_DIR}（使用已存在的 _yolo 裁剪结果）")
    print(f"  [3] 使用 YOLO 裁剪原始数据集后训练（从头裁剪，保存到 saves/dataset/）")
    print("  [0] 返回主菜单")
    print("-" * 40)

    while True:
        try:
            choice = input("请选择 (1/2/3/0): ").strip().strip("\x1a")
        except (KeyboardInterrupt, EOFError):
            print()
            return None, None
        if choice == "0" or choice == "":
            return None, None
        elif choice == "1":
            return str(DATASET_DIR), False
        elif choice == "2":
            return str(CROPPED_DATASET_DIR), False
        elif choice == "3":
            return str(DATASET_DIR), True
        else:
            print("无效选择，请输入 1、2、3 或 0")
