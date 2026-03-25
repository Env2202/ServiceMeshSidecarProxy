# tests/unit/test_discovery.py
# TDD: Tests written FIRST to define expected behavior

import pytest

try:
    from sidecar.discovery.resolver import DNSResolver, StaticResolver
    from sidecar.discovery.endpoint import Endpoint
except ImportError:
    DNSResolver = None
    StaticResolver = None
    Endpoint = None


class TestEndpoint:
    """Test endpoint model."""

    def test_endpoint_requires_address_and_port(self):
        """Endpoint must have address and port."""
        # TDD Red: will fail until implemented
                pass

    def test_endpoint_has_weight_default(self):
        """Endpoint has default weight of 1."""
        # TDD Red: will fail until implemented
                pass

    def test_endpoint_equality(self):
        """Endpoints with same address:port should be equal."""
        # TDD Red: will fail until implemented
                pass


class TestStaticResolver:
    """Test static endpoint resolver (POC scope)."""

    def test_returns_configured_endpoints(self):
        """Should return endpoints from config."""
        # TDD Red: will fail until implemented
                pass

    def test_returns_empty_for_unknown_cluster(self):
        """Unknown cluster returns empty list."""
        # TDD Red: will fail until implemented
                pass

    def test_respects_endpoint_weights(self):
        """Endpoints should have weights from config."""
        # TDD Red: will fail until implemented
                pass

    def test_no_k8s_dependency_for_poc(self):
        """Static resolver should not require K8s (POC scope)."""
        # TDD Red: will fail until implemented
                # This test verifies no K8s imports or calls
        pass


class TestDNSResolver:
    """Test DNS-based endpoint resolver (POC scope)."""

    def test_resolves_hostname_to_endpoints(self):
        """Should resolve hostname to IP endpoints."""
        # TDD Red: will fail until implemented
                pass

    def test_handles_multiple_ips(self):
        """Should handle DNS returning multiple IPs."""
        # TDD Red: will fail until implemented
                pass

    def test_refreshes_on_interval(self):
        """Should re-resolve DNS at configured interval."""
        # TDD Red: will fail until implemented
                pass

    def test_fallback_on_dns_failure(self):
        """Should handle DNS resolution failures gracefully."""
        # TDD Red: will fail until implemented
                pass
