# services/menu_service.py
import os
import sys
import argparse
from utils.validation_utils import validate_dataset_images
from utils.image_utils import validate_image_file
from config.log_config import get_logger

logger = get_logger("menu_service")


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
        logger.error("数据集目录不存在: %s", DATASET_DIR)
        logger.error(
            "请先创建数据集目录，结构为: 作品文件夹/角色文件夹/图片"
        )
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error("数据集目录不可读: %s", DATASET_DIR)
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

    logger.info("数据集总计: %d 个图像文件", total_samples)
    logger.info("有效图像: %d 个", valid_samples)
    logger.info("无效图像: %d 个", total_samples - valid_samples)

    if valid_samples == 0:
        logger.error("没有有效的图像文件")
        return

    valid_ratio = (valid_samples / total_samples) * 100
    logger.info("有效图像比例: %.2f%%", valid_ratio)
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
        logger.error("数据集目录不存在: %s", DATASET_DIR)
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error("数据集目录不可读: %s", DATASET_DIR)
        return

    try:
        from detection.yolo_detector import crop_dataset
    except ImportError:
        logger.warning("YOLO 模块未安装 (ultralytics)，无法裁剪数据集")
        return

    from utils.cli_input import ExitProgram, KeyWatcher, GoBack, ask, read_line
    from utils.concurrency import CancelToken

    # 裁剪范围（在开启按键监听之前询问，避免监听线程抢走 input 的按键）
    only_roles = None
    reset_roles = False
    print("  [1] 全部裁剪（所有角色）")
    print("  [2] 只裁剪指定角色（避免全局重裁产生脏数据）")
    try:
        scope = ask("请选择 (1/2): ", valid=("1", "2"))
    except GoBack:
        print()
        return
    if scope == "2":
        try:
            raw = read_line("  输入角色（可多个，逗号/分号分隔；支持只写角色名或通配符）: ")
        except GoBack:
            print()
            return
        only_roles = [p for p in raw.replace(";", ",").replace("；", ",").replace("，", ",").split(",") if p.strip()]
        if not only_roles:
            logger.warning("没有输入角色，已取消")
            return
        try:
            reset = ask("  先清空这些角色在数据集里的旧产物再重裁？(y/N): ", valid=("y", "Y", "n", "N"))
        except GoBack:
            print()
            return
        reset_roles = reset.lower() == "y"
        logger.info("指定裁剪角色: %s%s", ", ".join(only_roles),
                    "（先清空旧产物）" if reset_roles else "")

    token = CancelToken()
    watcher = KeyWatcher()
    watcher.on_back = token.cancel          # ESC / Ctrl+Z → 停止裁剪
    watcher.start()
    print("  提示：ESC / Ctrl+Z 停止并返回上级菜单，Ctrl+C 结束程序（已处理的图片保留）")
    logger.info("开始裁剪原始数据集: %s → %s", DATASET_DIR, CROPPED_DATASET_DIR)
    try:
        result = crop_dataset(
            str(DATASET_DIR),
            str(CROPPED_DATASET_DIR),
            max_images_per_role=MAX_IMAGES_PER_ROLE,
            cancel_event=token,
            only_roles=only_roles,
            reset_roles=reset_roles,
        )
    finally:
        watcher.stop()

    if result.get("interrupted") or watcher.back_requested:
        logger.warning(
            "裁剪已停止: 本次处理 %d 张, 跳过 %d 张, 失败 %d 张；"
            "已完成的图片保留在数据集目录，下次运行会跳过它们继续",
            result["processed"], result["skipped"], result["failed"],
        )
        if watcher.back_requested and not watcher.exit_requested:
            logger.info("已按 ESC/Ctrl+Z 停止，返回上级菜单")
            print("=" * 50)
            return
        raise ExitProgram()                 # Ctrl+C → 结束程序
    logger.info(
        "裁剪完成: 处理 %d 张, 跳过 %d 张, 失败 %d 张",
        result["processed"], result["skipped"], result["failed"],
    )
    print("=" * 50)


def convert_dataset_jpeg_function():
    """把数据集里的 PNG 等统一转成 JPEG（训练读图更快）"""
    from config.base import CROPPED_DATASET_DIR, DATASET_COMPRESS_QUALITY, DATASET_COMPRESS_WORKERS

    print()
    print("=" * 50)
    print("  数据集转 JPEG")
    print("=" * 50)
    if not os.path.isdir(CROPPED_DATASET_DIR):
        logger.error("已裁剪数据集不存在: %s", CROPPED_DATASET_DIR)
        return

    from utils.cli_input import ExitProgram, KeyWatcher
    from utils.concurrency import CancelToken
    from utils.image_utils import convert_dataset_to_jpeg

    token = CancelToken()
    watcher = KeyWatcher()
    watcher.on_back = token.cancel
    watcher.start()
    print("  提示：ESC / Ctrl+Z 停止并返回上级菜单，Ctrl+C 结束程序")
    try:
        result = convert_dataset_to_jpeg(
            str(CROPPED_DATASET_DIR),
            quality=DATASET_COMPRESS_QUALITY,
            workers=DATASET_COMPRESS_WORKERS,
            cancel_token=token,
        )
    finally:
        watcher.stop()
    if watcher.back_requested and not watcher.exit_requested:
        logger.info("已按 ESC/Ctrl+Z 停止，返回上级菜单")
        print("=" * 50)
        return
    if result.get("interrupted") and not watcher.back_requested:
        raise ExitProgram()
    print("=" * 50)


def compress_dataset_function():
    """压缩已裁剪数据集（最长边压到 DATASET_COMPRESS_SIZE 以内）"""
    from config.base import (
        CROPPED_DATASET_DIR,
        DATASET_COMPRESS_SIZE,
        DATASET_COMPRESS_QUALITY,
        DATASET_COMPRESS_WORKERS,
    )

    print()
    print("=" * 50)
    print("  压缩数据集")
    print("=" * 50)

    if DATASET_COMPRESS_SIZE <= 0:
        logger.warning("数据集压缩已禁用（DATASET_COMPRESS_SIZE=0），请先在 .env 配置")
        return

    if not os.path.isdir(CROPPED_DATASET_DIR):
        logger.error("已裁剪数据集不存在: %s", CROPPED_DATASET_DIR)
        return

    from utils.cli_input import ExitProgram, KeyWatcher
    from utils.concurrency import CancelToken
    from utils.image_utils import compress_dataset_images

    token = CancelToken()
    watcher = KeyWatcher()
    watcher.on_back = token.cancel
    watcher.start()
    print("  提示：ESC / Ctrl+Z 停止并返回上级菜单，Ctrl+C 结束程序")
    logger.info(
        "开始压缩: %s（最长边 %d, 并发 %d）",
        CROPPED_DATASET_DIR, DATASET_COMPRESS_SIZE, DATASET_COMPRESS_WORKERS,
    )
    try:
        result = compress_dataset_images(
            str(CROPPED_DATASET_DIR),
            max_size=DATASET_COMPRESS_SIZE,
            quality=DATASET_COMPRESS_QUALITY,
            workers=DATASET_COMPRESS_WORKERS,
            cancel_token=token,
        )
    finally:
        watcher.stop()

    logger.info(
        "压缩%s: 总计 %d, 已压缩 %d, 跳过 %d, 失败 %d",
        "已停止" if (result.get("interrupted") or watcher.back_requested) else "完成",
        result["total"], result["compressed"], result["skipped"], result["failed"],
    )
    if watcher.back_requested and not watcher.exit_requested:
        logger.info("已按 ESC/Ctrl+Z 停止，返回上级菜单")
        print("=" * 50)
        return
    if result.get("interrupted") and not watcher.back_requested:
        raise ExitProgram()
    print("=" * 50)


def show_dataset_menu():
    """显示数据集管理子菜单"""
    print()
    print("=" * 40)
    print("  数据集管理")
    print("=" * 40)
    print("  [1] 验证图像（检查数据集目录与图片有效性）")
    print("  [2] 裁剪数据集（YOLO 裁剪原始数据集，自动压缩）")
    print("  [3] 压缩数据集（压缩 saves/dataset 内图片）")
    print("  [4] 转 JPEG（统一为 JPEG，训练读图更快）")
    print("  [0] 返回主菜单")
    print("  " + "─" * 30)
    print("  ESC / Ctrl+Z 返回上级菜单，Ctrl+C 结束程序")
    print("-" * 40)


def run_dataset_settings():
    """数据集管理子菜单交互循环"""
    from utils.cli_input import GoBack, ask

    while True:
        drain_pending_input()
        show_dataset_menu()
        try:
            choice = ask("请选择 (1/2/3/4/0): ", valid=("1", "2", "3", "4", "0"))
        except GoBack:
            print()
            return
        if choice == "0":
            return
        elif choice == "1":
            verify_images_function()
        elif choice == "2":
            crop_dataset_function()
        elif choice == "3":
            compress_dataset_function()
        elif choice == "4":
            convert_dataset_jpeg_function()
        else:
            print("无效选择，请输入 1、2、3 或 0")


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
    ("1", "模型管理", "训练、检查点与训练基模"),
    ("2", "识别角色", "识别图片中的动漫角色"),
    ("3", "数据集管理", "验证图像、YOLO 裁剪、压缩数据集"),
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

    from utils.cli_input import GoBack, ask

    while True:
        try:
            choice = ask("请选择 (1/2/0): ", valid=("1", "2", "0"))
        except GoBack:
            print()
            return None
        if choice == "0":
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
    print("  ESC / Ctrl+Z 返回上级菜单，Ctrl+C 结束程序")


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
    print(f"  [2] 已裁剪数据集: {CROPPED_DATASET_DIR}（使用已存在的 _37ac 裁剪结果）")
    print(f"  [3] 使用 YOLO 裁剪原始数据集后训练（从头裁剪，保存到 saves/dataset/）")
    print("  [0] 返回主菜单")
    print("-" * 40)

    from utils.cli_input import GoBack, ask

    while True:
        try:
            choice = ask("请选择 (1/2/3/0): ", valid=("1", "2", "3", "0"))
        except GoBack:
            print()
            return None, None
        if choice == "0":
            return None, None
        elif choice == "1":
            return str(DATASET_DIR), False
        elif choice == "2":
            return str(CROPPED_DATASET_DIR), False
        elif choice == "3":
            return str(DATASET_DIR), True
        else:
            print("无效选择，请输入 1、2、3 或 0")


# ==================== 模型管理子菜单 ====================
def _write_env_value(key: str, value: str) -> bool:
    """把 KEY=VALUE 写回 src/cli/.env（不存在则追加；注释行不动）。"""
    from config.base import ROOT_PATH

    env_path = ROOT_PATH / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    for i, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[i] = "%s=%s" % (key, value)
            break
    else:
        lines.append("%s=%s" % (key, value))
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def show_model_menu():
    print()
    print("=" * 40)
    print("  模型管理")
    print("=" * 40)
    print("  [1] 训练 / 继续训练")
    print("  [2] 检查点管理（列表 / 回滚 / 删除 / 清理）")
    print("  [3] 训练基模（查看当前基模）")
    print("  [4] 当前模型信息")
    print("  [0] 返回主菜单")
    print("  " + "─" * 30)
    print("  ESC / Ctrl+Z 返回上级菜单，Ctrl+C 结束程序")
    print("-" * 40)


def show_checkpoint_list():
    from services.checkpoint_service import list_checkpoints, current_info

    items = list_checkpoints()
    info = current_info()
    print()
    print("=" * 56)
    print("  检查点（当前版本 %s，共 %d 个）" % (info.get("version"), len(items)))
    print("=" * 56)
    if not items:
        print("  （暂无检查点；进入本菜单时会自动为当前模型建 baseline）")
    for idx, it in enumerate(items, 1):
        flag = "" if it.get("exists") else "  [目录缺失]"
        acc = ("  正确率 %.2f%%" % it["accuracy"]) if it.get("accuracy") is not None else ""
        print("  [%2d] %-40s %-10s %6.1fMB%s" % (
            idx, it.get("name"), it.get("kind"), float(it.get("size_mb") or 0), acc))
        print("       %s%s" % (it.get("created_at"), flag))
    print("-" * 56)


def run_checkpoint_settings():
    """检查点管理循环"""
    from utils.cli_input import GoBack, ask
    from services import checkpoint_service as CS

    while True:
        drain_pending_input()
        show_checkpoint_list()
        print("  [r] 回滚到某个检查点   [d] 删除   [p] 清理（保留最近 10 个）   [0] 返回")
        try:
            choice = ask("请选择 (r/d/p/0): ", valid=("r", "R", "d", "D", "p", "P", "0"))
        except GoBack:
            print()
            return
        choice = choice.lower()
        if choice == "0":
            return
        if choice == "p":
            result = CS.prune(keep=10, max_total_mb=2000)
            logger.info("清理完成: 删除 %d 个，保留 %d 个，合计 %.1f MB",
                        len(result["removed"]), result["kept"], result["total_mb"])
            continue
        items = CS.list_checkpoints()
        if not items:
            continue
        try:
            pick = ask("  输入序号: ")
        except GoBack:
            continue
        try:
            item = items[int(pick) - 1]
        except (ValueError, IndexError):
            logger.warning("无效序号: %s", pick)
            continue
        if choice == "r":
            try:
                confirm = ask("  回滚到 %s ？当前模型会先自动备份 (y/N): " % item["name"],
                              valid=("y", "Y", "n", "N"))
            except GoBack:
                continue
            if confirm.lower() != "y":
                continue
            result = CS.restore_checkpoint(item["name"])
            if result:
                logger.warning("已回滚到 %s（回滚前状态已存为 %s）", item["name"], result.get("backup"))
        elif choice == "d":
            try:
                confirm = ask("  删除 %s ？(y/N): " % item["name"], valid=("y", "Y", "n", "N"))
            except GoBack:
                continue
            if confirm.lower() == "y":
                CS.delete_checkpoint(item["name"])


def run_model_settings(args=None):
    """模型管理子菜单（训练 / 检查点 / 基模 / 当前信息）"""
    from utils.cli_input import GoBack, ask
    from services import checkpoint_service as CS

    # 迁移：首次进入且没有任何检查点时，为当前模型建一个 baseline
    try:
        if not CS.list_checkpoints():
            meta = CS.create_checkpoint(kind="baseline", note="迁移：进入模型管理时自动建立")
            if meta:
                logger.info("已为当前模型建立基线检查点: %s", meta["name"])
    except Exception as e:
        logger.warning("建立基线检查点失败: %s", e)

    while True:
        drain_pending_input()
        show_model_menu()
        try:
            choice = ask("请选择 (1/2/3/4/0): ", valid=("1", "2", "3", "4", "0"))
        except GoBack:
            print()
            return
        if choice == "0":
            return
        if choice == "1":
            from main import _action_train
            _action_train(args)
        elif choice == "2":
            run_checkpoint_settings()
        elif choice == "3":
            _show_base_model()
        elif choice == "4":
            _show_current_model()


def _show_base_model():
    """训练基模：列出可用基模并可切换（写回 .env，重启后生效）"""
    from config.base import PRETRAINED_BASE, MODEL_MEAN, MODEL_STD
    from models.pretrained import list_bases
    from utils.cli_input import GoBack, ask

    while True:
        bases = list_bases()
        print()
        print("=" * 56)
        print("  训练基模")
        print("=" * 56)
        print("  当前基模: %s" % PRETRAINED_BASE)
        print("  预处理均值: %s   方差: %s" % (list(MODEL_MEAN), list(MODEL_STD)))
        print("-" * 56)
        print("  [0] imagenet-resnet18（内置：torchvision IMAGENET1K_V1）")
        for idx, b in enumerate(bases, 1):
            mark = " ←当前" if b["id"] == PRETRAINED_BASE else ""
            print("  [%d] %-20s %-9s %7sMB  输入%4s  %s%s" % (
                idx, b["id"], b["arch"] or "?", b["weights_mb"] or 0,
                b["input_size"] or "?", b["license"] or "许可未知", mark))
        if not bases:
            print("  （saves/models/pretrained/ 下暂无基模）")
        print("-" * 56)
        print("  说明：切换只改 .env 的 PRETRAINED_BASE，重启程序后对新训练生效")
        try:
            pick = ask("选择要使用的基模序号（0=内置，回车返回）: ", blank_means_back=True)
        except GoBack:
            print()
            return
        chosen = "imagenet-resnet18"
        if pick != "0":
            try:
                chosen = bases[int(pick) - 1]["id"]
            except (ValueError, IndexError):
                logger.warning("无效序号: %s", pick)
                continue
        _write_env_value("PRETRAINED_BASE", chosen)
        logger.info("已切换训练基模为 %s（写入 .env，重启后生效）", chosen)
        return


def _show_current_model():
    from services.checkpoint_service import current_info

    info = current_info()
    print()
    print("=" * 48)
    print("  当前模型信息")
    print("=" * 48)
    for key, label in (("version", "版本"), ("trained_at", "训练时间"), ("class_count", "类别数"),
                       ("model_file", "权重文件"), ("model_size_mb", "权重大小(MB)"),
                       ("base", "来源基模"), ("checkpoints", "检查点数")):
        print("  %-12s %s" % (label, info.get(key)))
    sha = info.get("model_sha256")
    print("  %-12s %s" % ("权重 SHA-256", (sha[:16] + "...") if sha else "（缺失）"))
    print("-" * 48)
