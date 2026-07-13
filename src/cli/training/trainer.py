# training/trainer.py
import os
import math
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from torchvision import transforms
from PIL import Image
from data.dataset import IPRoleImageFolder
from models.character_model import CharacterRecognitionModel
from utils.file_utils import save_classes_to_file
from config.base import *
from config.log_config import get_logger

logger = get_logger(__name__)

# ==================== 训练集 / 验证集数据增强 ====================

TRAIN_TRANSFORMS = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.10, hue=0.05),
    transforms.RandomRotation(degrees=10, fill=128),
    transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), fill=128),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

VAL_TRANSFORMS = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class LabelSmoothingCrossEntropy(nn.Module):
    """标签平滑交叉熵损失"""

    def __init__(self, smoothing: float = 0.1):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_probs = torch.log_softmax(pred, dim=1)
        n_classes = pred.size(1)
        smooth_target = torch.zeros_like(log_probs).scatter_(
            1, target.unsqueeze(1), 1 - self.smoothing
        )
        smooth_target += self.smoothing / n_classes
        loss = -(smooth_target * log_probs).sum(dim=1).mean()
        return loss


def _split_dataset(dataset, val_ratio: float, seed: int = 42):
    """按比例随机拆分训练/验证集索引，避免类别顺序偏差。"""
    n = len(dataset)
    indices = torch.randperm(n, generator=torch.Generator().manual_seed(seed)).tolist()
    n_val = max(1, int(n * val_ratio))
    n_train = n - n_val
    return indices[:n_train], indices[n_train:]


class _ValSubset(Subset):
    """验证集子集：与训练集共享 samples，但使用 VAL_TRANSFORMS 重新加载图片。"""

    def __getitem__(self, idx):
        real_idx = self.indices[idx]
        path, label = self.dataset.samples[real_idx]
        img = Image.open(path).convert("RGB")
        if VAL_TRANSFORMS is not None:
            img = VAL_TRANSFORMS(img)
        return img, label


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
            result = crop_dataset(
                train_dir, output_dir, max_images_per_role=MAX_IMAGES_PER_ROLE
            )
            if result["processed"] > 0:
                logger.info(
                    "YOLO 裁剪完成: 处理 %d 张, 跳过 %d 张, 失败 %d 张",
                    result["processed"], result["skipped"], result["failed"]
                )
            else:
                logger.info("YOLO 未裁剪新图片（可能已全部处理过）")
            train_dir = output_dir
            logger.info("使用 YOLO 裁剪后的数据集: %s", train_dir)
        except ImportError:
            logger.warning("YOLO 模块未安装 (ultralytics)，跳过裁剪步骤")
        except Exception as e:
            logger.error("YOLO 裁剪过程出错: %s", e)
    else:
        logger.info("使用数据集: %s", train_dir)

    device = get_device()

    try:
        # ========== 数据集加载（单一实例，保证标签一致性）==========
        full_dataset = IPRoleImageFolder(root=train_dir, transform=TRAIN_TRANSFORMS)
        class_names = full_dataset.classes
        NUM_CLASSES = len(class_names)
        logger.info(f"使用 {NUM_CLASSES} 个角色类别进行训练")

        # 拆分训练/验证集
        use_val = 0 < VAL_SPLIT_RATIO < 1.0 and len(full_dataset) >= 20
        if use_val:
            train_idx, val_idx = _split_dataset(full_dataset, VAL_SPLIT_RATIO)
            train_subset = Subset(full_dataset, train_idx)
            val_subset = _ValSubset(full_dataset, val_idx)
            train_loader = DataLoader(
                train_subset, batch_size=BATCH_SIZE, shuffle=True,
                num_workers=NUM_WORKERS
            )
            val_loader = DataLoader(
                val_subset, batch_size=BATCH_SIZE, shuffle=False,
                num_workers=NUM_WORKERS
            )
            logger.info("数据集拆分: 训练 %d 张, 验证 %d 张",
                        len(train_idx), len(val_idx))
        else:
            train_loader = DataLoader(
                full_dataset, batch_size=BATCH_SIZE, shuffle=True,
                num_workers=NUM_WORKERS
            )
            val_loader = None
            logger.info("使用全部 %d 张图片训练（无验证集）", len(full_dataset))

        # 模型定义
        model_handler = CharacterRecognitionModel(NUM_CLASSES)
        model = model_handler.get_model()

        criterion = LabelSmoothingCrossEntropy(smoothing=LABEL_SMOOTHING)
        optimizer = optim.Adam(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )

        # 学习率调度：预热 + 余弦退火至 FINE_TUNE_LR，之后固定微调
        warmup_epochs = min(5, NUM_EPOCHS)
        # 余弦阶段总轮数 = 从预热结束到 FINE_TUNE_EPOCH
        cos_epochs = max(1, FINE_TUNE_EPOCH - warmup_epochs)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=cos_epochs, eta_min=FINE_TUNE_LR
        )
        warmup_done = False

        logger.info("开始训练咯...")
        logger.info("配置: lr=%.0e → cosine %.0e → fine-tune %.0e | "
                     "weight_decay=%.0e | smooth=%.1f | batch=%d",
                     LEARNING_RATE, FINE_TUNE_LR, FINE_TUNE_LR,
                     WEIGHT_DECAY, LABEL_SMOOTHING, BATCH_SIZE)
        if EARLY_STOP_PATIENCE > 0:
            logger.info("早停: %d 轮无提升即停止", EARLY_STOP_PATIENCE)

        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(NUM_EPOCHS):
            # ===== 学习率调度 =====
            if epoch < warmup_epochs:
                factor = (epoch + 1) / warmup_epochs
                for pg in optimizer.param_groups:
                    pg["lr"] = LEARNING_RATE * factor
            elif epoch < FINE_TUNE_EPOCH:
                if not warmup_done:
                    for pg in optimizer.param_groups:
                        pg["lr"] = LEARNING_RATE
                    warmup_done = True
                scheduler.step()
            else:
                # 第 FINE_TUNE_EPOCH 轮后固定 FINE_TUNE_LR
                for pg in optimizer.param_groups:
                    pg["lr"] = FINE_TUNE_LR

            current_lr = optimizer.param_groups[0]["lr"]

            # ===== 训练 =====
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            from tqdm import tqdm

            loop = tqdm(train_loader, desc=f"第 {epoch+1}/{NUM_EPOCHS} 轮训练",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, "
                                    "{rate_fmt}{postfix}]")
            for inputs, labels in loop:
                try:
                    inputs, labels = inputs.to(device), labels.to(device)

                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    loss.backward()

                    if GRAD_CLIP_NORM > 0:
                        nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)

                    optimizer.step()

                    running_loss += loss.item()
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)

                    current_acc = correct / total if total > 0 else 0.0
                    loop.set_postfix(
                        loss=f"{running_loss/(loop.n+1):.4f}",
                        acc=f"{100.*current_acc:.2f}%",
                        lr=f"{current_lr:.0e}",
                    )
                except Exception as e:
                    logger.error(f"训练过程中出现错误: {str(e)}")
                    continue

            loop.close()
            epoch_train_acc = 100.0 * correct / total if total > 0 else 0.0
            epoch_loss = running_loss / len(train_loader) if len(train_loader) > 0 else 0.0

            # ===== 验证 =====
            if val_loader is not None:
                model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0
                val_loop = tqdm(val_loader, desc=f"第 {epoch+1}/{NUM_EPOCHS} 轮验证",
                                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                with torch.no_grad():
                    for inputs, labels in val_loop:
                        inputs, labels = inputs.to(device), labels.to(device)
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                        val_loss += loss.item()
                        _, preds = torch.max(outputs, 1)
                        val_correct += (preds == labels).sum().item()
                        val_total += labels.size(0)
                        val_loop.set_postfix(
                            loss=f"{val_loss/(val_loop.n+1):.4f}",
                            acc=f"{100.*val_correct/val_total:.2f}%" if val_total > 0 else "N/A",
                        )
                val_loop.close()
                val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0.0
                val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0.0
                metric = val_acc
                logger.info(
                    f"第 {epoch+1}/{NUM_EPOCHS} 轮 | loss={epoch_loss:.4f} | "
                    f"训练正确率: {epoch_train_acc:.2f}% | "
                    f"验证正确率: {val_acc:.2f}% | "
                    f"lr: {current_lr:.0e}"
                )
            else:
                metric = epoch_train_acc
                logger.info(
                    f"第 {epoch+1}/{NUM_EPOCHS} 轮 | loss={epoch_loss:.4f} | "
                    f"正确率: {epoch_train_acc:.2f}% | "
                    f"lr: {current_lr:.0e}"
                )

            # ===== 保存最佳模型 =====
            if metric > best_val_acc:
                best_val_acc = metric
                model_handler.save_model(MODEL_PATH)
                epochs_no_improve = 0
                logger.info(f"保存最佳模型 (验证正确率: {best_val_acc:.2f}%) → {str(MODEL_PATH)}")
                save_classes_to_file(CLASSES_TXT_PATH, class_names)
            else:
                epochs_no_improve += 1

            # ===== 早停 =====
            if EARLY_STOP_PATIENCE > 0 and epochs_no_improve >= EARLY_STOP_PATIENCE:
                logger.info(
                    "早停触发: %d 轮无提升，停止训练 (最佳验证正确率: %.2f%%)",
                    EARLY_STOP_PATIENCE, best_val_acc
                )
                break

        # 训练完成
        logger.info(f"训练完成！最佳验证正确率: {best_val_acc:.2f}%")
        logger.info(f"模型保存到: {str(MODEL_PATH)}")
        logger.info(f"类别名称已保存到: {str(CLASSES_TXT_PATH)}")

    except Exception as e:
        logger.error(f"训练过程中出现严重错误: {str(e)}", exc_info=True)
