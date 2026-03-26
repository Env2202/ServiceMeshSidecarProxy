# sidecar/discovery/endpoint.py - Endpoint model
# Shared endpoint definition used by resolvers and load balancers

from dataclasses import dataclass
from typing import Optional


@dataclass
class Endpoint:
    """Represents a service endpoint."""
    address: str
    port: int
    weight: int = 1
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

