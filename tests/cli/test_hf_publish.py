import json
import sys
import types
from pathlib import Path

import pytest

from services import hf_download


class FakeHfApi:
    def __init__(self, token=None):
        self.token = token
        self.created = []
        self.uploaded = []

    def create_repo(self, repo_id, repo_type="model", private=True, exist_ok=False):
        self.created.append({
            "repo_id": repo_id,
            "repo_type": repo_type,
            "private": private,
            "exist_ok": exist_ok,
        })
        return {"repo_id": repo_id, "private": private}

    def upload_file(self, *, path_or_fileobj, path_in_repo, repo_id, repo_type="model"):
        self.uploaded.append({
            "path_or_fileobj": str(path_or_fileobj),
            "path_in_repo": path_in_repo,
            "repo_id": repo_id,
            "repo_type": repo_type,
        })
        return {"path_in_repo": path_in_repo}


@pytest.fixture
def fake_hf(monkeypatch):
    fake_module = types.ModuleType("huggingface_hub")
    fake_module.HfApi = FakeHfApi
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)
    monkeypatch.setattr(hf_download, "hf_import", lambda: True)
    monkeypatch.setattr(hf_download, "apply_endpoint", lambda use_mirror=True: "https://huggingface.co")
    return fake_module


def test_publish_model_uploads_model_classes_and_config(tmp_path, fake_hf):
    model = tmp_path / "37ac-v1.pth"
    model.write_bytes(b"weights")
    classes = tmp_path / "classes.json"
    classes.write_text('{"a": 1}', encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"schema_version": 1, "version": "1.0.0"}), encoding="utf-8")

    info = hf_download.publish_model(
        repo_id="demo/37ac",
        model_path=model,
        classes_path=classes,
        config_path=config,
        token="tok",
        private=True,
    )

    assert info["repo_id"] == "demo/37ac"
    assert info["config_url"].endswith("config.json")
    assert info["weights_url"].endswith("37ac-v1.pth")
    assert info["classes_url"].endswith("classes.json")

    api = info["api"]
    assert api.created == [{"repo_id": "demo/37ac", "repo_type": "model", "private": True, "exist_ok": True}]
    assert [item["path_in_repo"] for item in api.uploaded] == ["37ac-v1.pth", "classes.json", "config.json"]
