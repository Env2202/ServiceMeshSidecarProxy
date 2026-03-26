# tests/unit/test_main.py
# TDD: Tests written FIRST to define expected behavior
# Run: python3 -m pytest tests/unit/test_main.py -v -o "addopts="

import pytest

# TDD Red: import fails until sidecar.main is implemented
from sidecar.main import main


class TestCLIMain:
    """Test CLI entry point."""

    def test_main_function_exists(self):
        """main() function should exist."""
        assert callable(main)

    def test_cli_requires_config(self):
        """CLI should require --config argument."""
        pass

    def test_cli_accepts_config_path(self):
        """CLI should accept --config <path> argument."""
        pass

    def test_cli_accepts_port_overrides(self):
        """CLI should accept --inbound-port, --outbound-port, --admin-port."""
        pass

    def test_cli_shows_version(self):
        """CLI should support --version flag."""
        pass

    def test_cli_shows_help(self):
        """CLI should support --help flag."""
        pass
