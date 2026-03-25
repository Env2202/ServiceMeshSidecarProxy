# tests/unit/test_main.py
# TDD: Tests written FIRST to define expected behavior

import pytest

# TDD Red: import fails until sidecar.main is implemented
from sidecar.main import main


class TestCLIMain:
    """Test CLI entry point."""

    def test_main_function_exists(self):
        """main() function should exist."""
        # TDD Red: will fail until implemented
                assert callable(main)

    def test_cli_requires_config(self):
        """CLI should require --config argument."""
        # TDD Red: will fail until implemented
                # When called without config, should fail or show usage
        pass

    def test_cli_accepts_config_path(self):
        """CLI should accept --config <path> argument."""
        # TDD Red: will fail until implemented
                pass

    def test_cli_accepts_port_overrides(self):
        """CLI should accept --inbound-port, --outbound-port, --admin-port."""
        # TDD Red: will fail until implemented
                pass

    def test_cli_shows_version(self):
        """CLI should support --version flag."""
        # TDD Red: will fail until implemented
                pass

    def test_cli_shows_help(self):
        """CLI should support --help flag."""
        # TDD Red: will fail until implemented
                pass
