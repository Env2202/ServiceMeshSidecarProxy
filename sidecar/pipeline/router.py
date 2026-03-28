# sidecar/pipeline/router.py - Routing engine
# Implements path, header, and host-based routing per plan

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re

from ..telemetry.logging import get_logger

logger = get_logger("router")


@dataclass
class RouteMatch:
    """Defines how a route should match incoming requests."""
    host: Optional[str] = None
    path_prefix: Optional[str] = None
    path_exact: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    def matches(self, request: Any) -> bool:
        """Check if this route matches the request."""
        # For now, we'll simulate request with attributes
        # In real implementation, this would take a web request object

        if self.host and hasattr(request, 'host'):
            if not re.match(self.host.replace('*', '.*'), request.host):
                return False

        if self.path_prefix and hasattr(request, 'path'):
            if not request.path.startswith(self.path_prefix):
                return False

        if self.path_exact and hasattr(request, 'path'):
            if request.path != self.path_exact:
                return False

        if self.headers and hasattr(request, 'headers'):
            for key, value in self.headers.items():
                if key not in request.headers or request.headers[key] != value:
                    return False

        return True


@dataclass
class Route:
    """Represents a single routing rule."""
    name: str
    match: RouteMatch
    cluster: str
    timeout: Optional[int] = 30
    weight: int = 100

    def matches(self, request: Any) -> bool:
        """Check if this route matches the request."""
        return self.match.matches(request)


class Router:
    """Main routing engine that selects routes based on request."""

    def __init__(self, routes: List[Route]):
        self.routes = routes or []

    def route(self, request: Any) -> Optional[Route]:
        """Find the first route that matches the request.

        Returns the matching Route or None if no match.
        """
        path = getattr(request, 'path', 'unknown')
        method = getattr(request, 'method', 'unknown')

        logger.debug("Routing request", method=method, path=path)

        for route in self.routes:
            if route.matches(request):
                logger.info(
                    "Route matched",
                    route=route.name,
                    cluster=route.cluster,
                    path=path
                )
                return route

        logger.warning("No route matched", path=path)
        return None

    def get_cluster(self, request: Any) -> Optional[str]:
        """Get the target cluster for a request."""
        route = self.route(request)
        return route.cluster if route else None

    def add_route(self, route: Route):
        """Add a new route to the router."""
        self.routes.append(route)

    def clear(self):
        """Clear all routes."""
        self.routes.clear()

