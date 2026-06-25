# Softlend Rule Engine

A configurable, two-mode rule engine for Softlend's credit flow.

- **Gap analysis** — given a customer's credit report, find what is dragging
  their score down and return a ranked list of improvement actions.
- **Eligibility** — given a customer profile, decide whether they qualify for
  a loan right now, and if not, exactly which rules failed and why.

**The core idea:** every threshold and rule lives in `rules.yaml`. The Python
code contains no business numbers at all. Changing a credit policy, tweaking a
cutoff, or adding a new rule means editing YAML only — no code change, no
redeploy of logic.

---

## Project structure

```
softlend-rule_engine/
├── engine.py              # CLI entry point (runs either mode)
├── api.py                 # Bonus: FastAPI POST /analyse endpoint
├── rules.yaml             # ALL rules & thresholds (the only place numbers live)
├── requirements.txt
├── rule_engine/
│   ├── operators.py       # operator registry — the heart of the engine
│   ├── loader.py          # loads & validates rules.yaml
│   ├── gap_analysis.py    # gap analysis mode
│   ├── eligibility.py     # eligibility mode (with weighted risk score)
│   └── errors.py          # custom exceptions for clean failures
├── examples/
│   ├── report.json        # sample credit report (gap analysis input)
│   └── profile.json       # sample customer profile (eligibility input)
└── tests/
    └── test_engine.py     # 8 tests covering both modes + edge cases
```

---

## Setup

```bash
# (recommended) create and activate a virtual environment
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

## How to run

```bash
# Gap analysis
python engine.py --mode gap_analysis --input examples/report.json

# Eligibility
python engine.py --mode eligibility  --input examples/profile.json

# Use a different rules file (optional)
python engine.py --mode gap_analysis --input examples/report.json --rules rules.yaml
```

Output is printed to the terminal as JSON. To save it to a file, redirect it:

```bash
python engine.py --mode gap_analysis --input examples/report.json > gap_output.json
```

---

## Sample output

**Gap analysis** (`examples/report.json`):

```json
{
  "customer_id": "C001",
  "mode": "gap_analysis",
  "gaps_found": 3,
  "total_potential_score_gain": 70,
  "gaps": [
    { "id": "high_utilisation", "impact": "high", "estimated_score_gain": 35,
      "action": "Reduce credit card utilisation from 87% to below 30%" },
    { "id": "missed_payments", "impact": "high", "estimated_score_gain": 25,
      "action": "Clear 2 overdue EMI(s) to remove the missed-payment flag" },
    { "id": "short_credit_age", "impact": "medium", "estimated_score_gain": 10,
      "action": "Avoid closing old accounts - your oldest account is only 14 months old" }
  ]
}
```

**Eligibility** (`examples/profile.json`):

```json
{
  "customer_id": "C001",
  "mode": "eligibility",
  "eligible": false,
  "risk_score": 30.0,
  "rules": [
    { "rule": "age", "passed": true },
    { "rule": "cibil_score", "passed": false, "reason": "CIBIL score must be at least 650" },
    { "rule": "foir", "passed": true },
    { "rule": "employment_type", "passed": true },
    { "rule": "no_written_off_accounts", "passed": true },
    { "rule": "loan_amount_cap", "passed": true }
  ],
  "fail_reasons": ["cibil_score"],
  "next_step": "Not eligible yet. Fix: CIBIL score must be at least 650. Run gap_analysis for a plan."
}
```

---

## Operators

The engine supports these operators (used via the `operator:` key in `rules.yaml`):

| Operator         | Meaning                       | Example                                          |
|------------------|-------------------------------|--------------------------------------------------|
| `gt`             | greater than                  | `credit_utilisation_pct > 30`                    |
| `lt`             | less than                     | `credit_age_months < 36`                         |
| `gte`            | greater than or equal         | `cibil_score >= 650`                             |
| `lte`            | less than or equal            | `foir <= 0.5`                                    |
| `eq`             | equal                         | `written_off_accounts == 0`                      |
| `between`        | inclusive range (`min`–`max`) | `21 <= age <= 60`                                |
| `in`             | value is in a list            | `employment_type in [salaried, self_employed]`   |
| `lte_multiplier` | field ≤ another field × N     | `requested_amount <= monthly_income * 10`        |

---

## How to add a new rule (no code changes)

**A new gap rule** — add an entry under `gap_rules` in `rules.yaml`:

```yaml
  - id: high_dpd
    field: max_dpd_days          # field name expected in the input JSON
    operator: gt
    value: 30
    impact: high
    estimated_score_gain: 20
    action_template: "Clear the overdue account - it is {current_value} days past due"
```

**A new eligibility rule** — add an entry under a group's `rules` list:

```yaml
      - id: min_income
        field: monthly_income
        operator: gte
        value: 15000
        weight: 0.15                # optional, used by the risk score
        message: "Monthly income must be at least 15,000"
```

That's it — the engine picks it up at startup. The only time you touch Python
is to add a brand-new *kind* of comparison (a new operator) in
`rule_engine/operators.py`.

---

## Running the tests

```bash
pytest -v
```

Eight tests cover: all gap rules firing (with correct sorting), no gaps,
`{current_value}` substitution, all eligibility rules passing, multiple rules
failing, and a missing input field raising a clean error in **both** modes.

---

## Bonus features

**1. Weighted risk score.** Each eligibility rule can carry a `weight` (0–1) in
`rules.yaml`. The eligibility output includes
`risk_score = (sum of failed weights / sum of all weights) × 100`.

**2. HTTP endpoint.** Both modes are exposed via a single route:

```bash
uvicorn api:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/analyse \
  -H "Content-Type: application/json" \
  -d '{"mode":"gap_analysis","customer_id":"C001","credit_utilisation_pct":87,"missed_payments_12m":2,"written_off_accounts":0,"credit_age_months":14,"hard_enquiries_6m":2}'
```

Interactive API docs are auto-generated at `http://127.0.0.1:8000/docs`.

---

## Design decisions

- **Config-driven, not code-driven.** Rules and thresholds live entirely in
  `rules.yaml`. The engine reads them at startup and evaluates generically, so a
  credit-policy change is a config edit, not a developer task.
- **Operator registry over `if/elif`.** Operators are a dictionary of small
  functions keyed by name. `evaluate()` dispatches by lookup, so adding a
  comparison type is one isolated addition with no branching logic to touch.
- **Uniform operator signature** `(field_value, rule, record)`. Passing the full
  record lets cross-field operators like `lte_multiplier` reference a second
  field without breaking the common interface.
- **Failure messages live in YAML**, so the text a customer sees can change
  without a code change.
- **Errors fail cleanly.** A missing input field raises a specific
  `MissingFieldError` that the CLI/API catch at the boundary and return as a
  structured JSON error — the program never crashes with a raw traceback.
