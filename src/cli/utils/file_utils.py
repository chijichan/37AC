# utils/file_utils.py
import os
import json
import hashlib
from config.log_config import get_logger

logger = get_logger(__name__)


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


def parse_class_name(class_name: str) -> tuple:
    """将类别名 "IP/角色" 拆分为 (所属IP, 角色名)。

    Args:
        class_name: 形如 "蔚蓝档案/一之濑明日奈" 的类别名

    Returns:
        (ip, role)：无 "/" 时 ip 为空字符串，role 为整个字符串
    """
    if not class_name:
        return "", ""
    if "/" in class_name:
        ip, role = class_name.split("/", 1)
        return ip.strip(), role.strip()
    return "", class_name.strip()


def _load_classes_from_json(file_path: str) -> list:
    """从 JSON 文件加载类别名（兼容 classes.json 规范格式）。

    支持两种结构：
      1. 规范格式（顶层对象）：
         { "IP/角色": {"id": "角色", "ip": "IP", "name_zh": "备用中文名"}, ... }
         返回 key 列表（即 "IP/角色"，保持写入顺序）。
      2. 宽松格式（顶层数组）：
         [ {"id","ip","name_zh"}, ... ] 或 [ "IP/角色", ... ]
         返回由每项拼出的 "IP/角色" 列表。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        # 规范格式：dict 键即 "IP/角色"（Python 3.7+ 保持插入顺序）
        keys = [k for k in data.keys() if k and isinstance(k, str)]
        return keys

    if isinstance(data, list):
        class_names = []
        for item in data:
            if isinstance(item, dict):
                ip = str(item.get("ip", "") or "")
                rid = str(item.get("id", "") or "")
                if ip and rid:
                    class_names.append(f"{ip}/{rid}")
                else:
                    class_names.append(rid or ip)
            elif isinstance(item, str) and item:
                class_names.append(item)
        return class_names

    return []


def load_classes_from_file(file_path: str) -> list:
    """从 classes.json 加载类别列表。

    仅支持 `.json` 格式（规范顶层对象或宽松数组结构），
    详见 _load_classes_from_json。返回的始终是类别名列表（"IP/角色"），
    供训练 / 预测使用。
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"类别文件不存在: {file_path}")
            return []

        if not os.access(file_path, os.R_OK):
            logger.error(f"类别文件不可读: {file_path}")
            return []

        if os.path.splitext(file_path)[1].lower() != ".json":
            logger.error(f"不支持的类别文件格式（仅支持 classes.json）: {file_path}")
            return []

        class_names = _load_classes_from_json(file_path)

        if not class_names:
            logger.error(f"类别文件为空或格式不正确: {file_path}")
            return []

        logger.info(f"从文件加载到 {len(class_names)} 个角色类别")
        return class_names
    except Exception as e:
        logger.error(f"加载类别文件失败 {file_path}: {str(e)}")
        return []


def classes_to_json_dict(class_names: list) -> dict:
    """将类别名列表转换为规范结构的 JSON 字典。

    规范格式：{ "IP/角色": {"id": 角色名, "ip": 所属IP, "name_zh": 备用中文名}, ... }
    返回的 dict 保持 class_names 的原始顺序（Python 3.7+ 字典保序）。
    """
    data = {}
    for name in class_names:
        name = name.strip()
        if not name:
            continue
        ip, role = parse_class_name(name)
        # name_zh 作为备用展示名，默认与角色名一致，可由外部自行覆盖
        data[name] = {"id": role, "ip": ip, "name_zh": role}
    return data


def save_classes_to_json(file_path: str, class_names: list) -> bool:
    """保存类别列表为规范结构的 JSON 文件（{IP/角色: {id, ip, name_zh}}）"""
    try:
        ensure_directory_exists(os.path.dirname(file_path))
        data = classes_to_json_dict(class_names)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"类别信息已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存类别 JSON 失败 {file_path}: {str(e)}")
        return False


def check_model_file(file_path: str) -> bool:
    """检查模型文件是否存在且可读（必须是文件，目录不算）"""
    if not os.path.exists(file_path):
        logger.error("模型文件不存在: %s", file_path)
        return False
    if not os.path.isfile(file_path):
        logger.error("模型路径不是文件: %s", file_path)
        return False
    if not os.access(file_path, os.R_OK):
        logger.error("模型文件不可读: %s", file_path)
        return False
    return True
