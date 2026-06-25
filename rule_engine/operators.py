"""Operator registry: the heart of the rule engine.

Each operator answers ONE yes/no question: "does this field value satisfy
this rule?". Operators are looked up by name (the `operator:` key in
rules.yaml), so the engine never contains any business threshold. Adding a
new *rule* is pure YAML; the only time we touch code is to add a new *kind*
of comparison here.

Every operator has the same signature:  fn(field_value, rule, record)
  - field_value : the value of rule["field"] pulled from the input
  - rule        : the rule dict from YAML (gives us value / min / max / etc.)
  - record      : the whole input record (needed by lte_multiplier, which
                  compares one field against another)
"""

from .errors import RuleConfigError, MissingFieldError


def _num(value):
    """Coerce to float for numeric comparison, with a clear error if it can't."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise RuleConfigError(f"Expected a number but got {value!r}")


def op_gt(field_value, rule, record):
    return _num(field_value) > _num(rule["value"])


def op_lt(field_value, rule, record):
    return _num(field_value) < _num(rule["value"])


def op_gte(field_value, rule, record):
    return _num(field_value) >= _num(rule["value"])


def op_lte(field_value, rule, record):
    return _num(field_value) <= _num(rule["value"])


def op_eq(field_value, rule, record):
    return field_value == rule["value"]


def op_between(field_value, rule, record):
    return _num(rule["min"]) <= _num(field_value) <= _num(rule["max"])


def op_in(field_value, rule, record):
    return field_value in rule["values"]


def op_lte_multiplier(field_value, rule, record):
    """field <= record[multiplier_field] * multiplier
    e.g. requested_amount <= monthly_income * 10
    """
    other_field = rule["multiplier_field"]
    if other_field not in record:
        raise MissingFieldError(other_field)
    cap = _num(record[other_field]) * _num(rule["multiplier"])
    return _num(field_value) <= cap


# name (as written in rules.yaml)  ->  function
OPERATORS = {
    "gt": op_gt,
    "lt": op_lt,
    "gte": op_gte,
    "lte": op_lte,
    "eq": op_eq,
    "between": op_between,
    "in": op_in,
    "lte_multiplier": op_lte_multiplier,
}


def evaluate(field_value, rule, record):
    """Dispatch to the operator named in the rule and return True/False."""
    name = rule["operator"]
    if name not in OPERATORS:
        raise RuleConfigError(f"Unknown operator: {name!r}")
    return OPERATORS[name](field_value, rule, record)
