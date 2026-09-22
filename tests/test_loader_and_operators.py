"""Tests for loading rules.yaml and for the operator registry."""

from pathlib import Path

import pytest

from rule_engine import operators
from rule_engine.errors import MissingFieldError, RuleConfigError
from rule_engine.loader import load_rules

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.yaml"


# --------------------------------------------------------------------------
# Loader
# --------------------------------------------------------------------------
def test_real_rules_file_loads():
    config = load_rules(RULES_PATH)
    assert len(config["gap_rules"]) == 5
    assert config["eligibility_rules"][0]["logic"] == "AND"


@pytest.mark.parametrize("content, message", [
    ("", "empty"),
    ("gap_rules: [unclosed", "not valid YAML"),
    ("- just\n- a list\n", "must be a mapping"),
    ("something_else: 1\n", "must define"),
])
def test_bad_rules_files_raise_config_error(tmp_path, content, message):
    path = tmp_path / "rules.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(RuleConfigError, match=message):
        load_rules(path)


def test_missing_rules_file(tmp_path):
    with pytest.raises(RuleConfigError, match="not found"):
        load_rules(tmp_path / "missing.yaml")


# --------------------------------------------------------------------------
# Operators
# --------------------------------------------------------------------------
@pytest.mark.parametrize("value, rule, expected", [
    (31, {"operator": "gt", "value": 30}, True),
    (30, {"operator": "gt", "value": 30}, False),
    (35, {"operator": "lt", "value": 36}, True),
    (650, {"operator": "gte", "value": 650}, True),
    (649, {"operator": "gte", "value": 650}, False),
    (0.5, {"operator": "lte", "value": 0.5}, True),
    (0, {"operator": "eq", "value": 0}, True),
    (1, {"operator": "eq", "value": 0}, False),
    (21, {"operator": "between", "min": 21, "max": 60}, True),
    (61, {"operator": "between", "min": 21, "max": 60}, False),
    ("salaried", {"operator": "in", "values": ["salaried", "self_employed"]}, True),
    ("student", {"operator": "in", "values": ["salaried", "self_employed"]}, False),
    ("87", {"operator": "gt", "value": 30}, True),  # numeric strings are accepted
])
def test_operators(value, rule, expected):
    assert operators.evaluate(value, rule, {}) is expected


def test_lte_multiplier_compares_two_fields():
    rule = {"operator": "lte_multiplier", "multiplier_field": "monthly_income", "multiplier": 10}
    assert operators.evaluate(600000, rule, {"monthly_income": 60000}) is True
    assert operators.evaluate(600001, rule, {"monthly_income": 60000}) is False


def test_lte_multiplier_needs_the_other_field():
    rule = {"operator": "lte_multiplier", "multiplier_field": "monthly_income", "multiplier": 10}
    with pytest.raises(MissingFieldError):
        operators.evaluate(100, rule, {})


def test_unknown_operator_is_reported():
    with pytest.raises(RuleConfigError, match="Unknown operator"):
        operators.evaluate(5, {"operator": "approximately", "value": 5}, {})


def test_non_numeric_value_is_reported():
    with pytest.raises(RuleConfigError, match="Expected a number"):
        operators.evaluate("high", {"operator": "gt", "value": 30}, {})
