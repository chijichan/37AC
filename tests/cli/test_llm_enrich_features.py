"""训练后用 LLM 补 features_used / tags：达到上限就跳过（默认各 3 条）。"""

import json
import shutil
import uuid
from pathlib import Path

import pytest

from config import base as cfg
from prediction import predictor as P
from training import trainer as T


def _root() -> Path:
    base = Path(__file__).resolve().parents[2] / "src" / "cli" / "saves" / "tmp" / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    root = base / ("enrich-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeDataset:
    def __init__(self, samples):
        self.samples = samples

    def __len__(self):
        return len(self.samples)


# ---------------- 工具函数 ----------------

def test_merge_items_dedupes_and_caps():
    merged = T._merge_profile_items(["银发", "长发"], ["长发", "红瞳", "制服", "武器"], 3)
    assert merged == ["银发", "长发", "红瞳"]          # 已有的在前、去重、截断到 3


def test_merge_items_unlimited_when_zero():
    assert T._merge_profile_items([], ["a", "b", "c", "d"], 0) == ["a", "b", "c", "d"]


def test_profile_reached_limit():
    assert T._profile_reached_limit({"features_used": ["a", "b", "c"], "tags": ["x", "y", "z"]}, 3, 3)
    assert not T._profile_reached_limit({"features_used": ["a", "b", "c"], "tags": []}, 3, 3)
    assert not T._profile_reached_limit({"features_used": ["a"], "tags": ["x"]}, 3, 3)
    # 上限为 0 表示"不限制"：此时只要有内容就算达标，空 profile 仍会去补
    assert not T._profile_reached_limit({}, 0, 0)
    assert T._profile_reached_limit({"features_used": ["a"], "tags": ["x"]}, 0, 0)


# ---------------- 解析层截断 ----------------

def test_parse_llm_response_caps_items(monkeypatch):
    monkeypatch.setattr(P, "LLM_MAX_FEATURES", 3)
    monkeypatch.setattr(P, "LLM_MAX_TAGS", 3)
    payload = {
        "label": "原神/荧",
        "confidence": 90,
        "features_used": ["f1", "f2", "f3", "f4", "f5"],
        "tags": ["t1", "t2", "t3", "t4"],
    }
    content = json.dumps(payload, ensure_ascii=False)
    resp = {"choices": [{"message": {"content": content}}]}

    label, _conf, feats, tags, _probs = P._parse_llm_response(resp)

    assert label == "原神/荧"
    assert feats == ["f1", "f2", "f3"]
    assert tags == ["t1", "t2", "t3"]


def test_cap_items_zero_means_unlimited():
    assert P._cap_items(["a", "b", "c", "d"], 0) == ["a", "b", "c", "d"]
    assert P._cap_items(["a", "b", "c"], 2) == ["a", "b"]


def test_default_prompt_documents_the_cap():
    assert "最多 3 条" in cfg.LLM_PROMPT_TEMPLATE


# ---------------- 训练补全：够 3 条就不调 API ----------------

@pytest.fixture
def enrich_env(monkeypatch):
    root = _root()
    classes_path = root / "classes.json"
    classes_path.write_text(json.dumps({
        "原神/荧": {"id": 1, "ip": "原神", "name_zh": "荧",
                    "features_used": ["金发", "双辫", "白裙"], "tags": ["金发", "女性角色", "旅行者"]},
        "原神/胡桃": {"id": 2, "ip": "原神", "name_zh": "胡桃",
                      "features_used": ["红褐双马尾"], "tags": []},
    }, ensure_ascii=False), encoding="utf-8")

    calls = []
    monkeypatch.setattr(T, "CLASSES_JSON_PATH", classes_path)
    monkeypatch.setattr(T, "LLM_ENRICH_FEATURES", True)
    monkeypatch.setattr(T, "LLM_RECOGNITION_ENABLED", True)
    monkeypatch.setattr(T, "LLM_MAX_FEATURES", 3)
    monkeypatch.setattr(T, "LLM_MAX_TAGS", 3)
    saved = {}
    monkeypatch.setattr(T, "save_classes_to_json",
                        lambda path, names, profiles=None: saved.update({"names": names, "profiles": profiles}))

    def fake_predict(image_path):
        calls.append(image_path)
        return {"features_used": ["f1", "f2", "f3", "f4"], "tags": ["t1", "t2", "t3", "t4"]}

    monkeypatch.setattr(P, "predict_image_llm", fake_predict)

    dataset = FakeDataset([("img0.png", 0), ("img1.png", 1), ("img2.png", 2)])
    yield {"dataset": dataset, "calls": calls, "saved": saved,
           "names": ["原神/荧", "原神/胡桃", "原神/钟离"]}
    shutil.rmtree(root, ignore_errors=True)


def test_enrich_skips_roles_already_at_limit(enrich_env):
    T._enrich_classes_with_llm_features(enrich_env["dataset"], enrich_env["names"])

    profiles = enrich_env["saved"]["profiles"]
    # 荧：已有 3+3 → 不调用 API，原样保留
    assert enrich_env["calls"] == ["img1.png", "img2.png"]
    assert profiles["原神/荧"] == {"features_used": ["金发", "双辫", "白裙"],
                                 "tags": ["金发", "女性角色", "旅行者"]}
    # 胡桃：只有 1 个 feature、0 个 tag → 合并补齐并截断到 3
    assert profiles["原神/胡桃"]["features_used"] == ["红褐双马尾", "f1", "f2"]
    assert profiles["原神/胡桃"]["tags"] == ["t1", "t2", "t3"]
    # 钟离：没有任何 profile → 全取 LLM 结果并截断
    assert profiles["原神/钟离"] == {"features_used": ["f1", "f2", "f3"], "tags": ["t1", "t2", "t3"]}
    assert len(enrich_env["calls"]) == 2


def test_enrich_disabled_by_switch(enrich_env, monkeypatch):
    monkeypatch.setattr(T, "LLM_ENRICH_FEATURES", False)

    T._enrich_classes_with_llm_features(enrich_env["dataset"], enrich_env["names"])

    assert enrich_env["calls"] == []
    assert enrich_env["saved"] == {}
