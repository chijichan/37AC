# -*- coding: utf-8 -*-
"""统一的交互输入：ESC / Ctrl+Z = 返回上级菜单；Ctrl+C = 结束程序。

约定（全局一致）：
- ESC（\x1b）或 Ctrl+Z（\x1a）：返回**上一级**菜单
- 直接回车（空输入）：等同 ESC（Windows 的 cmd 里按 ESC 往往是清空当前行）
- Ctrl+C：结束程序（不再只是返回上级）
- Ctrl+Z 在部分终端会触发 EOFError，同样按"返回上级"处理

所有菜单/提示都用这里的 read_line / ask，别再直接用 input()。
"""

BACK_KEYS = ("\x1b", "\x1a")          # ESC、Ctrl+Z
CTRL_C = "\x03"
HINT = "（ESC/Ctrl+Z 返回上级，Ctrl+C 结束程序）"


class GoBack(Exception):
    """用户按了 ESC / Ctrl+Z（或空输入）：返回上一级菜单。"""


class ExitProgram(Exception):
    """用户按了 Ctrl+C：结束程序。"""


def _strip_control(text: str) -> str:
    cleaned = text or ""
    for ch in BACK_KEYS + (CTRL_C,):
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


def read_line(prompt: str, blank_means_back: bool = True) -> str:
    """读取一行输入并统一处理控制键。

    Returns:
        str: 去掉控制字符后的非空输入

    Raises:
        GoBack: ESC / Ctrl+Z / 空输入 / EOF
        ExitProgram: Ctrl+C
    """
    try:
        raw = input(prompt)
    except KeyboardInterrupt:
        raise ExitProgram() from None
    except EOFError:
        raise GoBack() from None

    text = _strip_control(raw)
    if not text and blank_means_back:
        raise GoBack()
    return text


def ask(prompt: str, valid=None, invalid_tip: str = "无效选择",
        blank_means_back: bool = True) -> str:
    """循环询问直到拿到合法选择；ESC/Ctrl+Z 抛 GoBack，Ctrl+C 抛 ExitProgram。"""
    while True:
        text = read_line(prompt, blank_means_back=blank_means_back)
        if not valid or text in valid:
            return text
        tip = f"{invalid_tip}，请输入 {'/'.join(valid)}"
        print(f"{tip} {HINT}")


def wait_enter(prompt: str = "按回车返回上级菜单…") -> None:
    """暂停等待用户按键；ESC/Ctrl+Z 也当作继续（不抛异常）。"""
    try:
        read_line(prompt, blank_means_back=False)
    except GoBack:
        pass
