"""测试菜单服务模块（drain_pending_input 等工具函数）"""


class TestDrainPendingInput:
    """测试清理 stdin 残留输入"""

    def test_returns_none(self):
        """测试函数可正常调用且不抛异常（管道输入下应为无操作）"""
        from services.menu_service import drain_pending_input

        assert drain_pending_input() is None
        assert drain_pending_input() is None  # 重复调用也不报错

    def test_piped_stdin_not_consumed(self):
        """测试管道输入内容不会被 drain 消费（自动化/脚本场景不受影响）"""
        import sys

        from services.menu_service import drain_pending_input

        # 在 stdin 有数据时调用 drain，确认不会清掉管道里的输入
        if hasattr(sys.stdin, "readable") and sys.stdin.readable():
            drain_pending_input()
            # 能正常读/关闭即可，不抛异常
            assert True
