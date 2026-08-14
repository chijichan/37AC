"""测试识别结果统一结构（common/recognition.py）"""


class TestToProb:
    """测试概率归一化"""

    def test_numeric(self):
        from common.recognition import to_prob

        assert to_prob(93) == 93.0
        assert to_prob(93.5) == 93.5
        assert to_prob(0) == 0.0

    def test_string(self):
        from common.recognition import to_prob

        assert to_prob("93.5") == 93.5
        assert to_prob("93.5%") == 93.5
        assert to_prob(" 88 %") == 88.0

    def test_invalid(self):
        from common.recognition import to_prob

        assert to_prob("abc") is None
        assert to_prob(None) is None
        assert to_prob(True) is None


class TestParseCandidateEntry:
    """测试候选条目归一化"""

    def test_canonical_name_prob(self):
        from common.recognition import parse_candidate_entry

        entry = parse_candidate_entry({"name": "原神/荧", "prob": 93.0})
        assert entry == {"name": "原神/荧", "prob": 93.0}

    def test_legacy_label_confidence(self):
        from common.recognition import parse_candidate_entry

        entry = parse_candidate_entry({"label": "原神/荧", "confidence": "90.5%"})
        assert entry == {"name": "原神/荧", "prob": 90.5}

    def test_name_probability(self):
        from common.recognition import parse_candidate_entry

        entry = parse_candidate_entry({"name": "原神/空", "probability": 88})
        assert entry == {"name": "原神/空", "prob": 88.0}

    def test_passthrough_class_fields(self):
        from common.recognition import parse_candidate_entry

        entry = parse_candidate_entry({
            "name": "蔚蓝档案/黑见茜香", "prob": 92.0,
            "id": "黑见茜香", "ip": "蔚蓝档案", "name_zh": "黑见茜香",
            "features_used": ["银发"], "tags": ["女性角色"],
        })
        assert entry["name"] == "蔚蓝档案/黑见茜香"
        assert entry["prob"] == 92.0
        assert entry["id"] == "黑见茜香"
        assert entry["ip"] == "蔚蓝档案"
        assert entry["features_used"] == ["银发"]
        assert entry["tags"] == ["女性角色"]

    def test_invalid_entry(self):
        from common.recognition import parse_candidate_entry

        assert parse_candidate_entry(None) is None
        assert parse_candidate_entry({"prob": 90}) is None
        assert parse_candidate_entry({"name": "  "}) is None


class TestParseTopCandidate:
    """测试从识别结果提取最佳候选"""

    def test_top_from_class_probs(self):
        from common.recognition import parse_top_candidate

        result = {
            "success": True,
            "class_probs": [
                {"name": "原神/荧", "prob": 93.0},
                {"name": "原神/空", "prob": 5.2},
            ],
        }
        top = parse_top_candidate(result)
        assert top == {"name": "原神/荧", "prob": 93.0}

    def test_no_class_probs(self):
        from common.recognition import parse_top_candidate

        assert parse_top_candidate({"success": False, "error": "x"}) is None
        assert parse_top_candidate(None) is None
        assert parse_top_candidate("not a dict") is None

    def test_legacy_top_fields(self):
        from common.recognition import parse_top_candidate

        result = {"success": True, "class_probs": [{"label": "原神/荧", "confidence": 90}]}
        top = parse_top_candidate(result)
        assert top == {"name": "原神/荧", "prob": 90.0}

    def test_result_top_helpers(self):
        from common.recognition import result_top_name, result_top_prob

        result = {"success": True, "class_probs": [{"name": "原神/荧", "prob": 93.0}]}
        assert result_top_name(result) == "原神/荧"
        assert result_top_prob(result) == 93.0
        assert result_top_name({"success": False}) is None
        assert result_top_prob({"success": False}) is None
