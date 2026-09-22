"""pytest configuration.

This file is intentionally tiny. Because it sits in the project root, pytest
adds the root folder to sys.path, so the tests can import `rule_engine`,
`engine` and `api` without installing the project as a package.
"""
