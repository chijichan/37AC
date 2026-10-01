# -*- coding: utf-8 -*-
"""统一的交互输入：ESC / Ctrl+Z = 返回上级菜单；Ctrl+C = 结束程序。

约定（全局一致）：
- ESC（\x1b）或 Ctrl+Z（\x1a）：返回**上一级**菜单
- 直接回车（空输入）：等同 ESC（Windows 的 cmd 里按 ESC 往往是清空当前行）
- Ctrl+C：结束程序（不再只是返回上级）
- Ctrl+Z 在部分终端会触发 EOFError，同样按"返回上级"处理

所有菜单/提示都用这里的 read_line / ask，别再直接用 input()。
"""

import threading
import time

ESC = "\x1b"                          # ESC
CTRL_Z = "\x1a"                       # Ctrl+Z
CTRL_C = "\x03"                       # Ctrl+C
BACK_KEYS = (ESC, CTRL_Z)              # 返回上级菜单的按键
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


class KeyWatcher:
    """长任务（训练/裁剪/压缩）期间的后台按键监听。

    - ESC / Ctrl+Z → 置位 back_requested（任务应尽快停下，**返回上级菜单**）
    - Ctrl+C       → 置位 exit_requested（结束程序）

    用法：
        watcher = KeyWatcher()
        watcher.on_back = token.cancel      # 通知任务取消
        watcher.start()
        try:
            run_long_task()
        finally:
            watcher.stop()
    """

    def __init__(self, poll_interval: float = 0.05):
        self._stop = threading.Event()
        self._thread = None
        self._poll = max(0.01, float(poll_interval))
        self.back_requested = False
        self.exit_requested = False
        self.on_back = None
        self.on_exit = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self.back_requested = False
        self.exit_requested = False
        self._thread = threading.Thread(target=self._run, name="key-watcher", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def _request_back(self):
        if not self.back_requested:
            self.back_requested = True
            if callable(self.on_back):
                try:
                    self.on_back()
                except Exception:
                    pass

    def _request_exit(self):
        if not self.exit_requested:
            self.exit_requested = True
            if callable(self.on_exit):
                try:
                    self.on_exit()
                except Exception:
                    pass

    def handle_key(self, ch: str) -> bool:
        """处理一个按键字符；返回 True 表示已识别为控制键。"""
        if ch in (ESC, CTRL_Z):
            self._request_back()
            return True
        if ch == CTRL_C:
            self._request_exit()
            return True
        return False

    def _run(self):
        try:
            import msvcrt  # Windows：非阻塞读键，无需回车
        except ImportError:
            msvcrt = None

        while not self._stop.is_set():
            ch = ""
            try:
                if msvcrt is not None:
                    if not msvcrt.kbhit():
                        time.sleep(self._poll)
                        continue
                    ch = msvcrt.getwch()
                else:
                    import sys as _sys
                    if not (_sys.stdin and _sys.stdin.isatty()):
                        return
                    ch = _sys.stdin.read(1)
                    if not ch:
                        time.sleep(self._poll)
                        continue
            except Exception:
                return
            if not ch:
                continue
            if ch in ("\x00", "\xe0"):      # 方向键等功能键的前导字符：吃掉后续字节
                try:
                    if msvcrt is not None and msvcrt.kbhit():
                        msvcrt.getwch()
                except Exception:
                    pass
                continue
            self.handle_key(ch)



def wait_enter(prompt: str = "按回车返回上级菜单…") -> None:
    """暂停等待用户按键；ESC/Ctrl+Z 也当作继续（不抛异常）。"""
    try:
        read_line(prompt, blank_means_back=False)
    except GoBack:
        pass
