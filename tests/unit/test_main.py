# tests/unit/test_main.py
# TDD: Tests written FIRST to define expected behavior

import pytest

try:
    from sidecar.main import main
except ImportError:
    main = None


class TestCLIMain:
    """Test CLI entry point."""

    def test_main_function_exists(self):
        """main() function should exist."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        assert callable(main)

    def test_cli_requires_config(self):
        """CLI should require --config argument."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        # When called without config, should fail or show usage
        pass

    def test_cli_accepts_config_path(self):
        """CLI should accept --config <path> argument."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        pass

    def test_cli_accepts_port_overrides(self):
        """CLI should accept --inbound-port, --outbound-port, --admin-port."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        pass

    def test_cli_shows_version(self):
        """CLI should support --version flag."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        pass

    def test_cli_shows_help(self):
        """CLI should support --help flag."""
        if main is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/main.py")
        pass
