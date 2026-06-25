"""Command-line entry point for the Softlend rule engine.

Usage:
    python engine.py --mode gap_analysis --input examples/report.json
    python engine.py --mode eligibility  --input examples/profile.json
    python engine.py --mode gap_analysis --input examples/report.json --rules rules.yaml
"""

import argparse
import json
import sys

from rule_engine import gap_analysis, eligibility
from rule_engine.loader import load_rules
from rule_engine.errors import RuleEngineError

# mode name -> the function that runs it
MODES = {
    "gap_analysis": gap_analysis.run,
    "eligibility": eligibility.run,
}


def main():
    parser = argparse.ArgumentParser(description="Softlend credit rule engine")
    parser.add_argument("--mode", required=True, choices=list(MODES))
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--rules", default="rules.yaml", help="Path to rules config")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            record = json.load(f)
        config = load_rules(args.rules)
        result = MODES[args.mode](record, config)
    except RuleEngineError as e:
        # Handled, expected failure (missing field, bad config) -> clean JSON, no crash.
        print(json.dumps({"error": str(e), "code": "RULE_ENGINE_ERROR"}, indent=2))
        sys.exit(1)
    except FileNotFoundError:
        print(json.dumps({"error": f"Input file not found: {args.input}",
                          "code": "INPUT_NOT_FOUND"}, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
