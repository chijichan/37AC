# utils/file_utils.py
import os
import hashlib
import logging

logger = logging.getLogger(__name__)


def calculate_file_hash(
    file_path: str, hash_algorithm: str = "md5", buffer_size: int = 65536
) -> str:
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
        return ""


def ensure_directory_exists(dir_path: str) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {dir_path}: {str(e)}")
        return False


def load_classes_from_file(file_path: str) -> list:
    """从文件加载类别列表"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"类别文件不存在: {file_path}")
            return []

        if not os.access(file_path, os.R_OK):
            logger.error(f"类别文件不可读: {file_path}")
            return []

        CLASS_NAMES = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 忽略空行
                    CLASS_NAMES.append(line)

        if not CLASS_NAMES:
            logger.error(f"类别文件为空或格式不正确: {file_path}")
            return []

        logger.info(f"从文件加载到 {len(CLASS_NAMES)} 个角色类别")
        return CLASS_NAMES
    except Exception as e:
        logger.error(f"加载类别文件失败 {file_path}: {str(e)}")
        return []


def save_classes_to_file(file_path: str, class_names: list) -> bool:
    """保存类别列表到文件"""
    try:
        from config import CLASSES_TXT_PATH

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
