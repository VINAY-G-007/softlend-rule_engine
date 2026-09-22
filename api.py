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

from pathlib import Path
from typing import Annotated, Any, Dict

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from rule_engine import gap_analysis, eligibility
from rule_engine.loader import load_rules
from rule_engine.errors import RuleEngineError

app = FastAPI(
    title="Softlend Rule Engine API",
    description="Config-driven credit gap analysis and loan eligibility. "
                "Every rule and threshold lives in rules.yaml.",
    version="1.1.0",
)

# Rules are loaded once at startup, exactly like the CLI. The path is relative
# to this file, so the server can be started from any folder.
RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"
CONFIG = load_rules(RULES_PATH)

MODES = {
    "gap_analysis": gap_analysis.run,
    "eligibility": eligibility.run,
}

# Ready-made request bodies shown in the "Try it out" panel at /docs.
EXAMPLES = {
    "gap_analysis": {
        "summary": "Gap analysis (examples/report.json)",
        "value": {
            "mode": "gap_analysis", "customer_id": "C001",
            "credit_utilisation_pct": 87, "missed_payments_12m": 2,
            "written_off_accounts": 0, "credit_age_months": 14, "hard_enquiries_6m": 2,
        },
    },
    "eligibility": {
        "summary": "Eligibility (examples/profile.json)",
        "value": {
            "mode": "eligibility", "customer_id": "C001", "age": 29, "cibil_score": 620,
            "monthly_income": 60000, "existing_emis": 15000, "foir": 0.25,
            "employment_type": "salaried", "written_off_accounts": 0, "requested_amount": 400000,
        },
    },
}


@app.get("/", include_in_schema=False)
def root():
    """Send visitors of the bare URL to the interactive docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
def health():
    """Liveness check."""
    return {"status": "ok"}


@app.post("/analyse", tags=["engine"])
def analyse(payload: Annotated[Dict[str, Any], Body(openapi_examples=EXAMPLES)]):
    """Run gap_analysis or eligibility on the fields in the request body."""
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
