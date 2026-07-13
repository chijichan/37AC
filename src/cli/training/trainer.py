# training/trainer.py
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
from data.dataset import IPRoleImageFolder
from models.character_model import CharacterRecognitionModel
from utils.file_utils import save_classes_to_file
from config.base import *
from config.log_config import get_logger

logger = get_logger(__name__)

# 数据预处理
TRAIN_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


def train_model(dataset_dir=None, use_yolo_crop=False):
    # 确定训练用数据集目录
    train_dir = dataset_dir or str(DATASET_DIR)

    # 检查数据集目录
    if not os.path.exists(train_dir):
        logger.error(f"数据集目录不存在: {train_dir}")
        logger.error(
            "请先创建数据集目录，在每个IP文件夹下，为每个角色创建一个子文件夹，子文件夹内放入对应角色的图片。"
        )
        return

    if not os.access(train_dir, os.R_OK):
        logger.error(f"数据集目录不可读: {train_dir}")
        return

    # ======================
    # === YOLO 数据集裁剪 ===
    # ======================
    if use_yolo_crop:
        logger.info("用户选择使用 YOLO 裁剪数据集图片...")
        try:
            from detection.yolo_detector import crop_dataset
            output_dir = str(CROPPED_DATASET_DIR)
            result = crop_dataset(train_dir, output_dir, max_images_per_role=MAX_IMAGES_PER_ROLE)
            if result["processed"] > 0:
                logger.info(
                    "YOLO 裁剪完成: 处理 %d 张, 跳过 %d 张, 失败 %d 张",
                    result["processed"], result["skipped"], result["failed"]
                )
            else:
                logger.info("YOLO 未裁剪新图片（可能已全部处理过）")
            # 用裁剪后的数据集训练
            train_dir = output_dir
            logger.info("使用 YOLO 裁剪后的数据集: %s", train_dir)
        except ImportError:
            logger.warning("YOLO 模块未安装 (ultralytics)，跳过裁剪步骤")
        except Exception as e:
            logger.error("YOLO 裁剪过程出错: %s", e)
    else:
        logger.info("使用数据集: %s", train_dir)

    # 数据预处理
    data_transform = TRAIN_TRANSFORMS

    try:
        # 使用自定义的 IPRoleImageFolder 加载数据集
        train_dataset = IPRoleImageFolder(root=train_dir, transform=data_transform)
        class_names = train_dataset.classes
        NUM_CLASSES = len(class_names)
        logger.info(f"使用 {NUM_CLASSES} 个角色类别进行训练: {class_names}")

        train_loader = DataLoader(
            train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2
        )

        # 模型定义
        model_handler = CharacterRecognitionModel(NUM_CLASSES)
        model = model_handler.get_model()

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

        logger.info("开始训练咯...")

        best_accuracy = 0.0
        for epoch in range(NUM_EPOCHS):
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            from tqdm import tqdm

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
                model_handler.save_model(MODEL_PATH)
                logger.info(
                    f"保存最佳模型 (准确率: {best_accuracy:.2f}%) 到: {str(MODEL_PATH)}"
                )
                save_classes_to_file(CLASSES_TXT_PATH, class_names)  # 保存类别名称

        # 训练完成，输出最终模型
        logger.info(
            f"模型保存完成 (准确率: {best_accuracy:.2f}%) 到: {str(MODEL_PATH)}"
        )
        logger.info(f"类别名称已保存到: {str(CLASSES_TXT_PATH)}")

    except Exception as e:
        logger.error(f"训练过程中出现严重错误: {str(e)}", exc_info=True)
