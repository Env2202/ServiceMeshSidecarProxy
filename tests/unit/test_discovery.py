# tests/unit/test_discovery.py
# TDD: Tests written FIRST to define expected behavior
# Run: python3 -m pytest tests/unit/test_discovery.py -v -o "addopts="

import pytest

# TDD Red: import fails until sidecar.discovery is implemented
from sidecar.discovery.resolver import DNSResolver, StaticResolver
from sidecar.discovery.endpoint import Endpoint


class TestEndpoint:
    """Test endpoint model."""

    def test_endpoint_requires_address_and_port(self):
        """Endpoint must have address and port."""
        pass

    def test_endpoint_has_weight_default(self):
        """Endpoint has default weight of 1."""
        pass

    def test_endpoint_equality(self):
        """Endpoints with same address:port should be equal."""
        pass


class TestStaticResolver:
    """Test static endpoint resolver (POC scope)."""

    def test_returns_configured_endpoints(self):
        """Should return endpoints from config."""
        pass

    def test_returns_empty_for_unknown_cluster(self):
        """Unknown cluster returns empty list."""
        pass

    def test_respects_endpoint_weights(self):
        """Endpoints should have weights from config."""
        pass

    def test_no_k8s_dependency_for_poc(self):
        """Static resolver should not require K8s (POC scope)."""
        pass


class TestDNSResolver:
    """Test DNS-based endpoint resolver (POC scope)."""

    def test_resolves_hostname_to_endpoints(self):
        """Should resolve hostname to IP endpoints."""
        pass

    def test_handles_multiple_ips(self):
        """Should handle DNS returning multiple IPs."""
        pass

    def test_refreshes_on_interval(self):
        """Should re-resolve DNS at configured interval."""
        pass

    def test_fallback_on_dns_failure(self):
        """Should handle DNS resolution failures gracefully."""
        pass
