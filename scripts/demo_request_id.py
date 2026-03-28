#!/usr/bin/env python3
"""
Request ID Logging Demo

This script demonstrates the request ID propagation feature across all components
by simulating requests and showing how the request ID flows through:
1. Inbound entry (assigns/extracts request ID)
2. Router (logs routing decisions)
3. Load Balancer (logs endpoint selection)
4. Circuit Breaker (logs state changes)
5. Rate Limiter (logs rate limit decisions)
6. Outbound Client (forwards X-Request-ID header)

Run with: python3 scripts/demo_request_id.py
"""

import asyncio
import time
import sys
import json
from io import StringIO
from unittest.mock import Mock, patch

# Add sidecar to path
sys.path.insert(0, '/testbed/ServiceMeshSidecarProxy')

from sidecar.telemetry.context import RequestContext, REQUEST_ID_CTX
from sidecar.telemetry.logging import configure_logging, get_logger
from sidecar.pipeline.router import Router, Route, RouteMatch
from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint
from sidecar.pipeline.circuit_breaker import CircuitBreaker
from sidecar.pipeline.rate_limit import TokenBucketRateLimiter


class LogCapture:
    """Captures log output for display."""
    def __init__(self):
        self.entries = []
        self.buffer = StringIO()
    
    def write(self, data):
        """Write data to buffer and parse JSON logs."""
        self.buffer.write(data)
        for line in data.strip().split('\n'):
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    self.entries.append(entry)
                except json.JSONDecodeError:
                    pass
    
    def flush(self):
        pass
    
    def print_summary(self):
        """Print a summary of captured logs."""
        print("\n" + "=" * 80)
        print("LOG ENTRY SUMMARY")
        print("=" * 80)
        
        for i, entry in enumerate(self.entries, 1):
            req_id = entry.get('request_id', 'N/A')
            component = entry.get('component', 'unknown')
            event = entry.get('event', 'unknown')
            level = entry.get('level', 'info')
            
            print(f"{i}. [{component}] {event}")
            print(f"   Request ID: {req_id}")
            print(f"   Level: {level}")
            
            # Show additional context
            extras = {k: v for k, v in entry.items() 
                     if k not in ['request_id', 'component', 'event', 'level', 'timestamp', 'logger']}
            if extras:
                print(f"   Context: {extras}")
            print()


class DemoRequest:
    """Mock request object for demo purposes."""
    def __init__(self, path, method="GET", headers=None, host="localhost"):
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.host = host
    
    async def body(self):
        return b""


async def demo_phase_1():
    """Demo: Request Context Creation."""
    print("\n" + "=" * 80)
    print("PHASE 1: Request Context Creation")
    print("=" * 80)
    
    # Create context - generates a request ID
    ctx = RequestContext.create(method="GET", path="/api/users")
    print(f"Created context with request_id: {ctx.request_id}")
    print(f"Start time: {ctx.start_time}")
    
    # Set as current context
    ctx.set_current()
    print("Context set as current (available via REQUEST_ID_CTX)")
    
    return ctx


async def demo_phase_2():
    """Demo: Structured Logging."""
    print("\n" + "=" * 80)
    print("PHASE 2: Structured Logging")
    print("=" * 80)
    
    # Configure logging
    configure_logging(level="debug", format="json")
    print("Logging configured with JSON format")
    
    # Get logger - will automatically include request_id
    logger = get_logger("demo")
    logger.info("Application started")
    print("Log entry above includes request_id automatically")


async def demo_phase_3(ctx):
    """Demo: Pipeline Components with Request ID Logging."""
    print("\n" + "=" * 80)
    print("PHASE 3: Pipeline Components with Request ID Logging")
    print("=" * 80)
    
    # Simulate routing
    router = Router([
        Route("user-service", RouteMatch(path_prefix="/api/users"), "users"),
        Route("order-service", RouteMatch(path_exact="/api/orders"), "orders"),
    ])
    
    request = DemoRequest("/api/users/123", headers={"X-Request-ID": ctx.request_id})
    route = router.route(request)
    
    # Simulate load balancing
    endpoints = [
        Endpoint("10.0.1.10", 8080),
        Endpoint("10.0.1.11", 8080),
    ]
    lb = RoundRobinBalancer(endpoints)
    endpoint = lb.select(request)
    
    # Simulate circuit breaker
    cb = CircuitBreaker(failure_threshold=3, success_threshold=2)
    for _ in range(3):
        await cb.record_failure()
    
    # Simulate rate limiting
    rl = TokenBucketRateLimiter(rate=10, burst=10)
    rl.reset()
    allowed = rl.allow("client-1")


async def demo_full_flow():
    """Demo: Full Request Lifecycle."""
    print("\n" + "=" * 80)
    print("FULL FLOW: Complete Request Lifecycle")
    print("=" * 80)
    
    log_capture = LogCapture()
    
    # Capture logs by redirecting stdout
    original_stdout = sys.stdout
    sys.stdout = log_capture
    
    # Reconfigure logging to use our capture
    configure_logging(level="info", format="json")
    
    # Simulate a complete request flow
    # 1. Inbound: Assign/extract request ID
    existing_id = "req-demo-12345"
    ctx = RequestContext.create(method="GET", path="/api/users", existing_id=existing_id)
    ctx.set_current()
    
    # 2. Router
    router = Router([
        Route("user-service", RouteMatch(path_prefix="/api/users"), "users"),
    ])
    request = DemoRequest("/api/users", headers={"X-Request-ID": existing_id})
    route = router.route(request)
    
    # 3. Load Balancer
    lb = RoundRobinBalancer([
        Endpoint("10.0.1.10", 8080),
        Endpoint("10.0.1.11", 8080),
    ])
    endpoint = lb.select(request)
    
    # Log completion
    logger = get_logger("demo")
    logger.info("Request processing complete")
    
    # Restore stdout
    sys.stdout = original_stdout
    
    print(f"\nProcessed request {existing_id}")
    print(f"Route: {route}")
    print(f"Selected endpoint: {endpoint}")
    
    # Print log summary
    log_capture.print_summary()
    
    # Verify request_id in all logs
    print("\n" + "=" * 80)
    print("REQUEST ID PROPAGATION VERIFICATION")
    print("=" * 80)
    
    all_have_request_id = all(
        entry.get('request_id') == existing_id 
        for entry in log_capture.entries 
        if entry.get('component') != 'sidecar'
    )
    
    if all_have_request_id:
        print(f"✅ SUCCESS: All component logs contain request_id: {existing_id}")
    else:
        print("❌ FAILURE: Some logs missing request_id")


async def main():
    """Run all demo phases."""
    print("=" * 80)
    print("REQUEST ID PROPAGATION DEMO")
    print("=" * 80)
    print("\nThis demo shows how the request_id flows through all components")
    
    # Phase 1
    ctx = await demo_phase_1()
    
    # Phase 2
    await demo_phase_2()
    
    # Phase 3
    await demo_phase_3(ctx)
    
    # Full flow
    await demo_full_flow()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
