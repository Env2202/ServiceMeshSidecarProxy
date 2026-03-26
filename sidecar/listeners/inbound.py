# sidecar/listeners/inbound.py - Inbound HTTP listener (aiohttp)
# Listens on :15000 and forwards to backend services

from aiohttp import web
from typing import Dict, Any, Optional
import asyncio
import time
import json

from ..config.settings import SidecarConfig
from ..pipeline.router import Router, Route
from ..pipeline.load_balancer import LoadBalancer, RoundRobinBalancer
from ..pipeline.circuit_breaker import CircuitBreaker
from ..pipeline.rate_limit import TokenBucketRateLimiter
from ..pipeline.retry import RetryHandler
from ..telemetry.metrics import MetricsCollector


class InboundListener:
    """Inbound HTTP listener that accepts requests from applications."""

    def __init__(self, config: SidecarConfig):
        self.config = config
        self.app = web.Application()
        self.router = None
        self.load_balancer = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiter = TokenBucketRateLimiter()
        self.retry_handler = RetryHandler()
        self.metrics = MetricsCollector()

        # Setup routes
        self.app.router.add_get('/sidecar/health', self.health_handler)
        self.app.router.add_get('/sidecar/metrics', self.metrics_handler)
        self.app.router.add_get('/sidecar/config', self.config_handler)
        self.app.router.add_route('*', '/{path:.*}', self.proxy_handler)

    async def health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "version": "0.1.0",
            "timestamp": time.time()
        })

    async def metrics_handler(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        metrics_text = self.metrics.get_metrics()
        return web.Response(text=metrics_text, content_type='text/plain')

    async def config_handler(self, request: web.Request) -> web.Response:
        """Return current configuration (for debugging)."""
        config_dict = {
            "server": {
                "inbound_port": self.config.server.inbound_port,
                "outbound_port": self.config.server.outbound_port,
                "admin_port": self.config.server.admin_port,
            },
            "routes_count": len(self.config.routes),
            "rate_limits_count": len(self.config.rate_limits),
        }
        return web.json_response(config_dict)

    async def proxy_handler(self, request: web.Request) -> web.Response:
        """Main proxy handler that routes requests to backends."""
        start_time = time.time()

        try:
            # Create a simple request object for routing
            proxy_request = type('Request', (), {
                'host': request.host,
                'path': str(request.path),
                'headers': dict(request.headers),
                'method': request.method
            })()

            # Route the request
            route = self.router.route(proxy_request) if self.router else None

            if not route:
                # No route found - return 404
                duration = time.time() - start_time
                self.metrics.record_request(
                    method=request.method,
                    route="unknown",
                    status_code=404,
                    duration=duration
                )
                return web.json_response({"error": "No route found"}, status=404)

            # Check rate limiting
            client_key = request.remote or "unknown"
            if not self.rate_limiter.allow(client_key):
                duration = time.time() - start_time
                self.metrics.record_rate_limit(client_key, route.cluster)
                self.metrics.record_request(
                    method=request.method,
                    route=route.cluster,
                    status_code=429,
                    duration=duration
                )
                return web.json_response({"error": "Rate limit exceeded"}, status=429)

            # Get circuit breaker for this route
            if route.cluster not in self.circuit_breakers:
                self.circuit_breakers[route.cluster] = CircuitBreaker()

            cb = self.circuit_breakers[route.cluster]

            if not cb.allow_request():
                duration = time.time() - start_time
                self.metrics.record_circuit_breaker_state(route.cluster, "OPEN")
                self.metrics.record_request(
                    method=request.method,
                    route=route.cluster,
                    status_code=503,
                    duration=duration
                )
                return web.json_response({"error": "Circuit breaker is OPEN"}, status=503)

            # Select backend using load balancer
            if not self.load_balancer:
                # Simple static endpoint for now
                endpoint = type('Endpoint', (), {
                    'address': 'localhost',
                    'port': 8080,
                    'url': 'http://localhost:8080'
                })()
            else:
                endpoint = self.load_balancer.select(proxy_request)

            if not endpoint:
                return web.json_response({"error": "No healthy endpoints"}, status=503)

            # Forward request to backend (simplified for POC)
            # In real implementation, this would use httpx to forward the request
            duration = time.time() - start_time

            # Record success
            await cb.record_success()
            self.metrics.record_request(
                method=request.method,
                route=route.cluster,
                status_code=200,
                duration=duration
            )

            return web.json_response({
                "message": f"Proxied to {route.cluster}",
                "backend": endpoint.url if hasattr(endpoint, 'url') else f"http://{endpoint.address}:{endpoint.port}",
                "duration_ms": round(duration * 1000, 2)
            })

        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_request(
                method=request.method,
                route="error",
                status_code=500,
                duration=duration
            )
            return web.json_response({"error": str(e)}, status=500)


async def create_inbound_app(config: SidecarConfig) -> web.Application:
    """Create and return the inbound listener application."""
    listener = InboundListener(config)
    return listener.app

