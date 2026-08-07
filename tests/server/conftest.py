"""Server 测试专用配置：注入 src/server 与 src（公共模块）路径"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

for p in [_ROOT / "src" / "server", _ROOT / "src"]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
