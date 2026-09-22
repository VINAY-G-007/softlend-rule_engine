"""Command-line entry point for the Softlend rule engine.

Usage:
    python engine.py --mode gap_analysis --input examples/report.json
    python engine.py --mode eligibility  --input examples/profile.json
    python engine.py --mode gap_analysis --input examples/report.json --rules rules.yaml

Works from any folder: by default the rules are read from the rules.yaml that
sits next to this file, not from the current working directory.
"""

import argparse
import json
import sys
from pathlib import Path

from rule_engine import gap_analysis, eligibility
from rule_engine.loader import load_rules
from rule_engine.errors import RuleEngineError

DEFAULT_RULES = Path(__file__).resolve().parent / "rules.yaml"

# mode name -> the function that runs it
MODES = {
    "gap_analysis": gap_analysis.run,
    "eligibility": eligibility.run,
}


def fail(message, code):
    """Print a structured JSON error (never a raw traceback) and return exit code 1."""
    print(json.dumps({"error": message, "code": code}, indent=2))
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Softlend credit rule engine")
    parser.add_argument("--mode", required=True, choices=list(MODES))
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--rules", default=str(DEFAULT_RULES),
                        help="Path to rules config (default: rules.yaml next to engine.py)")
    args = parser.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            record = json.load(f)
    except FileNotFoundError:
        return fail(f"Input file not found: {args.input}", "INPUT_NOT_FOUND")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return fail(f"Input file is not valid JSON: {e}", "INVALID_JSON")
    except OSError as e:
        return fail(f"Could not read input file: {e}", "INPUT_NOT_READABLE")

    if not isinstance(record, dict):
        return fail('Input JSON must be an object, like {"customer_id": "C001", ...}', "INVALID_INPUT")

    try:
        config = load_rules(args.rules)
        result = MODES[args.mode](record, config)
    except RuleEngineError as e:
        # Handled, expected failure (missing field, bad config) -> clean JSON, no crash.
        return fail(str(e), "RULE_ENGINE_ERROR")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
