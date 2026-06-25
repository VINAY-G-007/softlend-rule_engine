"""Bonus: HTTP endpoint exposing both engine modes via a single route.

Run:
    uvicorn api:app --reload

Then POST to http://127.0.0.1:8000/analyse with a JSON body whose "mode"
field selects gap_analysis or eligibility, and the rest are the input fields:

    { "mode": "gap_analysis", "customer_id": "C001",
      "credit_utilisation_pct": 87, "missed_payments_12m": 2,
      "written_off_accounts": 0, "credit_age_months": 14,
      "hard_enquiries_6m": 2 }

Interactive docs are auto-generated at http://127.0.0.1:8000/docs
"""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from rule_engine import gap_analysis, eligibility
from rule_engine.loader import load_rules
from rule_engine.errors import RuleEngineError

app = FastAPI(title="Softlend Rule Engine API")

# Rules are loaded once at startup, exactly like the CLI.
CONFIG = load_rules("rules.yaml")

MODES = {
    "gap_analysis": gap_analysis.run,
    "eligibility": eligibility.run,
}


@app.post("/analyse")
def analyse(payload: Dict[str, Any]):
    mode = payload.get("mode")
    if mode not in MODES:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Unknown or missing mode: {mode!r}", "code": "UNKNOWN_MODE"},
        )

    # Everything except "mode" is the input record for the engine.
    record = {k: v for k, v in payload.items() if k != "mode"}

    try:
        return MODES[mode](record, CONFIG)
    except RuleEngineError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "code": "RULE_ENGINE_ERROR"},
        )
