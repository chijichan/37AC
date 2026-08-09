# data/dataset.py
import os
from PIL import ImageFile
from torchvision import datasets

ImageFile.LOAD_TRUNCATED_IMAGES = True

# torchvision 支持的图片扩展名
_VALID_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".pgm", ".tif", ".tiff", ".webp"}
)


def _has_valid_image(folder: str) -> bool:
    """判断一个文件夹中是否至少存在一张有效（可被读取）的图片。"""
    try:
        entries = os.listdir(folder)
    except OSError:
        return False
    for name in entries:
        ext = os.path.splitext(name)[1].lower()
        if ext in _VALID_EXTENSIONS:
            return True
    return False


class IPRoleImageFolder(datasets.ImageFolder):
    def find_classes(self, directory: str):
        """
        重写 find_classes 方法，将目录结构 IP/角色 映射为类别名 "IP/角色"。

        仅收录至少包含一张图片的角色文件夹，自动跳过空角色文件夹，
        避免 torchvision 因空类别目录抛出 FileNotFoundError。
        """
        from config.log_config import get_logger

        logger = get_logger(__name__)

        ip_names = sorted(
            [
                d
                for d in os.listdir(directory)
                if os.path.isdir(os.path.join(directory, d)) and not d.startswith(".")
            ]
        )
        class_names = []
        class_to_idx = {}
        skipped = []

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
                role_path = os.path.join(ip_path, role_name)
                class_name = f"{ip_name}/{role_name}"  # 格式: IP/角色
                if not _has_valid_image(role_path):
                    # 跳过没有任何有效图片的角色文件夹
                    skipped.append(class_name)
                    continue
                class_names.append(class_name)
                class_to_idx[class_name] = len(class_to_idx)

        if skipped:
            logger.warning(
                "以下 %d 个角色文件夹无有效图片，已自动跳过: %s",
                len(skipped), ", ".join(skipped),
            )
        logger.info(f"自动生成 {len(class_names)} 个类别（格式: IP/角色）")
        return class_names, class_to_idx
