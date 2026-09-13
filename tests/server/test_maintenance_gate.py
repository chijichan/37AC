"""维护模式闸门：503 信封与错误码（不触碰数据库，monkeypatch 设置读取）。"""

import pytest


@pytest.fixture
def app_client(monkeypatch):
    from AC_web import app
    from services import settings_service

    monkeypatch.setattr(
        settings_service,
        "get_setting",
        lambda key, default=None: "1" if key == "maintenance_mode" else default,
    )
    return app.test_client()


def test_maintenance_returns_503_with_code(app_client):
    response = app_client.get("/models")
    body = response.get_json()

    assert response.status_code == 503
    assert body["success"] is False
    assert body["code"] == "MAINTENANCE_MODE"
    assert body["maintenance"] is True
    assert body["message"]


def test_maintenance_allows_auth_prefix(app_client):
    # /auth 前缀始终放行（否则管理员进不去关开关）
    assert app_client.get("/auth/verify").status_code != 503


@pytest.fixture
def normal_client(monkeypatch):
    from AC_web import app
    from services import settings_service

    monkeypatch.setattr(
        settings_service,
        "get_setting",
        lambda key, default=None: "0" if key == "maintenance_mode" else default,
    )
    return app.test_client()


def test_normal_mode_not_blocked(normal_client):
    assert normal_client.get("/models").status_code == 200
