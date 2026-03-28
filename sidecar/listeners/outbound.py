# sidecar/listeners/outbound.py - Outbound HTTP client
# Handles forwarding requests to backend services using httpx

import httpx
from typing import Optional, Dict, Any
import asyncio
import time

from ..config.settings import SidecarConfig
from ..pipeline.router import Router
from ..pipeline.load_balancer import LoadBalancer, RoundRobinBalancer
from ..pipeline.circuit_breaker import CircuitBreaker
from ..pipeline.retry import RetryHandler
from ..telemetry.metrics import MetricsCollector
from ..telemetry.context import REQUEST_ID_CTX

REQUEST_ID_HEADER = "X-Request-ID"


class OutboundClient:
    """Outbound HTTP client for forwarding requests to backends."""

    def __init__(self, config: SidecarConfig):
        self.config = config
        self.router: Optional[Router] = None
        self.load_balancer: Optional[LoadBalancer] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handler = RetryHandler()
        self.metrics = MetricsCollector()
        self.client = httpx.AsyncClient(timeout=10.0)

    async def forward(self, request: Any) -> Dict[str, Any]:
        """Forward request to appropriate backend."""
        start_time = time.time()

        try:
            # Route the request
            route = self.router.route(request) if self.router else None
            if not route:
                return {
                    "status_code": 404,
                    "error": "No route found",
                    "duration": time.time() - start_time
                }

            # Get or create circuit breaker
            if route.cluster not in self.circuit_breakers:
                self.circuit_breakers[route.cluster] = CircuitBreaker()

            cb = self.circuit_breakers[route.cluster]

            if not cb.allow_request():
                self.metrics.record_circuit_breaker_state(route.cluster, "OPEN")
                return {
                    "status_code": 503,
                    "error": "Circuit breaker is OPEN",
                    "duration": time.time() - start_time
                }

            # Select backend
            if self.load_balancer:
                endpoint = self.load_balancer.select(request)
            else:
                # Default endpoint
                endpoint = type('Endpoint', (), {
                    'address': 'localhost',
                    'port': 8080,
                    'url': 'http://localhost:8080'
                })()

            if not endpoint:
                return {
                    "status_code": 503,
                    "error": "No healthy endpoints",
                    "duration": time.time() - start_time
                }

            # Make the request to backend
            backend_url = f"http://{endpoint.address}:{endpoint.port}{request.path if hasattr(request, 'path') else '/'}"

            # Get request_id from context and add to headers
            headers = {}
            try:
                request_id = REQUEST_ID_CTX.get()
                headers[REQUEST_ID_HEADER] = request_id
            except LookupError:
                pass  # No request_id in context

            try:
                response = await self.client.get(backend_url, headers=headers, timeout=5.0)
                duration = time.time() - start_time

                # Record success
                await cb.record_success()
                self.metrics.record_request(
                    method="GET",
                    route=route.cluster,
                    status_code=response.status_code,
                    duration=duration
                )

                return {
                    "status_code": response.status_code,
                    "backend": backend_url,
                    "duration": duration,
                    "success": True
                }

            except Exception as e:
                duration = time.time() - start_time
                await cb.record_failure()
                self.metrics.record_request(
                    method="GET",
                    route=route.cluster,
                    status_code=502,
                    duration=duration
                )

                return {
                    "status_code": 502,
                    "error": str(e),
                    "backend": backend_url,
                    "duration": duration,
                    "success": False
                }

        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_request(
                method="GET",
                route="error",
                status_code=500,
                duration=duration
            )
            return {
                "status_code": 500,
                "error": str(e),
                "duration": duration,
                "success": False
            }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

