"""Eligibility mode.

Given a customer profile, evaluate one or more rule groups and decide whether
the customer qualifies for a loan right now. Each group declares its own logic
(AND / OR) in YAML. A customer is eligible only if every group is satisfied.
"""

from . import operators
from .errors import MissingFieldError


def run(profile, config):
    groups = config.get("eligibility_rules", [])

    rule_results = []     # flat list of every rule's pass/fail (matches the brief)
    fail_reasons = []     # ids of rules that failed
    group_outcomes = []   # one True/False per group, combined at the end

    for group in groups:
        logic = group.get("logic", "AND").upper()
        passed_flags = []

        for rule in group.get("rules", []):
            field = rule["field"]
            if field not in profile:
                raise MissingFieldError(field)

            passed = operators.evaluate(profile[field], rule, profile)
            result = {"rule": rule["id"], "passed": passed}
            if not passed:
                # The failure message lives in YAML, so wording/policy changes
                # need no code change.
                result["reason"] = rule.get("message", f"Rule '{rule['id']}' failed")
                fail_reasons.append(rule["id"])

            rule_results.append(result)
            passed_flags.append(passed)

        if logic == "OR":
            group_outcomes.append(any(passed_flags))
        else:  # default AND
            group_outcomes.append(all(passed_flags))

    eligible = all(group_outcomes) if group_outcomes else False

    return {
        "customer_id": profile.get("customer_id"),
        "mode": "eligibility",
        "eligible": eligible,
        "rules": rule_results,
        "fail_reasons": fail_reasons,
        "next_step": _next_step(eligible, rule_results),
    }


def _next_step(eligible, rule_results):
    if eligible:
        return "Customer is eligible. Show available loan offers."
    failed = [r["reason"] for r in rule_results if not r["passed"]]
    return "Not eligible yet. Fix: " + " | ".join(failed) + ". Run gap_analysis for a plan."
