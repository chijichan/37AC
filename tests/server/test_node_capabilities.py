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
