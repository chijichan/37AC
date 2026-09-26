"""多通道结果（services/channel_service.py）回归测试。"""

import time

from services import channel_service as cs


# ---------------- 通道解析 ----------------

def test_parse_channels_explicit_list():
    assert cs.parse_channels("37ac,llm,human") == ["37ac", "llm", "human"]
    assert cs.parse_channels("human, llm ,37ac") == ["human", "llm", "37ac"]
    assert cs.parse_channels("37ac，llm") == ["37ac", "llm"]          # 中文逗号
    assert cs.parse_channels("37ac,37ac,local") == ["37ac"]           # 去重 + 别名


def test_parse_channels_aliases():
    assert cs.parse_channels("local,manual") == ["37ac", "human"]
    assert cs.parse_channels("人工") == ["human"]


def test_parse_channels_falls_back_to_legacy_model():
    assert cs.parse_channels(None, "37ac") == ["37ac"]
    assert cs.parse_channels("", "llm") == ["llm"]
    assert cs.parse_channels(None, "auto") == ["auto"]               # 旧分流行为
    assert cs.parse_channels("bogus", "llm") == ["llm"]
    assert cs.parse_channels(None, None) == ["37ac"]


def test_node_channels_filters_human():
    assert cs.node_channels(["37ac", "llm", "human"]) == ["37ac", "llm"]
    assert cs.node_channels(["human"]) == []


# ---------------- 子任务 id ----------------

def test_sub_task_id_single_channel_keeps_parent_id():
    assert cs.sub_task_id("abc", "37ac", 1) == "abc"


def test_sub_task_id_and_split_roundtrip():
    sub = cs.sub_task_id("abc-123", "llm", 2)
    assert sub == "abc-123:llm"
    assert cs.split_task_id(sub) == ("abc-123", "llm")


def test_split_task_id_without_suffix():
    assert cs.split_task_id("abc-123") == ("abc-123", None)
    # 未知后缀不拆（避免把 uuid 里的内容误判成通道）
    assert cs.split_task_id("abc-123:stream") == ("abc-123:stream", None)


# ---------------- 结果骨架与合并 ----------------

def test_initial_result_scaffold():
    payload = cs.initial_result("t1", ["37ac", "llm", "human"])

    assert payload["requested_channels"] == ["37ac", "llm", "human"]
    assert payload["37ac"]["status"] == "queued"
    assert payload["llm"]["status"] == "queued"
    assert payload["human"] == {"status": "awaiting", "votes": []}


def test_merge_channel_result_keeps_legacy_fields_from_37ac():
    payload = cs.initial_result("t1", ["37ac", "llm"])
    cs.merge_channel_result(payload, "llm", {"recognition_type": "llm", "class_probs": [{"name": "B", "prob": 50}], "characters": [{"index": 0}]})
    cs.merge_channel_result(payload, "37ac", {"recognition_type": "local", "class_probs": [{"name": "A", "prob": 90}], "characters": [{"index": 0}], "crop_method": "yolo"})

    assert payload["llm"]["class_probs"][0]["name"] == "B"
    assert payload["37ac"]["crop_method"] == "yolo"
    # 顶层兼容字段：37ac 优先
    assert payload["class_probs"][0]["name"] == "A"
    assert payload["crop_method"] == "yolo"


def test_merge_channel_result_llm_fills_legacy_when_no_37ac():
    payload = cs.initial_result("t1", ["llm"])
    cs.merge_channel_result(payload, "llm", {"recognition_type": "llm", "class_probs": [{"name": "B", "prob": 50}]})

    assert payload["class_probs"][0]["name"] == "B"
    assert payload["recognition_type"] == "llm"


def test_overall_status_transitions():
    payload = cs.initial_result("t1", ["37ac", "llm"])
    assert cs.overall_status(payload) == "pending"

    cs.merge_channel_result(payload, "37ac", {"class_probs": []})
    assert cs.overall_status(payload) == "partial"

    cs.merge_channel_result(payload, "llm", {"class_probs": []})
    assert cs.overall_status(payload) == "completed"


def test_overall_status_human_only():
    payload = cs.initial_result("t1", ["human"])
    assert cs.overall_status(payload) == "pending"

    cs.add_human_vote(payload, cs.human_entry("原神/荧", source="human"))
    assert cs.overall_status(payload) == "completed"


def test_channel_status_missing_or_unknown():
    assert cs.channel_status({}, "37ac") == "missing"
    assert cs.channel_status({"37ac": {}}, "37ac") == "unknown"


# ---------------- 人工标注 ----------------

def test_add_human_vote_appends_and_counts():
    payload = cs.initial_result("t1", ["human"])
    cs.add_human_vote(payload, cs.human_entry("A", source="human"))
    cs.add_human_vote(payload, cs.human_entry("B", source="human"))

    section = payload["human"]
    assert section["count"] == 2
    assert [v["name"] for v in section["votes"]] == ["A", "B"]
    assert section["status"] == "completed"


def test_add_human_vote_same_voter_overwrites():
    payload = cs.initial_result("t1", ["human"])
    cs.add_human_vote(payload, cs.human_entry("A", source="human"), voter_key="ip:1.2.3.4")
    cs.add_human_vote(payload, cs.human_entry("B", source="human"), voter_key="ip:1.2.3.4")

    votes = payload["human"]["votes"]
    assert len(votes) == 1
    assert votes[0]["name"] == "B"
    assert votes[0]["voter"] == "ip:1.2.3.4"


def test_human_entry_fields():
    entry = cs.human_entry("原神/荧", character_index="2", note="很确定", source="human", voter="ip:1")

    assert entry["name"] == "原神/荧"
    assert entry["character_index"] == 2
    assert entry["note"] == "很确定"
    assert entry["voter"] == "ip:1"
    assert entry["status"] == "completed"
    assert isinstance(entry["at"], int)


# ---------------- 读时补框 ----------------

def test_resolve_human_bbox_from_character_index():
    payload = cs.initial_result("t1", ["37ac", "human"])
    cs.merge_channel_result(payload, "37ac", {
        "characters": [
            {"index": 0, "bbox": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.5},
             "bbox_percent": {"x": 10.0, "y": 10.0, "w": 20.0, "h": 50.0},
             "class_probs": [{"name": "模型猜的", "prob": 88.0}]},
        ],
    })
    cs.add_human_vote(payload, cs.human_entry("人工答的", character_index=0, source="human"))

    cs.resolve_human_bbox(payload)
    vote = payload["human"]["votes"][0]

    assert vote["bbox"] == {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.5}
    assert vote["bbox_percent"]["w"] == 20.0
    assert vote["model_guess"] == "模型猜的"


def test_resolve_human_bbox_keeps_explicit_box():
    payload = cs.initial_result("t1", ["human"])
    cs.add_human_vote(payload, cs.human_entry("A", character_index=0, bbox={"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1}))

    cs.resolve_human_bbox(payload)
    assert payload["human"]["votes"][0]["bbox"] == {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1}


# ---------------- 匿名投票限流 ----------------

def test_vote_allowed_per_ip_limit():
    cs._vote_windows.clear()
    assert cs.vote_allowed("9.9.9.9", 2) is True
    assert cs.vote_allowed("9.9.9.9", 2) is True
    assert cs.vote_allowed("9.9.9.9", 2) is False        # 超过每小时上限
    assert cs.vote_allowed("8.8.8.8", 2) is True         # 其它 IP 不受影响


def test_vote_allowed_zero_means_unlimited():
    cs._vote_windows.clear()
    for _ in range(5):
        assert cs.vote_allowed("7.7.7.7", 0) is True


# ---------------- 结果通道判定（生产环境 37ac 溢出到 llm 的回归） ----------------

def _scaffold(channels=("37ac", "llm")):
    return cs.initial_result("p1", list(channels))


def test_resolve_channel_prefers_task_id_suffix():
    payload = _scaffold()
    # 后缀说了算：即使节点上报的是 local（回退），也必须落在 llm 通道
    assert cs.resolve_result_channel(
        "p1", "p1:llm", payload,
        reported_channel="37ac",
        assigned_tasks=["p1:37ac", "p1:llm"],
        inferred_type="local",
    ) == "llm"


def test_resolve_channel_uses_reported_channel_without_suffix():
    payload = _scaffold()
    assert cs.resolve_result_channel("p1", "p1", payload, reported_channel="llm") == "llm"
    assert cs.resolve_result_channel("p1", "p1", payload, reported_channel="本地模型") is None


def test_resolve_channel_uses_unique_assigned_subtask():
    payload = _scaffold()
    assert cs.resolve_result_channel(
        "p1", "p1", payload, assigned_tasks=["p1:llm", "p1:human", "other:37ac"]
    ) == "llm"


def test_resolve_channel_single_requested_node_channel():
    payload = _scaffold(("llm", "human"))
    assert cs.resolve_result_channel("p1", "p1", payload) == "llm"


def test_resolve_channel_infers_by_recognition_type_as_last_resort():
    payload = _scaffold()
    assert cs.resolve_result_channel("p1", "p1", payload, inferred_type="llm") == "llm"
    assert cs.resolve_result_channel("p1", "p1", payload, inferred_type="local") == "37ac"


def test_resolve_channel_refuses_channel_that_was_not_requested():
    payload = _scaffold(("llm", "human"))
    # 只请求了 llm：无后缀的结果只能是 llm（节点回退本地模型也仍属于 llm 通道，
    # 但绝不能写进没请求过的 37ac —— 那正是"37ac 结果溢出到 llm"的反向污染）
    assert cs.resolve_result_channel("p1", "p1", payload, inferred_type="local") == "llm"
    # 后缀指向没请求过的通道 → 丢弃
    assert cs.resolve_result_channel("p1", "p1:37ac", payload) is None


def test_resolve_channel_refuses_when_only_human_requested():
    payload = cs.initial_result("p1", ["human"])
    assert cs.resolve_result_channel("p1", "p1", payload, inferred_type="local") is None


def test_resolve_channel_refuses_human_and_unknown():
    payload = _scaffold()
    assert cs.resolve_result_channel("p1", "p1:human", payload) is None
    assert cs.resolve_result_channel("p1", "p1:stream", payload) is None


def test_resolve_channel_none_when_nothing_matches():
    payload = _scaffold()
    assert cs.resolve_result_channel("p1", "p1", payload, assigned_tasks=["other:37ac"]) is None


# ---------------- 重复回传 ----------------

def test_duplicate_channel_result_detected():
    payload = _scaffold()
    first = {"recognition_type": "local", "success": True,
             "class_probs": [{"name": "A", "prob": 90}], "characters": []}
    cs.merge_channel_result(payload, "37ac", first)
    assert cs.is_duplicate_channel_result(payload, "37ac", dict(first)) is True
    # 换一张图的结果 → 不是重复
    other = {"recognition_type": "local", "success": True,
             "class_probs": [{"name": "B", "prob": 80}], "characters": []}
    assert cs.is_duplicate_channel_result(payload, "37ac", other) is False
    # 通道还没结果 → 不算重复
    assert cs.is_duplicate_channel_result(payload, "llm", dict(first)) is False


# ---------------- 回退标记 ----------------

def test_merge_marks_fallback_when_node_used_other_model():
    payload = _scaffold()
    cs.merge_channel_result(payload, "llm", {
        "recognition_type": "local",              # 节点回退到本地模型
        "class_probs": [{"name": "A", "prob": 24.35}],
        "characters": [],
    })
    assert payload["llm"]["fallback"] == {"requested": "llm", "actual": "local"}


def test_merge_has_no_fallback_marker_for_matching_type():
    payload = _scaffold()
    cs.merge_channel_result(payload, "llm", {
        "recognition_type": "llm", "class_probs": [], "characters": [],
    })
    assert "fallback" not in payload["llm"]

    # 先回退、后正常：标记要被清掉
    cs.merge_channel_result(payload, "llm", {
        "recognition_type": "local", "class_probs": [], "characters": [],
    })
    assert "fallback" in payload["llm"]
    cs.merge_channel_result(payload, "llm", {
        "recognition_type": "llm", "class_probs": [], "characters": [],
    })
    assert "fallback" not in payload["llm"]
