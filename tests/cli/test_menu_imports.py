"""长任务函数里的关键 import 防回归。

背景：给 compress_dataset_function 加按键监听时误删了
from utils.image_utils import compress_dataset_images，
py_compile 查不出来（运行时才 NameError），跑菜单才炸。
这里用源码检查把这类"用了但没导入"的退化锁住。
"""

from pathlib import Path

from services import menu_service

SRC = Path(menu_service.__file__).read_text(encoding="utf-8")

CASES = [
    ("def compress_dataset_function", "compress_dataset_images"),
    ("def convert_dataset_jpeg_function", "convert_dataset_to_jpeg"),
    ("def crop_dataset_function", "crop_dataset"),
]


def test_long_task_functions_keep_their_imports():
    for marker, symbol in CASES:
        start = SRC.index(marker)
        # 取该函数体（到下一个顶层 def 为止）
        nxt = SRC.find("\ndef ", start + 1)
        body = SRC[start:nxt if nxt != -1 else len(SRC)]
        assert symbol in body, "%s 里缺少 %s（import 被误删？）" % (marker, symbol)
        assert "import %s" % symbol in body or "import (" in body, \
            "%s 里没有 import %s 的语句" % (marker, symbol)
