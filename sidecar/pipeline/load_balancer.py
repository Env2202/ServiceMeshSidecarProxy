# sidecar/pipeline/load_balancer.py - Load balancer algorithms
# Implements round-robin and least-connections per plan

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random


@dataclass
class Endpoint:
    """Represents a backend endpoint."""
    address: str
    port: int
    weight: int = 1
    active_connections: int = 0
    healthy: bool = True

    @property
    def url(self) -> str:
        """Get full URL for this endpoint."""
        return f"http://{self.address}:{self.port}"

    def __hash__(self):
        return hash((self.address, self.port))

    def __eq__(self, other):
        if not isinstance(other, Endpoint):
            return False
        return self.address == other.address and self.port == other.port


class LoadBalancer:
    """Base class for load balancers."""

    def __init__(self, endpoints: List[Endpoint]):
        self.endpoints = endpoints or []

    def select(self, request: Any = None) -> Optional[Endpoint]:
        """Select an endpoint for the request. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement select()")

    def add_endpoint(self, endpoint: Endpoint):
        """Add a new endpoint."""
        if endpoint not in self.endpoints:
            self.endpoints.append(endpoint)

    def remove_endpoint(self, endpoint: Endpoint):
        """Remove an endpoint."""
        if endpoint in self.endpoints:
            self.endpoints.remove(endpoint)

    def get_healthy_endpoints(self) -> List[Endpoint]:
        """Return only healthy endpoints."""
        return [e for e in self.endpoints if e.healthy]


class RoundRobinBalancer(LoadBalancer):
    """Round-robin load balancer - cycles through endpoints evenly."""

    def __init__(self, endpoints: List[Endpoint]):
        super().__init__(endpoints)
        self._current_index = 0

    def select(self, request: Any = None) -> Optional[Endpoint]:
        """Select next endpoint in round-robin fashion."""
        healthy = self.get_healthy_endpoints()
        if not healthy:
            return None

        if self._current_index >= len(healthy):
            self._current_index = 0

        endpoint = healthy[self._current_index]
        self._current_index = (self._current_index + 1) % len(healthy)
        return endpoint


class LeastConnectionsBalancer(LoadBalancer):
    """Least-connections load balancer - picks endpoint with fewest active connections."""

    def select(self, request: Any = None) -> Optional[Endpoint]:
        """Select endpoint with fewest active connections."""
        healthy = self.get_healthy_endpoints()
        if not healthy:
            return None

        # Pick endpoint with fewest active connections
        # On tie, pick first one (deterministic)
        return min(healthy, key=lambda e: e.active_connections)


class WeightedBalancer(LoadBalancer):
    """Weighted load balancer for canary deployments."""

    def select(self, request: Any = None) -> Optional[Endpoint]:
        """Select endpoint based on weights."""
        healthy = self.get_healthy_endpoints()
        if not healthy:
            return None

        # Simple weighted random selection
        total_weight = sum(e.weight for e in healthy)
        if total_weight == 0:
            return healthy[0]

        pick = random.randint(1, total_weight)
        current = 0
        for endpoint in healthy:
            current += endpoint.weight
            if current >= pick:
                return endpoint
        return healthy[0]  # fallback

