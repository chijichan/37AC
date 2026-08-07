# training/trainer.py
import os
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

# ==================== 继续训练辅助函数 ====================

def _backup_old_model(model_path, bak_dir):
    """将旧模型权重备份到备份目录，避免覆盖后无法回退。

    Args:
        model_path (Path): 当前模型权重路径
        bak_dir (Path): 备份目录路径
    """
    import shutil
    from datetime import datetime

    if not model_path.exists():
        logger.info("没有旧模型需要备份（%s 不存在）", model_path)
        return

    bak_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_name = f"{model_path.stem}_bak_{timestamp}{model_path.suffix}"
    bak_path = bak_dir / bak_name

    shutil.copy2(str(model_path), str(bak_path))
    logger.info("旧模型已备份 → %s", bak_path)

    # 同时备份 classes.txt
    classes_txt = model_path.parent / "classes.txt"
    if classes_txt.exists():
        bak_classes = bak_dir / f"classes_bak_{timestamp}.txt"
        shutil.copy2(str(classes_txt), str(bak_classes))
        logger.info("旧 classes.txt 已备份 → %s", bak_classes)

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
    n_val = max(1, min(int(n * val_ratio), n - 1))  # 至少留 1 个训练样本
    n_train = n - n_val
    return indices[:n_train], indices[n_train:]


class _ValSubset(Subset):
    """验证集子集：与训练集共享 samples，但使用 VAL_TRANSFORMS 重新加载图片。"""

    def __getitem__(self, idx):
        real_idx = self.indices[idx]
        path, label = self.dataset.samples[real_idx]
        with Image.open(path) as img:
            img = img.convert("RGB")
            if VAL_TRANSFORMS is not None:
                img = VAL_TRANSFORMS(img)
        return img, label

    def __getitems__(self, indices):
        """PyTorch 新版要求 Subset 子类重写 __getitem__ 时必须同时重写 __getitems__。"""
        return [self.__getitem__(idx) for idx in indices]


def train_model(dataset_dir=None, use_yolo_crop=False, resume_model=None):
    """训练模型

    Args:
        dataset_dir (str, optional): 数据集目录路径
        use_yolo_crop (bool): 是否使用 YOLO 裁剪
        resume_model (str or Path, optional): 已有模型权重路径，用于继续训练而非从头开始
    """
    # 中断标记：首次 Ctrl+C 安全保存，再次强制退出
    training_interrupted = False

    # 确定训练用数据集目录
    train_dir = dataset_dir or str(DATASET_DIR)

    # 检查数据集目录
    if not os.path.exists(train_dir):
        logger.error("数据集目录不存在: %s", train_dir)
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

        # ======================
        # === 模型定义 ===
        # ======================
        # 判断是否从已有模型权重继续训练
        resume_path = resume_model or RESUME_MODEL_PATH
        if resume_path is not None and os.path.exists(str(resume_path)):
            logger.info("=" * 50)
            logger.info("检测到已有模型权重: %s", resume_path)
            logger.info("将从已有权重继续训练（跳过阶段1冻结，直接全局精调）")

            # 备份旧模型（训练开始前备份，防止训练中途失败导致丢失）
            _backup_old_model(MODEL_PATH, MODEL_BAK_DIR)

            # 加载已有模型权重
            model_handler = CharacterRecognitionModel(NUM_CLASSES, pretrained=False)
            model = model_handler.load_model(str(resume_path), NUM_CLASSES)

            # 继续训练模式：跳过阶段1，直接进入阶段2全局精调
            skip_phase1 = True
            logger.info("继续训练模式: 跳过阶段1（冻结backbone），直接全局精调")
        else:
            if resume_path is not None:
                logger.warning("指定的继续训练权重不存在: %s，将使用 ImageNet 预训练", resume_path)
            # 从头训练：使用 ImageNet 预训练权重
            model_handler = CharacterRecognitionModel(NUM_CLASSES, pretrained=True)
            model = model_handler.get_model()
            skip_phase1 = False
            logger.info("使用 torchvision.models.resnet18(weights=IMAGENET1K_V1)")

        criterion = LabelSmoothingCrossEntropy(smoothing=LABEL_SMOOTHING)
        logger.info("配置: smooth=%.1f | batch=%d | weight_decay=%.0e",
                     LABEL_SMOOTHING, BATCH_SIZE, WEIGHT_DECAY)
        if EARLY_STOP_PATIENCE > 0:
            logger.info("早停: %d 轮无提升即停止", EARLY_STOP_PATIENCE)

        best_val_acc = 0.0
        epochs_no_improve = 0
        total_epoch = 0

        # ======================
        # === 阶段1: 冻结 backbone，仅训练 FC + CBAM ===
        # ======================
        # 继续训练模式跳过阶段1，因为模型已经训练过
        if not skip_phase1 and PHASE1_EPOCHS > 0:
            model_handler.freeze_backbone()
            # 阶段1 优化器 — 只更新 requires_grad=True 的参数
            phase1_optimizer = optim.Adam(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=PHASE1_LR, weight_decay=WEIGHT_DECAY
            )
            logger.info("=" * 50)
            logger.info("阶段1: 冻结 backbone，仅训练 FC + CBAM (%d 轮, lr=%.0e)",
                         PHASE1_EPOCHS, PHASE1_LR)

            for epoch in range(PHASE1_EPOCHS):
                if training_interrupted:
                    break
                total_epoch += 1
                model.train()
                running_loss = 0.0
                correct = 0
                total = 0

                from tqdm import tqdm
                loop = tqdm(train_loader, desc=f"P1 训练 {epoch+1}/{PHASE1_EPOCHS}",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, "
                                        "{rate_fmt}{postfix}]")
                for batch_idx, (inputs, labels) in enumerate(loop):
                    try:
                        inputs, labels = inputs.to(device), labels.to(device)
                        phase1_optimizer.zero_grad()
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                        loss.backward()
                        if GRAD_CLIP_NORM > 0:
                            nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)
                        phase1_optimizer.step()
                        running_loss += loss.item()
                        _, preds = torch.max(outputs, 1)
                        correct += (preds == labels).sum().item()
                        total += labels.size(0)
                        loop.set_postfix(
                            loss=f"{running_loss/(loop.n+1):.4f}",
                            acc=f"{100.*correct/total:.2f}%" if total > 0 else "N/A",
                            lr=f"{PHASE1_LR:.0e}",
                        )
                    except Exception:
                        logger.exception("阶段1训练错误, epoch=%d, batch=%d", epoch + 1, batch_idx)
                        continue

                loop.close()
                epoch_train_acc = 100.0 * correct / total if total > 0 else 0.0
                epoch_loss = running_loss / len(train_loader) if len(train_loader) > 0 else 0.0

                if val_loader is not None:
                    model.eval()
                    val_correct = 0; val_total = 0
                    val_loop = tqdm(val_loader, desc=f"P1 验证 {epoch+1}/{PHASE1_EPOCHS}",
                                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                    with torch.no_grad():
                        for inputs, labels in val_loop:
                            inputs, labels = inputs.to(device), labels.to(device)
                            outputs = model(inputs)
                            _, preds = torch.max(outputs, 1)
                            val_correct += (preds == labels).sum().item()
                            val_total += labels.size(0)
                    val_loop.close()
                    val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0.0
                else:
                    val_acc = epoch_train_acc

                logger.info("P1 第 %d/%d 轮 | loss=%.4f | train=%.2f%% | val=%.2f%%",
                             epoch + 1, PHASE1_EPOCHS, epoch_loss, epoch_train_acc, val_acc)

                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    model_handler.save_model(MODEL_PATH)
                    epochs_no_improve = 0
                    logger.info("保存最佳模型 (正确率: %.2f%%) → %s", best_val_acc, str(MODEL_PATH))
                    save_classes_to_file(CLASSES_TXT_PATH, class_names)
                elif EARLY_STOP_PATIENCE > 0:
                    epochs_no_improve += 1
        else:
            logger.info("跳过阶段1（冻结backbone训练）")

        # ======================
        # === 阶段2: 解冻全部，余弦退火全局精调 ===
        # ======================
        model_handler.unfreeze_all()
        phase2_epochs = NUM_EPOCHS - (PHASE1_EPOCHS if not skip_phase1 else 0)
        if phase2_epochs <= 0:
            phase2_epochs = NUM_EPOCHS
        phase2_optimizer = optim.Adam(
            model.parameters(), lr=PHASE2_LR, weight_decay=WEIGHT_DECAY
        )
        phase2_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            phase2_optimizer, T_max=phase2_epochs, eta_min=PHASE2_MIN_LR
        )

        logger.info("=" * 50)
        logger.info("阶段2: 解冻全部，全局精调 (%d 轮, lr=%.0e → %.0e)",
                     phase2_epochs, PHASE2_LR, PHASE2_MIN_LR)

        for epoch in range(phase2_epochs):
            if training_interrupted:
                break
            total_epoch += 1
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0
            current_lr = phase2_optimizer.param_groups[0]["lr"]

            from tqdm import tqdm
            loop = tqdm(train_loader, desc=f"P2 训练 {epoch+1}/{phase2_epochs}",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, "
                                    "{rate_fmt}{postfix}]")
            for batch_idx, (inputs, labels) in enumerate(loop):
                try:
                    inputs, labels = inputs.to(device), labels.to(device)
                    phase2_optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    if GRAD_CLIP_NORM > 0:
                        nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)
                    phase2_optimizer.step()
                    running_loss += loss.item()
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)
                    loop.set_postfix(
                        loss=f"{running_loss/(loop.n+1):.4f}",
                        acc=f"{100.*correct/total:.2f}%" if total > 0 else "N/A",
                        lr=f"{current_lr:.0e}",
                    )
                except Exception:
                    logger.exception("阶段2训练错误, epoch=%d, batch=%d", epoch + 1, batch_idx)
                    continue

            loop.close()
            phase2_scheduler.step()
            current_lr = phase2_optimizer.param_groups[0]["lr"]
            epoch_train_acc = 100.0 * correct / total if total > 0 else 0.0
            epoch_loss = running_loss / len(train_loader) if len(train_loader) > 0 else 0.0

            if val_loader is not None:
                model.eval()
                val_correct = 0; val_total = 0
                val_loop = tqdm(val_loader, desc=f"P2 验证 {epoch+1}/{phase2_epochs}",
                                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                with torch.no_grad():
                    for inputs, labels in val_loop:
                        inputs, labels = inputs.to(device), labels.to(device)
                        outputs = model(inputs)
                        _, preds = torch.max(outputs, 1)
                        val_correct += (preds == labels).sum().item()
                        val_total += labels.size(0)
                val_loop.close()
                val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0.0
            else:
                val_acc = epoch_train_acc

            logger.info("P2 第 %d/%d 轮 | loss=%.4f | train=%.2f%% | val=%.2f%% | lr=%.0e",
                         epoch + 1, phase2_epochs, epoch_loss, epoch_train_acc, val_acc, current_lr)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                model_handler.save_model(MODEL_PATH)
                epochs_no_improve = 0
                logger.info("保存最佳模型 (正确率: %.2f%%) → %s", best_val_acc, str(MODEL_PATH))
                save_classes_to_file(CLASSES_TXT_PATH, class_names)
            elif EARLY_STOP_PATIENCE > 0:
                epochs_no_improve += 1
                if epochs_no_improve >= EARLY_STOP_PATIENCE:
                    logger.info("早停触发: %d 轮无提升 (最佳: %.2f%%)", EARLY_STOP_PATIENCE, best_val_acc)
                    break

        # 训练完成
        logger.info("=" * 50)
        logger.info(f"训练完成！最佳验证正确率: {best_val_acc:.2f}%")
        logger.info(f"模型保存到: {str(MODEL_PATH)}")
        logger.info(f"类别名称已保存到: {str(CLASSES_TXT_PATH)}")

    except KeyboardInterrupt:
        logger.warning("\n" + "=" * 50)
        logger.warning("训练被用户中断，正在保存当前模型...")
        try:
            if 'model_handler' in dir() and 'class_names' in dir() and class_names:
                model_handler.save_model(MODEL_PATH)
                save_classes_to_file(CLASSES_TXT_PATH, class_names)
                logger.warning("已保存当前模型至: %s (正确率: %.2f%%)", str(MODEL_PATH), best_val_acc)
            else:
                logger.warning("模型尚未初始化，无需保存")
        except Exception as save_err:
            logger.error("保存模型失败: %s", save_err)
        logger.warning("训练中断，当前模型已保存，下次可使用继续训练功能")
    except Exception as e:
        logger.error(f"训练过程中出现严重错误: {str(e)}", exc_info=True)
