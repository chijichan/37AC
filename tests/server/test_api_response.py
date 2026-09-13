"""响应信封与错误码的回归测试（utils/api_response.py）"""

import json

import pytest
from flask import Flask, Response, jsonify

from utils import api_response
from utils.api_response import install, normalize_payload


# ---------------- 纯函数 ----------------

def test_normalize_payload_adds_success_and_code():
    payload, changed = normalize_payload({"type": "dashboard_stats", "timestamp": 1, "data": {}}, 200)

    assert changed is True
    assert payload["success"] is True
    assert payload["code"] == "OK"
    # 旧字段原样保留
    assert payload["type"] == "dashboard_stats"
    assert payload["timestamp"] == 1


def test_normalize_payload_keeps_existing_values():
    payload, changed = normalize_payload({"success": False, "code": "MY_CODE", "message": "x"}, 400)

    assert changed is False
    assert payload["success"] is False
    assert payload["code"] == "MY_CODE"


def test_normalize_payload_mirrors_error_to_message():
    payload, changed = normalize_payload({"error": "获取仪表盘数据失败"}, 500)

    assert changed is True
    assert payload["success"] is False
    assert payload["code"] == "INTERNAL_ERROR"
    assert payload["message"] == "获取仪表盘数据失败"
    assert payload["error"] == "获取仪表盘数据失败"


def test_normalize_payload_override_code_wins():
    payload, _ = normalize_payload({}, 401, code="AUTH_TOKEN_MISSING")
    assert payload["code"] == "AUTH_TOKEN_MISSING"


def test_normalize_payload_ignores_non_dict():
    payload, changed = normalize_payload([1, 2, 3], 200)
    assert changed is False
    assert payload == [1, 2, 3]


# ---------------- Flask 集成 ----------------

@pytest.fixture
def client():
    app = Flask(__name__)
    install(app)

    @app.route("/a")
    def _a():
        return jsonify({"success": True, "message": "ok", "data": {"n": 1}})

    @app.route("/b")
    def _b():
        return jsonify({"type": "dashboard_stats", "timestamp": 1, "data": {"accuracy": 0.5}})

    @app.route("/c")
    def _c():
        return jsonify({"error": "获取仪表盘数据失败"}), 500

    @app.route("/explicit")
    def _explicit():
        return jsonify({"success": False, "code": "MY_CODE", "message": "x"}), 400

    @app.route("/sse")
    def _sse():
        return Response(iter(["data: {}\n\n"]), mimetype="text/event-stream")

    @app.route("/boom")
    def _boom():
        raise RuntimeError("kaboom")

    return app.test_client()


def _json(response):
    return json.loads(response.get_data(as_text=True))


def test_envelope_on_a_shape(client):
    body = _json(client.get("/a"))
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"] == {"n": 1}


def test_envelope_on_b_shape(client):
    response = client.get("/b")
    body = _json(response)

    assert response.status_code == 200
    assert body["success"] is True          # 新增
    assert body["code"] == "OK"             # 新增
    assert body["type"] == "dashboard_stats"  # 旧字段不动
    assert body["data"] == {"accuracy": 0.5}


def test_envelope_on_c_shape(client):
    response = client.get("/c")
    body = _json(response)

    assert response.status_code == 500
    assert body["success"] is False
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "获取仪表盘数据失败"


def test_explicit_code_is_preserved(client):
    body = _json(client.get("/explicit"))
    assert body["code"] == "MY_CODE"


def test_sse_response_is_untouched(client):
    response = client.get("/sse")

    assert response.mimetype == "text/event-stream"
    assert response.get_data(as_text=True) == "data: {}\n\n"


def test_unhandled_exception_returns_json_envelope(client):
    response = client.get("/boom")
    body = _json(response)

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    assert body["success"] is False
    assert body["code"] == "INTERNAL_ERROR"


def test_unknown_path_returns_json_404(client):
    response = client.get("/definitely-not-here")
    body = _json(response)

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert body["code"] == "NOT_FOUND"
    assert body["success"] is False


def test_method_not_allowed_returns_json_405(client):
    response = client.post("/a")
    body = _json(response)

    assert response.status_code == 405
    assert body["code"] == "METHOD_NOT_ALLOWED"


def test_default_codes_are_stable():
    assert api_response.default_code(200) == "OK"
    assert api_response.default_code(202) == "ACCEPTED"
    assert api_response.default_code(429) == "RATE_LIMITED"
    assert api_response.default_code(503) == "SERVICE_UNAVAILABLE"
    assert api_response.default_code(418) == api_response.ERROR_CODE
