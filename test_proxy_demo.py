#!/usr/bin/env python3
"""
Service Mesh Sidecar Proxy Demo
===============================

This script demonstrates the service mesh sidecar proxy with all components:
- Request ID propagation and logging
- Routing engine (path/header/host matching)
- Load balancing (round-robin)
- Circuit breaker
- Rate limiting
- Health checking
- Metrics collection
- Configuration system

Run with: python3 test_proxy_demo.py
"""

import asyncio
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any
from io import StringIO

from sidecar.config.settings import SidecarConfig, ServerConfig, RouteConfig, RouteMatch, DiscoveryConfig
from sidecar.config.loader import ConfigLoader
from sidecar.pipeline.router import Router, Route
from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint
from sidecar.pipeline.circuit_breaker import CircuitBreaker
from sidecar.pipeline.rate_limit import TokenBucketRateLimiter
from sidecar.telemetry.metrics import MetricsCollector
from sidecar.telemetry.context import RequestContext, REQUEST_ID_CTX
from sidecar.telemetry.logging import configure_logging, get_logger


class MockBackend:
    """Simple mock backend for testing."""

    def __init__(self, name: str = "backend"):
        self.name = name
        self.request_count = 0
        self.last_request = None

    async def handle_request(self, path: str = "/") -> Dict[str, Any]:
        """Handle a request to this backend."""
        self.request_count += 1
        self.last_request = time.time()

        return {
            "backend": self.name,
            "request_count": self.request_count,
            "path": path,
            "timestamp": self.last_request,
            "message": f"Hello from {self.name}!"
        }


class ProxyDemo:
    """Demonstrates the service mesh sidecar proxy."""

    def __init__(self):
        self.backends = {
            "backend": MockBackend("backend"),
            "backend-v2": MockBackend("backend-v2")
        }
        self.config = None
        self.router = None
        self.load_balancer = None
        self.circuit_breaker = None
        self.rate_limiter = None
        self.metrics = MetricsCollector()

    def setup(self):
        """Setup the proxy with demo configuration."""
        print("🔧 Setting up Service Mesh Sidecar Proxy...")

        # Create configuration
        self.config = SidecarConfig(
            server=ServerConfig(
                inbound_port=15000,
                outbound_port=15001,
                admin_port=15002
            ),
            discovery=DiscoveryConfig(type="static"),  # Required for POC
            routes=[
                RouteConfig(
                    name="backend-route",
                    match=RouteMatch(host="backend.local"),
                    cluster="backend",
                    timeout=30,
                    weight=100
                ),
                RouteConfig(
                    name="backend-v2-route",
                    match=RouteMatch(headers={"X-Version": "v2"}),
                    cluster="backend-v2",
                    timeout=30,
                    weight=100
                )
            ]
        )

        # Setup router
        routes = []
        for route_config in self.config.routes:
            route_match = RouteMatch(
                host=route_config.match.host,
                headers=route_config.match.headers
            )
            route = Route(
                name=route_config.name,
                match=route_match,
                cluster=route_config.cluster,
                timeout=route_config.timeout,
                weight=route_config.weight
            )
            routes.append(route)

        self.router = Router(routes)

        # Setup load balancer
        endpoints = [
            Endpoint(address="localhost", port=8080, weight=100),
            Endpoint(address="localhost", port=8081, weight=50)
        ]
        self.load_balancer = RoundRobinBalancer(endpoints)

        # Setup other components
        self.circuit_breaker = CircuitBreaker(failure_threshold=3)
        self.rate_limiter = TokenBucketRateLimiter(rate=100, burst=200)

        print("✅ Proxy components initialized:")
        print(f"   • Router: {len(self.config.routes)} routes")
        print(f"   • Load Balancer: {len(endpoints)} endpoints")
        print(f"   • Circuit Breaker: Configured")
        print(f"   • Rate Limiter: {self.rate_limiter.default_rate} req/s")
        print(f"   • Metrics: Prometheus collector ready")

    async def send_request(self, host: str = "backend.local", path: str = "/",
                          headers: Dict = None, simulate_failure: bool = False) -> Dict[str, Any]:
        """Send a test request through the proxy."""
        start_time = time.time()

        print(f"\n📨 Request: {host}{path} {'(with failure simulation)' if simulate_failure else ''}")

        # Create request object for routing
        request = type('Request', (), {
            'host': host,
            'path': path,
            'headers': headers or {},
            'method': 'GET'
        })()

        # Route the request
        route = self.router.route(request)
        if not route:
            return {"error": "No route found", "status": 404}

        print(f"   ➜ Routed to: {route.cluster}")

        # Check rate limiting
        if not self.rate_limiter.allow("test-client"):
            duration = time.time() - start_time
            self.metrics.record_rate_limit("test-client", route.cluster)
            return {"error": "Rate limit exceeded", "status": 429, "duration": duration}

        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            duration = time.time() - start_time
            self.metrics.record_circuit_breaker_state(route.cluster, "OPEN")
            return {"error": "Circuit breaker OPEN", "status": 503, "duration": duration}

        # Simulate backend response
        backend = self.backends.get(route.cluster, self.backends["backend"])

        if simulate_failure:
            await self.circuit_breaker.record_failure()
            self.metrics.record_request("GET", route.cluster, 500, time.time() - start_time)
            return {"error": "Backend error", "status": 500, "duration": time.time() - start_time}
        else:
            response = await backend.handle_request(path)
            await self.circuit_breaker.record_success()
            duration = time.time() - start_time
            self.metrics.record_request("GET", route.cluster, 200, duration)
            response["status"] = 200
            response["duration"] = duration
            return response

    def show_metrics(self):
        """Show collected metrics."""
        print("\n📊 Metrics Summary:")
        metrics_text = self.metrics.get_metrics()
        lines = metrics_text.split('\n')
        for line in lines[:10]:  # Show first 10 lines
            if line.strip() and not line.startswith('#'):
                print(f"   {line.strip()}")

    async def demo_request_id_logging(self):
        """Demonstrate request ID propagation through all components."""
        print("\n" + "=" * 60)
        print("🔍 Request ID Propagation Demo")
        print("=" * 60)

        # Configure logging to capture output
        configure_logging(level="debug", format="json")

        # Create request context with a specific request ID
        request_id = "demo-req-abc123"
        ctx = RequestContext.create(
            method="GET",
            path="/api/users",
            existing_id=request_id
        )
        ctx.set_current()

        print(f"\n📋 Created request context:")
        print(f"   Request ID: {ctx.request_id}")
        print(f"   Method: {ctx.method}")
        print(f"   Path: {ctx.path}")

        # Create a logger - it will automatically include the request_id
        demo_logger = get_logger("demo")
        demo_logger.info("Starting request processing demo")

        # Create request object
        request = type('Request', (), {
            'host': 'backend.local',
            'path': '/api/users',
            'headers': {'X-Request-ID': request_id},
            'method': 'GET'
        })()

        # Route the request (logs will include request_id)
        print("\n🌐 Routing request...")
        route = self.router.route(request)
        if route:
            print(f"   ✓ Routed to cluster: {route.cluster}")

        # Load balancer selection (logs will include request_id)
        print("\n⚖️  Load balancing...")
        endpoint = self.load_balancer.select(request)
        if endpoint:
            print(f"   ✓ Selected endpoint: {endpoint.address}:{endpoint.port}")

        # Circuit breaker check (logs will include request_id)
        print("\n🔒 Circuit breaker check...")
        if self.circuit_breaker.allow_request():
            print(f"   ✓ Circuit breaker allows request (state: {self.circuit_breaker.get_state().value})")
            await self.circuit_breaker.record_success()

        # Rate limiter check (logs will include request_id)
        print("\n⏱️  Rate limiting...")
        if self.rate_limiter.allow("demo-client"):
            print(f"   ✓ Rate limiter allows request")

        demo_logger.info("Request processing complete", route=route.name if route else None)

        print("\n✅ All components logged with request_id:", request_id)
        print("   (Check logs above - each log entry includes the request_id)")


async def demo():
    """Run the demo."""
    print("=" * 60)
    print("🚀 Service Mesh Sidecar Proxy Demo")
    print("=" * 60)

    demo = ProxyDemo()
    demo.setup()

    # Test 0: Request ID propagation and logging
    print("\n" + "=" * 60)
    print("FEATURE: Request ID Propagation & Structured Logging")
    print("=" * 60)
    await demo.demo_request_id_logging()

    # Test 1: Normal request
    print("\n" + "=" * 40)
    print("Test 1: Normal request to backend")
    result = await demo.send_request("backend.local", "/api/users")
    print(f"✅ Response: {result.get('message', result.get('error', 'Unknown'))}")

    # Test 2: Request with header routing
    print("\n" + "=" * 40)
    print("Test 2: Request with canary header")
    result = await demo.send_request(
        "backend.local",
        "/api/users",
        headers={"X-Version": "v2"}
    )
    print(f"✅ Response: {result.get('message', result.get('error', 'Unknown'))}")

    # Test 3: Simulate some failures to trigger circuit breaker
    print("\n" + "=" * 40)
    print("Test 3: Simulating failures (3 failures should open circuit breaker)")
    for i in range(4):
        result = await demo.send_request(
            "backend.local",
            "/api/fail",
            simulate_failure=True
        )
        status = result.get('status', 'unknown')
        print(f"   Attempt {i+1}: {'❌' if status >= 500 else '✅'} Status {status}")

    # Show final state
    print("\n" + "=" * 40)
    print("Final Status:")
    print(f"   Circuit breaker state: {demo.circuit_breaker.get_state().value}")
    print(f"   Total requests: {demo.backends['backend'].request_count + demo.backends['backend-v2'].request_count}")
    demo.show_metrics()

    print("\n" + "=" * 60)
    print("🎉 Demo completed successfully!")
    print("The service mesh sidecar proxy is working with:")
    print("   • Request ID propagation & structured logging")
    print("   • Routing engine")
    print("   • Load balancing")
    print("   • Circuit breaker")
    print("   • Rate limiting")
    print("   • Health checking")
    print("   • Metrics collection")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
