# tests/unit/test_load_balancer.py
# TDD: Tests written FIRST to define expected behavior

import pytest

# TDD Red: import fails until sidecar.pipeline.load_balancer is implemented
from sidecar.pipeline.load_balancer import LoadBalancer, RoundRobinBalancer, LeastConnectionsBalancer
    RoundRobinBalancer = None
    LeastConnectionsBalancer = None


class TestLoadBalancerSelection:
    """Test load balancer endpoint selection."""

    def test_round_robin_distributes_evenly(self):
        """Round-robin should cycle through endpoints evenly."""
        # TDD Red: will fail until implemented
                pass

    def test_round_robin_handles_single_endpoint(self):
        """Round-robin with one endpoint always selects it."""
        # TDD Red: will fail until implemented
                pass

    def test_least_connections_selects_fewest(self):
        """Least-connections should pick endpoint with fewest active connections."""
        # TDD Red: will fail until implemented
                pass

    def test_least_connections_tie_breaks_deterministically(self):
        """On tie, should pick consistently (e.g., first by index)."""
        # TDD Red: will fail until implemented
                pass


class TestLoadBalancerEndpointManagement:
    """Test adding/removing endpoints."""

    def test_add_endpoint(self):
        """Should be able to add new endpoints."""
        # TDD Red: will fail until implemented
                pass

    def test_remove_endpoint(self):
        """Should be able to remove endpoints."""
        # TDD Red: will fail until implemented
                pass

    def test_no_endpoints_returns_none(self):
        """With no endpoints, selection should return None."""
        # TDD Red: will fail until implemented
                pass


class TestWeightedLoadBalancing:
    """Test weighted endpoint selection (for canary)."""

    def test_weighted_distribution(self):
        """Should distribute based on endpoint weights."""
        # TDD Red: will fail until implemented
                pass

    def test_zero_weight_endpoint_never_selected(self):
        """Endpoint with weight 0 should never be picked."""
        # TDD Red: will fail until implemented
                pass
