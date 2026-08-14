"""测试文件工具模块"""

import os
from pathlib import Path

import pytest

from utils.file_utils import (
    calculate_file_hash,
    ensure_directory_exists,
    load_classes_from_file,
    load_classes_json_data,
    load_classes_registry,
    save_classes_to_json,
    classes_to_json_dict,
    parse_class_name,
    check_model_file,
)


class TestCalculateFileHash:
    """测试文件哈希计算"""

    def test_md5_hash(self, tmp_path: Path):
        """测试 MD5 哈希计算"""
        file = tmp_path / "test.txt"
        file.write_text("hello world", encoding="utf-8")
        hash_val = calculate_file_hash(str(file), "md5")
        assert hash_val == "5eb63bbbe01eeed093cb22bb8f5acdc3"

    def test_sha256_hash(self, tmp_path: Path):
        """测试 SHA-256 哈希计算"""
        file = tmp_path / "test.txt"
        file.write_text("hello world", encoding="utf-8")
        hash_val = calculate_file_hash(str(file), "sha256")
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert hash_val == expected

    def test_empty_file(self, tmp_path: Path):
        """测试空文件哈希"""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")
        hash_val = calculate_file_hash(str(file), "md5")
        assert hash_val == "d41d8cd98f00b204e9800998ecf8427e"

    def test_nonexistent_file(self):
        """测试不存在的文件"""
        hash_val = calculate_file_hash(r"C:\nonexistent\file.txt")
        assert hash_val == ""


class TestEnsureDirectoryExists:
    """测试目录创建"""

    def test_create_new_dir(self, tmp_path: Path):
        """测试创建新目录"""
        new_dir = tmp_path / "new_dir" / "sub_dir"
        assert ensure_directory_exists(str(new_dir)) is True
        assert new_dir.exists()

    def test_existing_dir(self, tmp_path: Path):
        """测试已存在的目录"""
        assert ensure_directory_exists(str(tmp_path)) is True

    def test_invalid_path(self):
        """测试无效路径"""
        # 使用非法字符
        assert ensure_directory_exists("") is False


class TestLoadClassesFromFile:
    """测试从文件加载类别"""

    def test_load_valid(self, classes_file: Path):
        """测试正常加载"""
        classes = load_classes_from_file(str(classes_file))
        assert len(classes) == 3
        assert classes == ["原神/荧", "原神/空", "蔚蓝档案/白子"]

    def test_load_empty(self, empty_classes_file: Path):
        """测试空文件"""
        classes = load_classes_from_file(str(empty_classes_file))
        assert classes == []

    def test_nonexistent_file(self):
        """测试文件不存在"""
        classes = load_classes_from_file(r"C:\nonexistent\classes.json")
        assert classes == []

    def test_rejects_txt_file(self, tmp_path: Path):
        """测试不再支持 classes.txt（仅支持 classes.json）"""
        file = tmp_path / "classes.txt"
        file.write_text("角色A\n角色B\n", encoding="utf-8")
        classes = load_classes_from_file(str(file))
        assert classes == []

    def test_load_json_spec_format(self, tmp_path: Path):
        """测试加载规范格式 classes.json（顶层对象）"""
        import json as _json
        file = tmp_path / "classes.json"
        data = {
            "蔚蓝档案/白子": {"id": "白子", "ip": "蔚蓝档案", "name_zh": "白子"},
            "原神/荧": {"id": "荧", "ip": "原神", "name_zh": "荧"},
        }
        file.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
        classes = load_classes_from_file(str(file))
        assert classes == ["蔚蓝档案/白子", "原神/荧"]

    def test_load_json_list_format(self, tmp_path: Path):
        """测试加载宽松数组格式 classes.json（兼容）"""
        import json as _json
        file = tmp_path / "classes.json"
        data = [
            {"id": "白子", "ip": "蔚蓝档案", "name_zh": "白子"},
            {"id": "荧", "ip": "原神", "name_zh": "荧"},
        ]
        file.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
        classes = load_classes_from_file(str(file))
        assert classes == ["蔚蓝档案/白子", "原神/荧"]

    def test_parse_class_name(self):
        """测试类别名拆分"""
        assert parse_class_name("蔚蓝档案/白子") == ("蔚蓝档案", "白子")
        assert parse_class_name("初音未来") == ("", "初音未来")

    def test_classes_to_json_dict(self):
        """测试类别列表转规范 JSON 字典"""
        data = classes_to_json_dict(["蔚蓝档案/白子", "原神/荧"])
        assert data == {
            "蔚蓝档案/白子": {"id": "白子", "ip": "蔚蓝档案", "name_zh": "白子"},
            "原神/荧": {"id": "荧", "ip": "原神", "name_zh": "荧"},
        }

    def test_classes_to_json_dict_with_profiles(self):
        """测试带 features_used / tags 的角色档案写入"""
        data = classes_to_json_dict(
            ["Piapro_Characters/初音未来", "蔚蓝档案/白子"],
            profiles={
                "Piapro_Characters/初音未来": {
                    "features_used": ["青色头发", "双马尾"],
                    "tags": ["长发", "绿发", "金瞳", "女性角色", "偶像风", "连衣裙"],
                },
            },
        )
        entry = data["Piapro_Characters/初音未来"]
        assert entry["features_used"] == ["青色头发", "双马尾"]
        assert entry["tags"] == ["长发", "绿发", "金瞳", "女性角色", "偶像风", "连衣裙"]
        # 未提供档案的角色不包含 features_used / tags
        assert "features_used" not in data["蔚蓝档案/白子"]
        assert "tags" not in data["蔚蓝档案/白子"]


class TestSaveClassesToJson:
    """测试保存类别到 classes.json"""

    def test_save_json_and_load(self, tmp_path: Path):
        """测试保存 classes.json 后可正确加载"""
        file = tmp_path / "classes.json"
        classes = ["原神/荧", "原神/空"]
        assert save_classes_to_json(str(file), classes) is True
        assert load_classes_from_file(str(file)) == classes

    def test_save_json_with_profiles_and_load_meta(self, tmp_path: Path):
        """测试保存带 features_used / tags 的 classes.json，且可加载元数据"""
        file = tmp_path / "classes.json"
        classes = ["Piapro_Characters/初音未来"]
        profiles = {
            "Piapro_Characters/初音未来": {
                "features_used": ["青色头发", "双马尾"],
                "tags": ["长发", "女性角色"],
            },
        }
        assert save_classes_to_json(str(file), classes, profiles=profiles) is True
        data = load_classes_json_data(str(file))
        assert data["Piapro_Characters/初音未来"]["features_used"] == ["青色头发", "双马尾"]
        assert data["Piapro_Characters/初音未来"]["tags"] == ["长发", "女性角色"]

    def test_load_classes_json_data_missing_file(self):
        """测试加载不存在的 classes.json 返回空 dict"""
        assert load_classes_json_data(r"C:\nonexistent\classes.json") == {}

    def test_load_classes_registry(self, tmp_path: Path):
        """测试加载完整角色类别注册表（类别名 = 整个对象）"""
        import json as _json

        file = tmp_path / "classes.json"
        data = {
            "蔚蓝档案/黑见茜香": {
                "id": "黑见茜香", "ip": "蔚蓝档案", "name_zh": "黑见茜香",
                "features_used": ["银发", "编发", "制服"],
                "tags": ["银发", "编发", "女性角色"],
            },
        }
        file.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")

        registry = load_classes_registry(str(file))
        assert len(registry) == 1
        entry = registry[0]
        assert entry["key"] == "蔚蓝档案/黑见茜香"
        assert entry["id"] == "黑见茜香"
        assert entry["ip"] == "蔚蓝档案"
        assert entry["features_used"] == ["银发", "编发", "制服"]
        assert entry["tags"] == ["银发", "编发", "女性角色"]


class TestCheckModelFile:
    """测试模型文件检查"""

    def test_file_exists(self, tmp_path: Path):
        """测试存在的文件"""
        file = tmp_path / "model.pth"
        file.write_text("dummy", encoding="utf-8")
        assert check_model_file(str(file)) is True

    def test_file_not_exists(self):
        """测试不存在的文件"""
        assert check_model_file(r"C:\nonexistent\model.pth") is False

    def test_directory_not_file(self, tmp_path: Path):
        """测试传入目录路径"""
        assert check_model_file(str(tmp_path)) is False