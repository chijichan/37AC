"""LLM 一图多角：位置解析 + 人物数组解析（不联网）。"""

import json

import pytest

from config import base as cfg
from prediction import predictor as P


def _api_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]}


# ---------------- 位置解析 ----------------

def test_normalize_box_percent_list():
    bbox, percent = P._normalize_llm_box([10, 20, 60, 90], (1000, 500))

    assert percent == {"x": 10.0, "y": 20.0, "w": 50.0, "h": 70.0}
    assert bbox == {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.7}


def test_normalize_box_normalized_list():
    bbox, percent = P._normalize_llm_box([0.1, 0.2, 0.6, 0.9], (1000, 500))

    assert percent["x"] == pytest.approx(10.0, abs=0.01)
    assert percent["w"] == pytest.approx(50.0, abs=0.01)
    assert bbox["w"] == pytest.approx(0.5, abs=0.001)


def test_normalize_box_xywh_dict_and_ltbr_dict():
    bbox, percent = P._normalize_llm_box({"x": 10, "y": 10, "w": 30, "h": 40})
    assert percent == {"x": 10.0, "y": 10.0, "w": 30.0, "h": 40.0}

    _bbox2, percent2 = P._normalize_llm_box({"left": 5, "top": 6, "right": 25, "bottom": 46})
    assert percent2 == {"x": 5.0, "y": 6.0, "w": 20.0, "h": 40.0}


def test_normalize_box_string_and_swapped_order():
    _bbox, percent = P._normalize_llm_box("60,90,10,20")
    assert percent == {"x": 10.0, "y": 20.0, "w": 50.0, "h": 70.0}   # 自动交换 x1<x2, y1<y2


def test_normalize_box_rejects_degenerate_and_garbage():
    assert P._normalize_llm_box(None) == (None, None)
    assert P._normalize_llm_box([10, 10, 10.5, 90]) == (None, None)     # 宽度 <1%
    assert P._normalize_llm_box("没有坐标") == (None, None)
    assert P._normalize_llm_box({"foo": 1}) == (None, None)


def test_normalize_box_clamps_out_of_range():
    _bbox, percent = P._normalize_llm_box([-20, -10, 150, 130])
    assert percent == {"x": 0.0, "y": 0.0, "w": 100.0, "h": 100.0}


# ---------------- 人物数组解析 ----------------

def test_parse_characters_multi():
    parsed = {
        "characters": [
            {"label": "蔚蓝档案/白子", "confidence": 82, "box": [55, 20, 90, 92]},
            {"label": "原神/雷电将军", "confidence": 95, "box": [10, 15, 45, 88],
             "class_probs": [{"label": "原神/雷电将军", "confidence": 80}]},
        ],
        "label": "原神/雷电将军",
        "confidence": 95,
    }
    characters = P._parse_llm_characters(parsed, (1000, 1000))

    assert [c["label"] for c in characters] == ["原神/雷电将军", "蔚蓝档案/白子"]   # 面积降序
    assert [c["index"] for c in characters] == [0, 1]
    assert characters[0]["bbox_percent"] == {"x": 10.0, "y": 15.0, "w": 35.0, "h": 73.0}
    assert characters[0]["source"] == "llm"
    assert characters[0]["class_probs"][0]["name"] == "原神/雷电将军"


def test_parse_characters_single_object_compat():
    parsed = {"label": "原神/荧", "confidence": 88,
              "class_probs": [{"label": "原神/荧", "confidence": 70}]}
    characters = P._parse_llm_characters(parsed, (800, 600))

    assert len(characters) == 1
    assert characters[0]["label"] == "原神/荧"
    assert characters[0]["bbox"] is None          # 旧格式没有位置
    assert characters[0]["confidence"] == 88


def test_parse_characters_filters_placeholder_and_invalid():
    parsed = {"characters": [
        {"label": "作品名/角色名", "confidence": 90},
        {"label": "原神/荧", "confidence": 80},
    ]}
    characters = P._parse_llm_characters(parsed, (100, 100))

    assert [c["label"] for c in characters] == ["原神/荧"]


def test_parse_characters_normalizes_reversed_label():
    parsed = {"characters": [{"label": "雷电将军/原神", "confidence": 90}]}
    characters = P._parse_llm_characters(parsed, (100, 100))

    assert characters[0]["label"] == "原神/雷电将军"


def test_parse_characters_respects_cap(monkeypatch):
    monkeypatch.setattr(P, "LLM_MAX_CHARACTERS", 2)
    parsed = {"characters": [
        {"label": "A/1", "confidence": 90, "box": [0, 0, 10, 10]},
        {"label": "B/2", "confidence": 80, "box": [0, 0, 40, 40]},
        {"label": "C/3", "confidence": 70, "box": [0, 0, 30, 30]},
    ]}
    characters = P._parse_llm_characters(parsed, (100, 100))

    assert len(characters) == 2
    assert [c["label"] for c in characters] == ["B/2", "C/3"]     # 面积大的优先保留


def test_parse_characters_without_box_sorted_by_confidence():
    parsed = {"characters": [
        {"label": "A/1", "confidence": 60},
        {"label": "B/2", "confidence": 90},
    ]}
    characters = P._parse_llm_characters(parsed, (100, 100))

    assert [c["label"] for c in characters] == ["B/2", "A/1"]


# ---------------- 整条解析链路 ----------------

def test_parse_llm_response_returns_characters():
    payload = {
        "characters": [
            {"label": "原神/雷电将军", "confidence": 95, "box": [10, 15, 45, 88]},
            {"label": "蔚蓝档案/白子", "confidence": 82, "box": [55, 20, 90, 92]},
        ],
        "label": "原神/雷电将军",
        "confidence": 95,
        "features_used": ["紫色长发"],
        "tags": ["紫发"],
    }
    label, confidence, features, tags, probs, characters = P._parse_llm_response(_api_response(payload), (1000, 1000))

    assert label == "原神/雷电将军"
    assert confidence == 95
    assert len(characters) == 2
    assert characters[0]["bbox"] is not None
    assert features == ["紫色长发"] and tags == ["紫发"]


def test_parse_llm_response_fills_label_from_characters():
    payload = {"characters": [{"label": "崩坏：星穹铁道/银狼", "confidence": 77, "box": [0, 0, 50, 50]}]}
    label, confidence, _f, _t, probs, characters = P._parse_llm_response(_api_response(payload), (100, 100))

    assert label == "崩坏：星穹铁道/银狼"       # 顶层缺失 -> 用人物的
    assert confidence == 77
    assert len(characters) == 1


def test_parse_llm_response_empty_content():
    assert P._parse_llm_response({"choices": [{"message": {"content": ""}}]}) == ("", 0.0, [], [], [], [])


# ---------------- 提示词开关 ----------------

def test_default_prompt_switches_with_flag():
    if cfg.LLM_MULTI_CHARACTER:
        assert "characters" in cfg.LLM_PROMPT_TEMPLATE
        assert "0-100" in cfg.LLM_PROMPT_TEMPLATE
        assert cfg.LLM_PROMPT_TEMPLATE == cfg._DEFAULT_LLM_PROMPT_MULTI
    else:
        assert cfg.LLM_PROMPT_TEMPLATE == cfg._DEFAULT_LLM_PROMPT
    # 两个提示词都要保底存在，便于随时切回去
    assert "只识别主体角色" in cfg._DEFAULT_LLM_PROMPT
