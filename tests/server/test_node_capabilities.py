"""节点 capabilities 字段语义的回归测试。"""

from services.dashboard.node_service import _row_to_node_dict, parse_capabilities


def test_parse_capabilities_json_string():
    assert parse_capabilities('["local", "llm"]') == ["local", "llm"]


def test_parse_capabilities_list():
    assert parse_capabilities(["local", "llm"]) == ["local", "llm"]


def test_parse_capabilities_comma_string():
    assert parse_capabilities("local,llm") == ["local", "llm"]


def test_parse_capabilities_empty_falls_back_to_default():
    assert parse_capabilities(None) == ["local"]
    assert parse_capabilities("") == ["local"]
    assert parse_capabilities([]) == ["local"]
    assert parse_capabilities("  ") == ["local"]


def test_parse_capabilities_custom_default():
    assert parse_capabilities(None, default=("local", "llm")) == ["local", "llm"]


def test_parse_capabilities_broken_json_string_falls_back():
    assert parse_capabilities('[local, llm') == ["[local", "llm"]


def test_parse_capabilities_strips_blanks():
    assert parse_capabilities("local, , llm ") == ["local", "llm"]


def test_row_to_node_dict_exposes_array_form():
    node = _row_to_node_dict({
        "id": 5,
        "name": "n-001",
        "capabilities": '["local", "llm"]',
        "status": "online",
        "is_active": 1,
    })

    assert node["capabilities"] == '["local", "llm"]'      # 旧字段保留
    assert node["capabilities_list"] == ["local", "llm"]   # 新增数组字段


def test_row_to_node_dict_default_capabilities():
    node = _row_to_node_dict({"id": 1, "name": "n", "capabilities": None})
    assert node["capabilities"] == '["local"]'
    assert node["capabilities_list"] == ["local"]


# ---------------- 分发时不跨能力降级（37ac 结果溢出到 llm 的根因） ----------------

class _FakeSocket:
    def setblocking(self, flag):
        return None

    def send(self, data):
        return 0


def test_allocate_does_not_hand_llm_task_to_local_only_node():
    from services.node_manager import node_manager

    node_manager.register_node("cap-local-1", ("127.0.0.1", 1), socket_obj=_FakeSocket(),
                               capabilities='["local"]', models=["37ac"], llm_enabled=False)
    try:
        # 没有 llm 能力的节点：llm 任务必须转为等待，而不是"降级"发过去
        # （发过去节点只能回退本地模型，结果顶着 llm 通道存下来 → 看起来就是 37ac 溢出到 llm）
        assert node_manager.allocate_node_for_task("llm") == (None, None)
        # 本地任务照常
        node_id, _sock = node_manager.allocate_node_for_task("local")
        assert node_id == "cap-local-1"
    finally:
        node_manager.remove_node("cap-local-1")


def test_allocate_can_still_fall_back_when_explicitly_allowed():
    from services.node_manager import node_manager

    node_manager.register_node("cap-local-2", ("127.0.0.1", 2), socket_obj=_FakeSocket(),
                               capabilities='["local"]', models=["37ac"], llm_enabled=False)
    try:
        node_id, _sock = node_manager.allocate_node_for_task("llm", allow_fallback=True)
        assert node_id == "cap-local-2"
    finally:
        node_manager.remove_node("cap-local-2")


def test_allocate_prefers_capable_node_for_llm():
    from services.node_manager import node_manager

    node_manager.register_node("cap-local-3", ("127.0.0.1", 3), socket_obj=_FakeSocket(),
                               capabilities='["local"]', models=["37ac"], llm_enabled=False)
    node_manager.register_node("cap-llm-3", ("127.0.0.1", 4), socket_obj=_FakeSocket(),
                               capabilities='["local", "llm"]', models=["37ac"], llm_enabled=True)
    try:
        node_id, _sock = node_manager.allocate_node_for_task("llm")
        assert node_id == "cap-llm-3"
    finally:
        node_manager.remove_node("cap-local-3")
        node_manager.remove_node("cap-llm-3")


def test_get_assigned_tasks_exposes_sub_task_ids():
    from services.node_manager import node_manager

    node_manager.register_node("cap-assign-1", ("127.0.0.1", 5), socket_obj=_FakeSocket(),
                               capabilities='["local"]', models=["37ac"])
    try:
        node_manager.assign_task("cap-assign-1", "p1:37ac")
        node_manager.assign_task("cap-assign-1", "p1:llm")
        assert node_manager.get_assigned_tasks("cap-assign-1") == ["p1:37ac", "p1:llm"]
        assert node_manager.get_assigned_tasks("no-such-node") == []
    finally:
        node_manager.remove_node("cap-assign-1")
