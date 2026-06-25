"""Custom exceptions.

These exist so the engine fails with a clear, specific message instead of
letting a raw KeyError / TypeError leak out. The CLI catches these at the
boundary and turns them into clean JSON errors, so the program never crashes
with an ugly traceback (this is exactly the "missing field" test case).
"""


class RuleEngineError(Exception):
    """Base class for every error the engine raises on purpose."""


class MissingFieldError(RuleEngineError):
    """A rule needs a field that the input record does not contain."""

    def __init__(self, field):
        self.field = field
        super().__init__(f"Required field '{field}' is missing from the input")


class RuleConfigError(RuleEngineError):
    """rules.yaml is malformed: unknown operator, empty file, bad shape, etc."""
