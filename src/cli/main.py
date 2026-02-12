from config import (
    DATASET_DIR,
    MODEL_SAVE_PATH,
    CLASSES_TXT_PATH,
    NUM_EPOCHS,
    BATCH_SIZE,
    IMAGE_SIZE,
    LEARNING_RATE,
    MODEL_LOAD_PATH,
)
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
from tqdm import tqdm
import hashlib
from typing import List, Optional, Tuple, Dict, Any
import argparse

# ======================
# ===== 全局配置 =====
# ======================
# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# 允许PIL加载截断的图像文件，增强健壮性
ImageFile.LOAD_TRUNCATED_IMAGES = True

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"使用设备: {DEVICE}")

# 数据预处理
TRAIN_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)

# 工具函数

import warnings
from PIL import Image


def validate_image_file(file_path: str) -> bool:
    """
    终极版图片验证：可检测以下问题：
    - 图片文件是否损坏（基础验证）
    - 图片尺寸是否合法
    - 是否能转为 RGB
    - 是否存在 EXIF 数据异常（如 Corrupt EXIF data...）
    """
    try:
        # -------------------------------
        # 新增：用 warnings 捕获该图片打开过程中产生的所有 UserWarning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # 确保所有警告都被捕获

            # 1. 打开图片（可能触发 EXIF 相关的 Warning）
            with Image.open(file_path) as img:
                img.verify()  # 基础验证：检测是否为有效图片数据

            # 2. 重新打开，进一步检测
            with Image.open(file_path) as img:
                # 检查尺寸
                width, height = img.size
                if width <= 0 or height <= 0:
                    logger.warning(
                        f"图片尺寸异常（宽或高 <= 0） {file_path}: {width}x{height}"
                    )
                    return False

                # 尝试转为 RGB
                try:
                    rgb_img = img.convert("RGB")
                except Exception as e:
                    logger.warning(
                        f"图片色彩模式异常，无法转为 RGB {file_path}: {str(e)}"
                    )
                    return False

                # 至此，图片基本看起来是正常的
                # 但我们还是要检查是否在打开过程中捕获到了 EXIF 相关的 Warning
                # 如：Corrupt EXIF data. Expecting to read 4 bytes but only got 0.

                # 检查刚刚捕获的 warnings
                exif_warning_detected = any(
                    "Corrupt EXIF data" in str(warn.message)
                    or "Expecting to read 4 bytes but only got 0" in str(warn.message)
                    for warn in w
                    if warn.category == UserWarning
                )

                if exif_warning_detected:
                    # logger.warning(f"检测到图片 EXIF 数据异常（PIL 警告） {file_path}")
                    # 如果您希望把 EXIF 异常也视为图片无效，请取消下面这行注释：
                    logger.warning(f"图片因 EXIF 异常视为无效: {file_path}")
                    return False
                    # 当前策略：仅警告，不阻断（您可自主选择严格模式）

                # 如果没有 EXIF 警告，认为图片有效
                return True

    except (
        IOError,
        OSError,
        Image.DecompressionBombError,
        Image.UnidentifiedImageError,
        ValueError,
        IndexError,
    ) as e:
        logger.warning(f"图片文件验证失败（数据/格式错误） {file_path}: {str(e)}")
        return False
    except Exception as e:
        logger.warning(f"图片文件发生未知错误 {file_path}: {str(e)}")
        return False


def calculate_file_hash(
    file_path: str, hash_algorithm: str = "md5", buffer_size: int = 65536
) -> Optional[str]:
    """计算文件的哈希值"""
    try:
        hasher = hashlib.new(hash_algorithm)
        with open(file_path, "rb") as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败 {file_path}: {str(e)}")
        return None


def ensure_directory_exists(dir_path: str) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {dir_path}: {str(e)}")
        return False


def load_classes_from_file(file_path: str) -> Optional[List[str]]:
    """从文件加载类别列表"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"类别文件不存在: {file_path}")
            return None

        if not os.access(file_path, os.R_OK):
            logger.error(f"类别文件不可读: {file_path}")
            return None

        CLASS_NAMES = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 忽略空行
                    CLASS_NAMES.append(line)

        if not CLASS_NAMES:
            logger.error(f"类别文件为空或格式不正确: {file_path}")
            return None

        logger.info(f"从文件加载到 {len(CLASS_NAMES)} 个角色类别")
        return CLASS_NAMES
    except Exception as e:
        logger.error(f"加载类别文件失败 {file_path}: {str(e)}")
        return None


def save_classes_to_file(file_path: str, class_names: List[str]) -> bool:
    """保存类别列表到文件"""
    try:
        ensure_directory_exists(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as f:
            for name in class_names:
                f.write(name + "\n")
        logger.info(f"类别名称已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存类别文件失败 {file_path}: {str(e)}")
        return False


def check_model_file(file_path: str) -> bool:
    """检查模型文件是否存在且可读"""
    if not os.path.exists(file_path):
        logger.error(f"模型文件不存在: {file_path}")
        return False
    if not os.access(file_path, os.R_OK):
        logger.error(f"模型文件不可读: {file_path}")
        return False
    return True


def validate_dataset_images(dataset_dir: str) -> Tuple[int, int, List[str], List[str]]:
    """验证数据集中的图像文件"""
    valid_samples = 0
    total_samples = 0
    class_names = []
    invalid_image_paths = []  # 存储无效图像路径
    invalid_classes = []  # 存储包含无效图像的类别

    try:
        # 尝试加载数据集以获取类别信息
        if os.path.exists(dataset_dir):
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


# ======================
# ===== 3. 验证图像文件 =====
# ======================
def verify_images_function():
    """单独的图像文件验证功能"""

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


class IPRoleImageFolder(datasets.ImageFolder):
    def find_classes(self, directory: str):
        """
        重写 find_classes 方法，将目录结构 IP@角色 映射为类别名 "IP@角色"
        """
        ip_names = sorted(
            [
                d
                for d in os.listdir(directory)
                if os.path.isdir(os.path.join(directory, d)) and not d.startswith(".")
            ]
        )
        class_names = []
        class_to_idx = {}

        for ip_name in ip_names:
            ip_path = os.path.join(directory, ip_name)
            role_names = sorted(
                [
                    r
                    for r in os.listdir(ip_path)
                    if os.path.isdir(os.path.join(ip_path, r))
                ]
            )
            for role_name in role_names:
                class_name = f"{ip_name}/{role_name}"  # 格式: IP@角色
                class_names.append(class_name)
                class_to_idx[class_name] = len(class_to_idx)

        logger.info(f"自动生成 {len(class_names)} 个类别（格式: IP@角色）")
        return class_names, class_to_idx


# ======================
# ===== 4. 训练函数 =====
# ======================
def train_model():
    logger.info("\n=== 1. 训练模型 ===")

    # 检查数据集目录
    if not os.path.exists(DATASET_DIR):
        logger.error(f"数据集目录不存在: {DATASET_DIR}")
        logger.error(
            "请先创建数据集目录，在每个IP文件夹下，为每个角色创建一个子文件夹，子文件夹内放入对应角色的图片。"
        )
        return

    if not os.access(DATASET_DIR, os.R_OK):
        logger.error(f"数据集目录不可读: {DATASET_DIR}")
        return

    # 数据预处理
    data_transform = TRAIN_TRANSFORMS

    try:
        # 使用自定义的 IPRoleImageFolder 加载数据集
        train_dataset = IPRoleImageFolder(root=DATASET_DIR, transform=data_transform)
        # ============================================================

        class_names = train_dataset.classes
        NUM_CLASSES = len(class_names)
        logger.info(f"使用 {NUM_CLASSES} 个角色类别进行训练: {class_names}")

        train_loader = DataLoader(
            train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2
        )

        # 模型定义
        model = resnet18(weights=None)
        model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
        model = model.to(DEVICE)

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

        logger.info("(ง •̀_•́)ง 开始训练咯...")

        best_accuracy = 0.0
        for epoch in range(NUM_EPOCHS):
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            loop = tqdm(train_loader, desc=f"第 {epoch+1}/{NUM_EPOCHS} 轮训练")
            for inputs, labels in loop:
                try:
                    inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)

                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()

                    running_loss += loss.item()
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)

                    current_acc = correct / total if total > 0 else 0.0
                    loop.set_postfix(
                        loss=f"{running_loss/(loop.n+1):.4f}",
                        acc=f"{100.*current_acc:.2f}%",
                    )
                except Exception as e:
                    logger.error(f"训练过程中出现错误: {str(e)}")
                    continue

            epoch_acc = 100.0 * correct / total if total > 0 else 0.0
            epoch_loss = (
                running_loss / len(train_loader) if len(train_loader) > 0 else 0.0
            )
            logger.info(
                f"第 {epoch+1} 轮完成 | 损失: {epoch_loss:.4f} | 正确率: {epoch_acc:.2f}%"
            )

            if epoch_acc > best_accuracy:
                best_accuracy = epoch_acc
                torch.save(model.state_dict(), MODEL_SAVE_PATH)
                logger.info(
                    f"保存最佳模型 (准确率: {best_accuracy:.2f}%) 到: {MODEL_SAVE_PATH}"
                )

        # 训练完成，保存最终模型
        torch.save(model.state_dict(), MODEL_SAVE_PATH)
        logger.info("模型保存好啦~ 文件: " + MODEL_SAVE_PATH)

        # 保存类别名称
        if save_classes_to_file(CLASSES_TXT_PATH, class_names):
            logger.info("类别名称已保存到: " + CLASSES_TXT_PATH)
        else:
            logger.error("保存类别名称失败")

    except Exception as e:
        logger.error(f"训练过程中出现严重错误: {str(e)}", exc_info=True)


# ======================
# ===== 5. 预测函数 =====
# ======================
def predict_character():
    logger.info("\n=== 2. 预测角色 ===")

    # --- 1. 加载类别 ---
    global CLASS_NAMES
    classes_file = CLASSES_TXT_PATH

    CLASS_NAMES = load_classes_from_file(classes_file)
    if CLASS_NAMES is None:
        return

    # --- 2. 加载模型 ---
    if not check_model_file(MODEL_LOAD_PATH):
        return

    try:
        model = resnet18(weights=None)
        num_classes = len(CLASS_NAMES)
        model.fc = nn.Linear(model.fc.in_features, num_classes)

        # 加载模型状态字典
        state_dict = torch.load(MODEL_LOAD_PATH, map_location=DEVICE)
        model.load_state_dict(state_dict)

        model = model.to(DEVICE)
        model.eval()
        logger.info("模型加载成功")

    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}", exc_info=True)
        return

    # --- 3. 用户输入图片路径 ---
    while True:
        user_input = input(
            "Hiahiahia… 请输入你要预测的图片路径（或输入 0 返回主菜单）: "
        ).strip()
        if user_input == "0":
            logger.info("好的，返回主菜单~")
            return
        if not user_input:
            logger.info("路径不能为空哦，再试一次吧~")
            continue
        if not os.path.exists(user_input):
            logger.info(f"找不到图片: {user_input}，请检查路径是否正确~")
            continue
        if not user_input.lower().endswith((".jpg", ".jpeg", ".png")):
            logger.info("请上传图片文件（如 .jpg / .png），当前格式可能不支持~")
            continue

        TEST_IMAGE_PATH = user_input

        # 验证图像文件
        if not validate_image_file(TEST_IMAGE_PATH):
            logger.info(f"图像文件可能已损坏或格式不正确: {TEST_IMAGE_PATH}")
            continue

        # --- 4. 图像预处理 ---
        transform = TRAIN_TRANSFORMS

        # --- 5. 预测 ---
        try:
            image = Image.open(TEST_IMAGE_PATH).convert("RGB")
            image_tensor = transform(image).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                output = model(image_tensor)
                probabilities = torch.softmax(output, dim=1)
                confidence, predicted_idx = torch.max(probabilities, 1)
                predicted_label = CLASS_NAMES[predicted_idx.item()]
                conf = confidence.item() * 100

                print(f"\n预测结果是: {predicted_label}")
                print(f"置信度: {conf:.2f}%")
                print(f"图片路径: {TEST_IMAGE_PATH}")
                for i, (name, prob) in enumerate(zip(CLASS_NAMES, probabilities[0])):
                    print(f"   → {name}: {prob.item() * 100:.1f}%")
            print()

        except Exception as e:
            logger.error(f"预测过程中出现错误: {str(e)}", exc_info=True)
            logger.info(f"处理图片失败: {TEST_IMAGE_PATH}")


# ======================
# ===== 6. 主菜单 =====
# ======================
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
        print("7888")
        from node import start_node_service

        start_node_service()
        return

    while True:
        try:
            print("\n" + "=" * 40)
            print("(｡･ω･｡) 二次元角色识别小助手")
            print("=" * 40)
            print("1. 训练模型")
            print("2. 预测角色")
            print("3. 验证图像文件")
            print("4. 启动节点服务")
            print("0. 退出程序")
            print("-" * 40)

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
                from node import start_node_service

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
