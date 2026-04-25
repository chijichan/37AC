# services/file_service.py
"""文件上传服务 - 提供文件上传相关的工具函数"""

import os
import uuid
from config import IMAGE_PATH


def save_uploaded_file(file):
    """保存上传的图片文件，返回保存路径"""
    if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".jfif")):
        filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
        filepath = os.path.join(str(IMAGE_PATH), filename)
        file.save(filepath)
        return filepath
    return None
