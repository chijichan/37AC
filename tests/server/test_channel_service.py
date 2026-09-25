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
