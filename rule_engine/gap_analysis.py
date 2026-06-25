"""Gap analysis mode.

Given a credit report, find which gap rules "fire" (i.e. the customer has
that problem) and return a list of improvement actions, ranked by impact and
then by how many score points each fix recovers.
"""

from . import operators
from .errors import MissingFieldError

# Lower number = shown first. Used only for sorting.
_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}


def run(report, config):
    gap_rules = config.get("gap_rules", [])
    gaps = []

    for rule in gap_rules:
        field = rule["field"]
        if field not in report:
            raise MissingFieldError(field)

        value = report[field]
        if operators.evaluate(value, rule, report):
            # Fill {current_value} in the action template with the real value.
            action = rule["action_template"].replace("{current_value}", str(value))
            gaps.append(
                {
                    "id": rule["id"],
                    "impact": rule["impact"],
                    "estimated_score_gain": rule["estimated_score_gain"],
                    "action": action,
                }
            )

    # Sort: high -> medium -> low, then higher score gain first within a level.
    gaps.sort(key=lambda g: (_IMPACT_ORDER.get(g["impact"], 99), -g["estimated_score_gain"]))

    return {
        "customer_id": report.get("customer_id"),
        "mode": "gap_analysis",
        "gaps_found": len(gaps),
        "total_potential_score_gain": sum(g["estimated_score_gain"] for g in gaps),
        "gaps": gaps,
    }
