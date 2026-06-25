"""Test suite for the Softlend rule engine.

Covers the six cases required by the brief plus the risk-score bonus.
Run from the project root with:  pytest -v
"""

import os
import pytest

from rule_engine import gap_analysis, eligibility
from rule_engine.loader import load_rules
from rule_engine.errors import MissingFieldError

# Load the real rules.yaml once, relative to this file (works from any cwd).
RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules.yaml")
CONFIG = load_rules(RULES_PATH)


# --------------------------------------------------------------------------
# Test 1: every gap rule fires -> 5 gaps, sorted high->medium then by gain
# --------------------------------------------------------------------------
def test_all_gap_rules_fire():
    report = {
        "customer_id": "C100",
        "credit_utilisation_pct": 90,   # > 30  -> fires (high, 35)
        "missed_payments_12m": 3,       # > 0   -> fires (high, 25)
        "written_off_accounts": 1,      # > 0   -> fires (high, 40)
        "credit_age_months": 12,        # < 36  -> fires (medium, 10)
        "hard_enquiries_6m": 5,         # > 3   -> fires (medium, 10)
    }
    result = gap_analysis.run(report, CONFIG)

    assert result["gaps_found"] == 5
    assert result["total_potential_score_gain"] == 120
    # Sorted: high impact first, highest score gain first within a level.
    ids = [g["id"] for g in result["gaps"]]
    assert ids == [
        "written_off_account",   # high, 40
        "high_utilisation",      # high, 35
        "missed_payments",       # high, 25
        "short_credit_age",      # medium, 10
        "too_many_enquiries",    # medium, 10
    ]


# --------------------------------------------------------------------------
# Test 2: clean report -> no gaps
# --------------------------------------------------------------------------
def test_no_gaps_found():
    report = {
        "customer_id": "C101",
        "credit_utilisation_pct": 10,
        "missed_payments_12m": 0,
        "written_off_accounts": 0,
        "credit_age_months": 60,
        "hard_enquiries_6m": 1,
    }
    result = gap_analysis.run(report, CONFIG)

    assert result["gaps_found"] == 0
    assert result["gaps"] == []
    assert result["total_potential_score_gain"] == 0


# --------------------------------------------------------------------------
# Test 3: {current_value} in the action template is replaced with real value
# --------------------------------------------------------------------------
def test_action_template_substitution():
    report = {
        "customer_id": "C102",
        "credit_utilisation_pct": 87,
        "missed_payments_12m": 0,
        "written_off_accounts": 0,
        "credit_age_months": 60,
        "hard_enquiries_6m": 0,
    }
    result = gap_analysis.run(report, CONFIG)
    action = result["gaps"][0]["action"]

    assert "87" in action                 # the value was substituted in
    assert "{current_value}" not in action  # no leftover placeholder


# --------------------------------------------------------------------------
# Test 4: a fully-qualified customer -> eligible, no fail reasons
# --------------------------------------------------------------------------
def test_all_eligibility_rules_pass():
    profile = {
        "customer_id": "C103",
        "age": 30,
        "cibil_score": 720,
        "monthly_income": 60000,
        "foir": 0.30,
        "employment_type": "salaried",
        "written_off_accounts": 0,
        "requested_amount": 300000,   # <= 60000 * 10
    }
    result = eligibility.run(profile, CONFIG)

    assert result["eligible"] is True
    assert result["fail_reasons"] == []
    assert result["risk_score"] == 0.0


# --------------------------------------------------------------------------
# Test 5: a customer who fails several rules -> all failures listed
# --------------------------------------------------------------------------
def test_multiple_eligibility_rules_fail():
    profile = {
        "customer_id": "C104",
        "age": 19,                    # fails (must be 21-60)
        "cibil_score": 600,           # fails (>= 650)
        "monthly_income": 60000,
        "foir": 0.70,                 # fails (<= 0.5)
        "employment_type": "student",  # fails (salaried/self_employed)
        "written_off_accounts": 1,    # fails (== 0)
        "requested_amount": 5000000,  # fails (<= income * 10 = 600000)
    }
    result = eligibility.run(profile, CONFIG)

    assert result["eligible"] is False
    assert set(result["fail_reasons"]) == {
        "age", "cibil_score", "foir",
        "employment_type", "no_written_off_accounts", "loan_amount_cap",
    }
    assert result["risk_score"] == 100.0  # every weighted rule failed


# --------------------------------------------------------------------------
# Test 6: a missing input field raises a clear error (does not crash) - BOTH modes
# --------------------------------------------------------------------------
def test_missing_field_gap_analysis():
    report = {"customer_id": "C105", "credit_utilisation_pct": 50}  # other fields absent
    with pytest.raises(MissingFieldError):
        gap_analysis.run(report, CONFIG)


def test_missing_field_eligibility():
    profile = {"customer_id": "C106", "age": 30}  # cibil_score etc. absent
    with pytest.raises(MissingFieldError):
        eligibility.run(profile, CONFIG)
