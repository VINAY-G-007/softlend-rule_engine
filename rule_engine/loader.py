"""Loads rules.yaml once at startup and does light sanity-checking.

The whole point of the engine is that thresholds live in YAML, not here.
Changing a cutoff or adding a rule means editing rules.yaml only — this
file never changes.
"""

import yaml

from .errors import RuleConfigError


def load_rules(path):
    """Read the YAML config and return it as a plain dict."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise RuleConfigError(f"Rules file not found: {path}") from None
    except yaml.YAMLError as e:
        raise RuleConfigError(f"Rules file is not valid YAML: {path} ({e})") from None

    if not config:
        raise RuleConfigError(f"Rules file is empty: {path}")

    if not isinstance(config, dict):
        raise RuleConfigError(
            f"Rules file must be a mapping with 'gap_rules' and/or 'eligibility_rules': {path}"
        )

    if "gap_rules" not in config and "eligibility_rules" not in config:
        raise RuleConfigError(
            "Rules file must define 'gap_rules' and/or 'eligibility_rules'"
        )

    return config
