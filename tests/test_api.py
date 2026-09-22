"""Tests for the HTTP API in api.py."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

import engine
from api import app

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
client = TestClient(app)


def example(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_root_redirects_to_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_gap_analysis_endpoint():
    response = client.post("/analyse", json={"mode": "gap_analysis", **example("report.json")})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "gap_analysis"
    assert body["gaps_found"] == 3


def test_eligibility_endpoint():
    response = client.post("/analyse", json={"mode": "eligibility", **example("profile.json")})
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["fail_reasons"] == ["cibil_score"]


def test_unknown_mode():
    response = client.post("/analyse", json={"mode": "magic"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNKNOWN_MODE"


def test_missing_mode():
    response = client.post("/analyse", json=example("report.json"))
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNKNOWN_MODE"


def test_missing_field_returns_clean_error():
    response = client.post("/analyse", json={"mode": "eligibility", "customer_id": "C9"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "RULE_ENGINE_ERROR"
    assert "missing" in detail["error"]


def test_body_must_be_a_json_object():
    response = client.post("/analyse", json=[1, 2, 3])
    assert response.status_code == 422


def test_api_and_cli_give_identical_results(capsys):
    for mode, file in [("gap_analysis", "report.json"), ("eligibility", "profile.json")]:
        api_result = client.post("/analyse", json={"mode": mode, **example(file)}).json()
        assert engine.main(["--mode", mode, "--input", str(EXAMPLES / file)]) == 0
        cli_result = json.loads(capsys.readouterr().out)
        assert api_result == cli_result
