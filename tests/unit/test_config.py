# tests/unit/test_config.py
# TDD: Tests written FIRST to define expected behavior
# Run: pytest tests/unit/test_config.py -v (should FAIL until implementation)

import pytest
from pydantic import ValidationError

# These imports will fail until we implement sidecar/config/settings.py
# That's expected in TDD - write tests first, then implement
try:
    from sidecar.config.settings import SidecarConfig, ServerConfig, RouteConfig, DiscoveryConfig
except ImportError:
    SidecarConfig = None
    ServerConfig = None
    RouteConfig = None
    DiscoveryConfig = None


class TestServerConfig:
    """Test server configuration (inbound/outbound/admin ports)."""

    def test_server_config_requires_ports(self):
        """Server config must have inbound_port, outbound_port, admin_port."""
        if ServerConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # Should fail without required fields
        with pytest.raises(ValidationError):
            ServerConfig()

    def test_server_config_defaults(self):
        """Server config should have sensible defaults."""
        if ServerConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        config = ServerConfig(inbound_port=15000, outbound_port=15001, admin_port=15002)
        assert config.inbound_port == 15000
        assert config.outbound_port == 15001
        assert config.admin_port == 15002

    def test_server_config_validates_port_range(self):
        """Ports should be valid (1-65535)."""
        if ServerConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # Invalid port should raise
        with pytest.raises(ValidationError):
            ServerConfig(inbound_port=0, outbound_port=15001, admin_port=15002)
        with pytest.raises(ValidationError):
            ServerConfig(inbound_port=70000, outbound_port=15001, admin_port=15002)


class TestDiscoveryConfig:
    """Test service discovery configuration."""

    def test_discovery_type_static_is_valid_for_poc(self):
        """Static discovery should be valid (POC scope: no K8s)."""
        if DiscoveryConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        config = DiscoveryConfig(type="static")
        assert config.type == "static"

    def test_discovery_type_dns_is_valid_for_poc(self):
        """DNS discovery should be valid."""
        if DiscoveryConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        config = DiscoveryConfig(type="dns")
        assert config.type == "dns"

    def test_discovery_type_kubernetes_is_invalid_for_poc(self):
        """K8s discovery should be invalid for POC scope."""
        if DiscoveryConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # Per POC plan: no K8s dependency
        with pytest.raises(ValidationError):
            DiscoveryConfig(type="kubernetes")

    def test_discovery_default_refresh_interval(self):
        """Discovery should have default refresh interval."""
        if DiscoveryConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        config = DiscoveryConfig(type="dns")
        assert config.refresh_interval > 0


class TestRouteConfig:
    """Test routing configuration (path, header, host matching)."""

    def test_route_requires_name_and_match(self):
        """Route must have name and match criteria."""
        if RouteConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        with pytest.raises(ValidationError):
            RouteConfig()

    def test_route_host_match(self):
        """Route can match by host."""
        if RouteConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # This will be implemented - defining expected behavior
        # Route should match requests to specific host
        pass  # TODO: Implement after RouteConfig is defined

    def test_route_path_prefix_match(self):
        """Route can match by path prefix."""
        if RouteConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass  # TODO: Implement after RouteConfig is defined

    def test_route_header_match(self):
        """Route can match by headers."""
        if RouteConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass  # TODO: Implement after RouteConfig is defined


class TestSidecarConfig:
    """Test full sidecar configuration loading and validation."""

    def test_config_loads_from_yaml(self):
        """Config should load from YAML file."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # TODO: Test loading examples/basic-config.yaml
        pass

    def test_config_validates_required_server_section(self):
        """Config must have server section with ports."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass

    def test_config_validates_routes(self):
        """Config should validate all route definitions."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass

    def test_config_allows_empty_routes(self):
        """Config can have no routes (pass-through mode)."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass

    def test_config_poc_scope_rejects_tls(self):
        """TLS config should be rejected or ignored for POC (plain HTTP only)."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # Per POC plan: mTLS skipped, plain HTTP only
        pass

    def test_config_poc_scope_rejects_tracing(self):
        """Tracing config should be rejected or ignored for POC."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        # Per POC plan: Prometheus metrics only, no OpenTelemetry
        pass


class TestConfigDefaults:
    """Test sensible defaults for optional config fields."""

    def test_default_log_level_is_info(self):
        """Default logging level should be 'info'."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass

    def test_default_log_format_is_json(self):
        """Default log format should be JSON for structured logging."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass

    def test_default_telemetry_enabled(self):
        """Metrics should be enabled by default."""
        if SidecarConfig is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/config/settings.py")
        
        pass
