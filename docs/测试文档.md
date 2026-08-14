# 测试文档

## 概述

本项目使用 **pytest** 作为测试框架，配合 `pytest-cov` 统计代码覆盖率。测试用例覆盖 CLI 模块和服务端模块的核心功能。

## 目录结构

```
tests/
├─ pytest.ini              # pytest 配置（含 --cov 覆盖率参数）
├─ conftest.py             # 全局 fixtures（临时目录、测试图片、模拟数据集等）
├─ requirements-test.txt   # 测试依赖
├─ cli/
│  ├─ conftest.py             # ✨ CLI 专用路径注入（src/cli + src）
│  ├─ test_config.py          # CLI 配置模块测试
│  ├─ test_file_utils.py      # 文件工具函数测试
│  ├─ test_image_utils.py     # 图片验证函数测试
│  ├─ test_validation_utils.py# 数据集验证函数测试
│  ├─ test_character_model.py # 角色识别模型测试
│  ├─ test_dataset.py         # 数据集加载测试
│  ├─ test_trainer.py         # 训练器模块测试
│  ├─ test_predictor.py       # 预测器模块测试
│  └─ test_log_config.py      # 日志配置测试
└─ server/
   ├─ conftest.py             # ✨ Server 专用路径注入（src/server + src）
   ├─ test_validators.py      # 表单验证器测试
   ├─ test_jwt_utils.py       # JWT 令牌工具测试
   ├─ test_password_service.py# 密码服务测试
   ├─ test_auth_service.py    # 认证服务测试
   ├─ test_user_service.py    # 用户服务测试
   ├─ test_api_key_service.py # API 密钥管理测试
   ├─ test_rate_limiter.py    # 限流中间件测试
   ├─ test_sse_bus.py         # SSE 事件总线测试
   └─ test_auth_middleware.py # 认证中间件测试
```

> ⚠️ **路径隔离**：CLI 与 Server 各自拥有独立的 `config` 包（`src/cli/config/` 与 `src/server/config/`），
> 不能在同一个 Python 进程中共存。因此测试路径注入按目录拆分：
> `tests/cli/conftest.py` 只注入 `src/cli + src`，`tests/server/conftest.py` 只注入 `src/server + src`（`src` 用于公共模块 `common`）。
> **必须分目录运行测试，不能一次 `pytest tests/`。**

## 安装与运行

### 1. 安装测试依赖

```bash
pip install -r tests/requirements-test.txt
```

### 2. 运行测试（分目录）

```bash
# CLI 模块测试（89 个）
pytest tests/cli/

# 服务端模块测试（94 个）
pytest tests/server/
```

### 3. 指定测试文件

```bash
pytest tests/cli/test_file_utils.py

# 带详细输出
pytest -v tests/cli/test_file_utils.py
```

### 4. 覆盖率报告

```bash
# 终端显示覆盖率
pytest --cov=src --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest --cov=src --cov-report=html
# 打开 htmlcov/index.html 查看
```

## 测试约定

### 命名规范

- 测试文件：`test_<模块名>.py`
- 测试类：`Test<功能名>`
- 测试方法：`test_<场景描述>`

### Fixtures 使用

`conftest.py` 提供以下全局 fixtures：

| Fixture | 类型 | 说明 |
|---------|------|------|
| `tmp_model_dir` | Path | 临时模型目录 |
| `tmp_log_dir` | Path | 临时日志目录 |
| `tmp_upload_dir` | Path | 临时上传目录 |
| `valid_png` | Path | 224x224 有效 PNG 图片 |
| `valid_jpg` | Path | 224x224 有效 JPEG 图片 |
| `invalid_file` | Path | 非图片文件（.txt） |
| `corrupted_image` | Path | 损坏的 PNG 文件 |
| `classes_file` | Path | 3 个类别的列表文件 |
| `empty_classes_file` | Path | 空类别文件 |
| `mock_dataset_dir` | Path | 模拟数据集（IP/角色两级结构，共 4 张图片） |

### 测试标记

| 标记 | 说明 |
|------|------|
| `@pytest.mark.slow` | 需要较长时间执行的测试（如模型训练） |
| `@pytest.mark.network` | 需要网络连接的测试 |
| `@pytest.mark.db` | 需要数据库连接的测试 |
| `@pytest.mark.gpu` | 需要 GPU 的测试 |

## 测试覆盖范围

### CLI 模块

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_config.py` | 环境变量读取、默认值、特性开关、节点配置、能力列表 |
| `test_file_utils.py` | MD5/SHA-256 哈希、目录创建、类别文件读写、模型文件检查 |
| `test_image_utils.py` | 有效/损坏/非图片文件验证、尺寸检查、色彩模式转换 |
| `test_validation_utils.py` | IP/角色两级目录结构遍历、隐藏目录跳过、无效图片检测 |
| `test_character_model.py` | 模型构建、前向传播、冻结/解冻、保存/加载、类别数变化兼容 |
| `test_dataset.py` | IPRoleImageFolder 的类别映射、样本索引、隐藏目录过滤 |
| `test_trainer.py` | 标签平滑损失、数据集拆分、模型备份、训练后分 IP 成功率统计、成功率表格构建、函数签名 |
| `test_predictor.py` | 参数校验、图片预处理、结果展示、模型缓存逻辑 |
| `test_log_config.py` | 日志级别、处理器配置、传播控制 |

### 服务端模块

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_validators.py` | 邮箱/用户名/密码格式验证 |
| `test_jwt_utils.py` | 令牌生成、解码、过期检测、篡改检测 |
| `test_password_service.py` | 哈希、验证、密码修改、弱密码拒绝 |
| `test_auth_service.py` | 注册/登录/令牌刷新、重复用户/禁用账号/令牌类型检查 |
| `test_user_service.py` | 用户查询、资料更新、列表分页 |
| `test_api_key_service.py` | 创建/查询/哈希、权限校验、密钥格式 |
| `test_rate_limiter.py` | 滑动窗口结构、禁用开关、装饰器封装、限流 429（独立实例防污染） |
| `test_sse_bus.py` | 订阅/发布/取消、多订阅者、超时处理、JSON 序列化 |
| `test_auth_middleware.py` | 令牌提取、登录/管理员装饰器、refresh token 拒绝、可选登录（Flask test_request_context） |

## 编写新的测试

### 1. 添加测试文件

在 `tests/cli/` 或 `tests/server/` 下创建 `test_<模块名>.py`。

### 2. 使用 conftest fixtures

```python
from pathlib import Path

def test_my_function(valid_png: Path, classes_file: Path):
    """使用 fixtures 测试"""
    result = my_function(str(valid_png), str(classes_file))
    assert result["success"] is True
```

### 3. Mock 外部依赖

```python
from unittest.mock import patch, MagicMock

@patch("my_module.get_connection")
def test_with_db(mock_get_conn):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": 1, "name": "test"}
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    result = my_function()
    assert result["success"] is True
```

### 4. 参数化测试

```python
@pytest.mark.parametrize("input_val,expected", [
    ("valid@example.com", True),
    ("invalid", False),
])
def test_validation(input_val, expected):
    assert validate(input_val) == expected
```

## 注意事项

- 测试不会连接真实数据库，数据库相关功能使用 `unittest.mock` 模拟
- 模型测试使用 `pretrained=False` 避免下载 ImageNet 预训练权重
- 图片相关的 fixture 在内存中生成，不依赖外部文件
- 耗时操作（如模型训练）使用 mock 验证而非实际执行
- 认证中间件测试使用 Flask `test_request_context` 提供请求上下文（Werkzeug 3.x 下无法直接 mock `flask.request`）
- 限流测试使用**独立限流器实例**（mock `_get_client_key`），避免污染全局单例
- 预测器测试中 `_classes_cache` 全局缓存可能跨用例污染，必要时在用例内重置为 `None`