# Service Mesh Sidecar Proxy

A lightweight service mesh sidecar proxy for HTTP-based microservices, providing routing, load balancing, circuit breaking, rate limiting, and comprehensive observability through structured logging with request ID propagation.

## Features

- ✅ **Request ID Propagation** - Unique request IDs that flow through all components and downstream services
- ✅ **Structured Logging** - JSON-formatted logs with automatic request ID binding
- ✅ **Routing Engine** - Path-based, header-based, and host-based routing
- ✅ **Load Balancing** - Round-robin and least-connections algorithms
- ✅ **Circuit Breaker** - Automatic failure detection and recovery
- ✅ **Rate Limiting** - Token bucket algorithm for traffic control
- ✅ **Health Checks** - Active HTTP probes and passive failure tracking
- ✅ **Prometheus Metrics** - Request counts, latencies, error rates

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Basic Configuration

Create `sidecar-config.yaml`:

```yaml
version: "1.0"
server:
  inbound_port: 15000
  outbound_port: 15001
  admin_port: 15002

logging:
  level: info
  format: json

discovery:
  type: static

routes:
  - name: backend
    match:
      path_prefix: /
    cluster:
      name: backend
      endpoints:
        - address: localhost
          port: 8080
```

### Run the Sidecar

```bash
python -m sidecar --config ./sidecar-config.yaml
```

### Test Request ID Propagation

```bash
# Send request with custom request ID
curl -v -H "X-Request-ID: my-request-123" http://localhost:15000/api/users

# Verify response includes the same request ID
# < X-Request-ID: my-request-123
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Application Pod                                  │
│  ┌─────────────────────┐         ┌───────────────────────────────────┐ │
│  │   Main Application  │         │       Sidecar Proxy               │ │
│  │   (Business Logic)  │◄────────│   (Communication Layer)           │ │
│  │                     │  :15000  │                                   │ │
│  │   Listens on :8080  │◄────────│   • Request ID Propagation        │ │
│  │                     │  :15001  │   • Structured Logging            │ │
│  └─────────────────────┘         │   • Routing & Load Balancing      │ │
│                                  │   • Circuit Breaker               │ │
│                                  │   • Rate Limiting                 │ │
│                                  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Documentation

- [Architecture](./docs/architecture.md) - System architecture and component design
- [Configuration](./docs/configuration.md) - Configuration options and examples
- [Deployment](./docs/deployment.md) - Deployment guides for various environments
- [Logging & Tracing](./docs/logging-tracing.md) - Structured logging and request ID propagation
- [Execution Plan](./docs/request-id-execution-plan.md) - Implementation phases and TDD approach

## Demo

Run the demo to see request ID propagation in action:

```bash
# Request ID propagation demo
python3 scripts/demo_request_id.py

# Full proxy demo with all components
python3 test_proxy_demo.py
```

Example output:
```json
{
  "request_id": "req-a1b2c3d4e5f6",
  "component": "router",
  "event": "Route matched",
  "route": "user-service",
  "cluster": "users",
  "path": "/api/users",
  "timestamp": "2024-01-15T09:23:45.125Z",
  "level": "info"
}
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sidecar --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_context_propagation.py -v
```

## Project Structure

```
service-mesh-sidecar/
├── sidecar/                    # Main package
│   ├── telemetry/              # Logging, metrics, tracing
│   │   ├── context.py          # Request context with contextvars
│   │   ├── logging.py          # Structured logging with structlog
│   │   └── metrics.py          # Prometheus metrics
│   ├── listeners/              # HTTP listeners
│   │   ├── inbound.py          # Inbound listener (:15000)
│   │   ├── outbound.py         # Outbound client (:15001)
│   │   └── middleware.py       # Request ID middleware
│   ├── pipeline/               # Request processing pipeline
│   │   ├── router.py           # Routing engine
│   │   ├── load_balancer.py    # Load balancing algorithms
│   │   ├── circuit_breaker.py  # Circuit breaker pattern
│   │   └── rate_limit.py       # Rate limiting
│   └── config/                 # Configuration management
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── docs/                       # Documentation
├── scripts/                    # Demo scripts
└── examples/                   # Example configurations
```

## POC Scope

This is a **Proof of Concept** implementation with the following scope:

- ✅ HTTP only (no gRPC, TCP, etc.)
- ✅ Config-file based (no centralized control plane)
- ✅ Standalone/Container deployment (no Kubernetes integration)
- ✅ Plain HTTP (no TLS/mTLS)
- ✅ Prometheus metrics only (no OpenTelemetry tracing)
- ✅ Request ID propagation with structured logging ✅

## License

MIT License