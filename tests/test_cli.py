"""Tests for the command-line interface in engine.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import engine

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def run(capsys, *args):
    """Run the CLI in-process and return (exit code, parsed JSON output)."""
    code = engine.main(list(args))
    return code, json.loads(capsys.readouterr().out)


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_gap_analysis_example(capsys):
    code, out = run(capsys, "--mode", "gap_analysis", "--input", str(EXAMPLES / "report.json"))
    assert code == 0
    assert out["gaps_found"] == 3
    assert out["total_potential_score_gain"] == 70
    assert [g["id"] for g in out["gaps"]] == ["high_utilisation", "missed_payments", "short_credit_age"]


def test_eligibility_example_not_eligible(capsys):
    code, out = run(capsys, "--mode", "eligibility", "--input", str(EXAMPLES / "profile.json"))
    assert code == 0
    assert out["eligible"] is False
    assert out["fail_reasons"] == ["cibil_score"]
    assert out["risk_score"] == 30.0


def test_eligibility_example_eligible(capsys):
    code, out = run(capsys, "--mode", "eligibility", "--input", str(EXAMPLES / "profile_eligible.json"))
    assert code == 0
    assert out["eligible"] is True
    assert out["next_step"] == "Customer is eligible. Show available loan offers."


def test_cli_works_from_any_folder(tmp_path):
    # Run the real script from an unrelated folder: rules.yaml must still be found.
    result = subprocess.run(
        [sys.executable, str(ROOT / "engine.py"), "--mode", "gap_analysis",
         "--input", str(EXAMPLES / "report.json")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["gaps_found"] == 3


def test_custom_rules_file(capsys, tmp_path):
    rules = write(tmp_path, "rules.yaml", """
gap_rules:
  - id: high_dpd
    field: max_dpd_days
    operator: gt
    value: 30
    impact: high
    estimated_score_gain: 20
    action_template: "Clear the overdue account - it is {current_value} days past due"
""")
    report = write(tmp_path, "report.json", '{"customer_id": "C9", "max_dpd_days": 45}')
    code, out = run(capsys, "--mode", "gap_analysis", "--input", report, "--rules", rules)
    assert code == 0
    assert out["gaps"][0]["action"] == "Clear the overdue account - it is 45 days past due"


def test_missing_input_file(capsys, tmp_path):
    code, out = run(capsys, "--mode", "gap_analysis", "--input", str(tmp_path / "nope.json"))
    assert code == 1
    assert out["code"] == "INPUT_NOT_FOUND"


def test_invalid_json(capsys, tmp_path):
    path = write(tmp_path, "bad.json", "{not json")
    code, out = run(capsys, "--mode", "gap_analysis", "--input", path)
    assert code == 1
    assert out["code"] == "INVALID_JSON"


def test_input_must_be_a_json_object(capsys, tmp_path):
    path = write(tmp_path, "list.json", "[1, 2, 3]")
    code, out = run(capsys, "--mode", "eligibility", "--input", path)
    assert code == 1
    assert out["code"] == "INVALID_INPUT"


def test_missing_field_is_a_clean_error(capsys, tmp_path):
    path = write(tmp_path, "partial.json", '{"customer_id": "C7", "age": 30}')
    code, out = run(capsys, "--mode", "eligibility", "--input", path)
    assert code == 1
    assert out["code"] == "RULE_ENGINE_ERROR"
    assert "cibil_score" in out["error"]


def test_missing_rules_file(capsys, tmp_path):
    code, out = run(capsys, "--mode", "gap_analysis", "--input", str(EXAMPLES / "report.json"),
                    "--rules", str(tmp_path / "missing.yaml"))
    assert code == 1
    assert "not found" in out["error"]


def test_unknown_mode_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        engine.main(["--mode", "magic", "--input", str(EXAMPLES / "report.json")])
    assert exc.value.code == 2
