# data/dataset.py
import os
from torchvision import datasets


class IPRoleImageFolder(datasets.ImageFolder):
    def find_classes(self, directory: str):
        """
        重写 find_classes 方法，将目录结构 IP/角色 映射为类别名 "IP/角色"
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
                class_name = f"{ip_name}/{role_name}"  # 格式: IP/角色
                class_names.append(class_name)
                class_to_idx[class_name] = len(class_to_idx)

        from config.base import DATASET_DIR
        from config.log_config import get_logger

        logger = get_logger(__name__)
        logger.info(f"自动生成 {len(class_names)} 个类别（格式: IP/角色）")
        return class_names, class_to_idx
