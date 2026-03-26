# sidecar/discovery/resolver.py - DNS and static resolvers
# Implements service discovery for POC (no K8s)

from typing import List, Dict, Optional
from dataclasses import dataclass
import socket


@dataclass
class Endpoint:
    """Represents a service endpoint."""
    address: str
    port: int
    weight: int = 1
    healthy: bool = True

    @property
    def url(self) -> str:
        return f"http://{self.address}:{self.port}"


class StaticResolver:
    """Static resolver that uses configured endpoints."""

    def __init__(self):
        self.endpoints: Dict[str, List[Endpoint]] = {}

    def add_endpoint(self, cluster: str, endpoint: Endpoint):
        """Add endpoint to a cluster."""
        if cluster not in self.endpoints:
            self.endpoints[cluster] = []
        if endpoint not in self.endpoints[cluster]:
            self.endpoints[cluster].append(endpoint)

    def resolve(self, cluster: str) -> List[Endpoint]:
        """Resolve endpoints for a cluster."""
        return self.endpoints.get(cluster, [])

    def get_all_clusters(self) -> List[str]:
        """Get all configured clusters."""
        return list(self.endpoints.keys())


class DNSResolver:
    """DNS-based resolver for dynamic service discovery."""

    def __init__(self):
        self.cache: Dict[str, List[Endpoint]] = {}
        self.cache_timeout = 30  # seconds

    def resolve(self, hostname: str, port: int = 8080) -> List[Endpoint]:
        """Resolve hostname to endpoints using DNS."""
        cache_key = f"{hostname}:{port}"

        # Check cache (simplified - in real implementation would check timestamp)
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Resolve hostname to IP addresses
            ips = socket.gethostbyname_ex(hostname)[2]
            endpoints = []

            for ip in ips:
                endpoints.append(Endpoint(address=ip, port=port))

            self.cache[cache_key] = endpoints
            return endpoints

        except socket.gaierror:
            # DNS resolution failed
            return []

    def clear_cache(self):
        """Clear DNS cache."""
        self.cache.clear()

