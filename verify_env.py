#!/usr/bin/env python3
"""
验证Python环境是否正常工作
检查核心依赖包是否能够正常导入
"""

import sys


def check_package(package_name, import_name=None):
    """检查包是否能够正常导入"""
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        print(f"✓ {package_name} 导入成功")
        return True
    except ImportError as e:
        print(f"✗ {package_name} 导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠ {package_name} 导入时出现警告: {e}")
        return True


def check_python_version():
    """检查 Python 版本是否满足最低要求"""
    required = (3, 14)
    current = sys.version_info[:2]
    if current >= required:
        print(f"✓ Python 版本 {current[0]}.{current[1]} >= {required[0]}.{required[1]}，符合要求")
        return True
    else:
        print(f"✗ Python 版本 {current[0]}.{current[1]} < {required[0]}.{required[1]}，请升级")
        return False


def main():
    print("=" * 50)
    print("验证Python环境")
    print(f"Python版本: {sys.version}")
    print("=" * 50)

    version_ok = check_python_version()

    # 核心深度学习包
    print("\n1. 深度学习框架:")
    torch_ok = check_package("torch")
    torchvision_ok = check_package("torchvision")
    torchaudio_ok = check_package("torchaudio")

    # Web框架
    print("\n2. Web框架:")
    flask_ok = check_package("flask")
    flask_cors_ok = check_package("flask_cors")

    # 数据库
    print("\n3. 数据库:")
    pymysql_ok = check_package("pymysql", "pymysql")

    # 图像处理
    print("\n4. 图像处理:")
    pillow_ok = check_package("PIL", "PIL.Image")
    numpy_ok = check_package("numpy")

    # 系统监控（服务器特有）
    print("\n5. 系统工具:")
    psutil_ok = check_package("psutil")

    # 网络请求
    print("\n6. 网络请求:")
    requests_ok = check_package("requests")

    # 工具库
    print("\n7. 工具库:")
    tqdm_ok = check_package("tqdm")

    print("\n" + "=" * 50)
    print("环境验证完成")

    # 检查关键包
    critical_packages = [version_ok, torch_ok, flask_ok, pillow_ok, numpy_ok]
    if all(critical_packages):
        print("✅ 核心包全部正常，环境准备就绪！")
        return 0
    else:
        print("❌ 部分核心包导入失败，请检查依赖安装")
        return 1


if __name__ == "__main__":
    sys.exit(main())
