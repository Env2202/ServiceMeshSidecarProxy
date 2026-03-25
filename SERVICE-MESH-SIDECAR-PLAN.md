# Service Mesh Sidecar Proxy - Implementation Plan

## Executive Summary

This document outlines a comprehensive plan for building a service mesh sidecar proxy to facilitate secure, reliable, and observable communication between microservices. The sidecar will handle routing, load balancing, circuit breaking, rate limiting, health checks, and other cross-cutting concerns.

---

## 1. Project Overview

### 1.1 Goals

- **Decouple service logic from infrastructure concerns**: Services focus on business logic; sidecar handles communication.
- **Provide a unified communication layer**: Consistent behavior across all services in the mesh.
- **Enable observability**: Rich telemetry for debugging and monitoring.
- **Ensure reliability**: Handle failures gracefully with retries, circuit breakers, and timeouts.
- **Support gradual adoption**: Services can opt-in without major refactoring.

### 1.2 Key Features

| Feature | Description |
|---------|-------------|
| **Service Discovery** | Dynamic resolution of service endpoints |
| **Routing** | Path-based, header-based, and weighted routing |
| **Load Balancing** | Round-robin, least-connections, random, consistent hashing |
| **Circuit Breaker** | Fail-fast patterns for downstream protection |
| **Rate Limiting** | Per-client and global rate limiting |
| **Health Checks** | Active and passive health monitoring |
| **Retry Logic** | Configurable retry with backoff strategies |
| **Timeout Handling** | Request and connection timeouts |
| **mTLS** | Mutual TLS for service-to-service security |
| **Telemetry** | Metrics, tracing, and logging |

### 1.3 Non-Goals (Out of Scope for v1)

- Centralized control plane (can be added later)
- Service mesh visualization UI
- Multi-datacenter/multi-region federation
- Legacy protocol support (beyond HTTP/HTTPS/gRPC)

---

## 2. Architecture Design

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Pod                              │
│  ┌─────────────────────┐         ┌───────────────────────────────┐  │
│  │   Main Application  │         │       Sidecar Proxy           │  │
│  │   (Business Logic)  │◄────────│   (Communication Layer)       │  │
│  │                     │  loopback│                               │  │
│  │   Listens on :8080  │         │   Listens on :15000 (inbound) │  │
│  │                     │         │   Listens on :15001 (outbound)│  │
│  └─────────────────────┘         │                               │  │
│                                  │  ┌─────────────────────────┐  │  │
│                                  │  │  Routing Engine         │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Load Balancer          │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Circuit Breaker        │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Rate Limiter           │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Health Checker         │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Retry Handler          │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  mTLS / Security        │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Telemetry (Metrics/    │  │  │
│                                  │  │  Tracing/Logging)       │  │  │
│                                  │  └─────────────────────────┘  │  │
│                                  └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Traffic Flow

#### Outbound (Egress)
1. Application makes request to `localhost:15001`
2. Sidecar intercepts and resolves destination service
3. Applies routing rules, load balancing, rate limits
4. Checks circuit breaker state
5. Establishes connection (with mTLS if enabled)
6. Forwards request to actual backend
7. Handles retries/timeouts on failure
8. Returns response to application

#### Inbound (Ingress)
1. External traffic arrives on `localhost:15000`
2. Sidecar validates incoming request (auth, rate limits)
3. Applies any inbound routing rules
4. Health checks / readiness probes handled
5. Forwards to application on `:8080`
6. Collects telemetry

### 2.3 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Sidecar Proxy                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Inbound   │    │  Outbound   │    │   Control Plane     │ │
│  │   Listener  │    │  Listener   │    │   Interface (API)   │ │
│  │  :15000     │    │  :15001     │    │                     │ │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘ │
│         │                  │                      │            │
│         ▼                  ▼                      ▼            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Request Pipeline                         ││
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐  ││
│  │  │  Auth   │→│ Rate     │→│ Route   │→│ Load            │  ││
│  │  │  Check  │ │ Limit    │ │ Match   │ │ Balancer        │  ││
│  │  └─────────┘ └──────────┘ └─────────┘ └────────┬────────┘  ││
│  │                                                │           ││
│  │  ┌─────────────────────────────────────────────┴─────────┐ ││
│  │  │              Circuit Breaker + Retry Handler            │ ││
│  │  └─────────────────────────────────────────────────────────┘ ││
│  │                                                │           ││
│  │  ┌─────────────────────────────────────────────┴─────────┐ ││
│  │  │              Connection Pool + mTLS                     │ ││
│  │  └─────────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Telemetry Layer                          ││
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────────────────┐ ││
│  │  │  Metrics  │  │  Tracing  │  │  Logging                │ ││
│  │  │ (Prometheus│  │ (OpenTel) │  │  (Structured)           │ ││
│  │  │  format)  │  │           │  │                         │ ││
│  │  └───────────┘  └───────────┘  └─────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Features Detailed Design

### 3.1 Routing Engine

**Capabilities:**
- Path-based routing (`/api/v1/*` → `service-a`)
- Header-based routing (`X-Version: v2` → `service-b:v2`)
- Host-based routing (`api.example.com` → `api-service`)
- Weighted routing (70% → v1, 30% → v2 for canary)
- Regex and prefix matching

**Configuration Example (YAML):**
```yaml
routes:
  - match:
      path_prefix: /api/users
    action:
      cluster: user-service
      timeout: 5s
  - match:
      headers:
        X-Canary: "true"
    action:
      cluster: user-service-v2
      weight: 100
```

### 3.2 Load Balancing

**Algorithms:**
| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| `round_robin` | Distributes evenly across backends | Homogeneous backends |
| `least_connections` | Routes to backend with fewest active connections | Variable request durations |
| `random` | Random selection | Simple, good distribution |
| `consistent_hash` | Hash-based sticky routing | Session affinity |
| `weighted` | Custom weights per backend | Gradual rollouts |

**Backend Selection Flow:**
```
Request → Routing Engine → Load Balancer → Backend Pool
                              ↓
                    [Round-Robin / Least-Con / Hash]
                              ↓
                    Select healthy endpoint
```

### 3.3 Circuit Breaker

**State Machine:**
```
           ┌─────────────┐
           │   CLOSED    │◄───────┐
           │ (allow all) │        │
           └──────┬──────┘        │
                  │               │
                  ▼               │
           ┌─────────────┐        │
           │   OPEN      │────────┘ (timeout)
           │ (reject all)│
           └──────┬──────┘
                  │
                  ▼
           ┌─────────────┐
           │   HALF-OPEN │
           │ (probe)     │
           └─────────────┘
```

**Configuration:**
```yaml
circuit_breaker:
  failure_threshold: 5        # failures before opening
  success_threshold: 3        # successes to close from half-open
  timeout: 30s                # time before half-open
  volume_threshold: 10        # min requests to evaluate
  failure_rate_threshold: 0.5 # 50% failures = open
```

### 3.4 Rate Limiting

**Types:**
- **Token Bucket**: Allows bursts, sustained rate over time
- **Sliding Window**: Accurate rate limiting per time window
- **Fixed Window**: Simple but allows burst at window edges

**Scopes:**
- Per-client (by IP, by API key, by identity)
- Per-route
- Global

**Configuration:**
```yaml
rate_limits:
  - scope: client
    limit: 100
    window: 1s
  - scope: route
    path: /api/heavy
    limit: 10
    window: 1s
```

### 3.5 Health Checks

**Active Health Checks:**
- HTTP/HTTPS probes (GET, HEAD)
- TCP socket checks
- gRPC health protocol
- Configurable interval, timeout, healthy/unhealthy thresholds

**Passive Health Checks:**
- Track request success/failure
- Automatic ejection of failing backends
- Re-add after recovery period

**Configuration:**
```yaml
health_check:
  type: http
  path: /health
  interval: 10s
  timeout: 2s
  healthy_threshold: 2
  unhealthy_threshold: 3
```

### 3.6 Retry Logic

**Features:**
- Configurable max retries
- Retry on specific status codes (5xx, 429, etc.)
- Exponential backoff with jitter
- Retry budget (prevent retry storms)

**Configuration:**
```yaml
retry:
  max_attempts: 3
  retry_on:
    - 5xx
    - connect_failure
    - reset
  backoff:
    base_interval: 100ms
    max_interval: 10s
    jitter: 0.2  # ±20%
```

### 3.7 Security (mTLS)

**Features:**
- Automatic certificate generation and rotation
- mTLS between all services
- Configurable TLS modes (strict, permissive, disabled)
- SPIFFE/SPIRE integration (optional)

**TLS Modes:**
| Mode | Description |
|------|-------------|
| `STRICT` | Require mTLS, reject plaintext |
| `PERMISSIVE` | Accept both TLS and plaintext |
| `DISABLE` | No TLS |

### 3.8 Telemetry

**Metrics (Prometheus format):**
- Request count, latency (p50, p99), error rates
- Circuit breaker state transitions
- Rate limit hits
- Connection pool stats
- Health check results

**Tracing:**
- OpenTelemetry integration
- W3C Trace Context propagation
- B3 propagation support

**Logging:**
- Structured JSON logs
- Configurable log levels per component
- Request/response logging (sanitized)

---

## 4. Project Structure

```
service-mesh-sidecar/
├── README.md
├── pyproject.toml             # Project metadata, dependencies, tooling
├── .python-version            # Python version pin
├── Dockerfile
├── .dockerignore
├── .gitignore
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   └── deployment.md
├── sidecar/                   # Main package (src layout)
│   ├── __init__.py
│   ├── main.py                # CLI entry point (click)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py        # Pydantic Settings for configuration
│   │   └── loader.py          # Load from file/env/K8s ConfigMap
│   ├── listeners/
│   │   ├── __init__.py
│   │   ├── inbound.py         # Inbound listener (aiohttp on :15000)
│   │   └── outbound.py        # Outbound listener (aiohttp on :15001)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication middleware
│   │   ├── rate_limit.py      # Rate limiting middleware
│   │   ├── router.py          # Routing engine
│   │   ├── load_balancer.py   # LB algorithms
│   │   ├── circuit_breaker.py # Circuit breaker logic
│   │   ├── retry.py           # Retry handler (tenacity)
│   │   └── timeout.py         # Timeout enforcement
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── resolver.py        # DNS-based or K8s-based discovery
│   │   └── endpoint.py        # Endpoint representation
│   ├── health/
│   │   ├── __init__.py
│   │   ├── checker.py         # Active health checking
│   │   └── tracker.py         # Passive health tracking
│   ├── security/
│   │   ├── __init__.py
│   │   ├── tls.py             # TLS/mTLS handling
│   │   └── auth.py            # Authentication providers
│   ├── telemetry/
│   │   ├── __init__.py
│   │   ├── metrics.py         # Prometheus metrics
│   │   ├── tracing.py         # OpenTelemetry tracing
│   │   └── logging.py         # Structured logging (structlog)
│   ├── connection/
│   │   ├── __init__.py
│   │   ├── pool.py            # Connection pooling
│   │   └── http_client.py     # HTTP client (httpx)
│   └── utils/
│       ├── __init__.py
│       ├── backoff.py         # Retry backoff utilities
│       └── time.py            # Time utilities
├── tests/                     # Test-driven: tests written FIRST
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── unit/                  # Unit tests (mocked dependencies)
│   │   ├── test_config.py
│   │   ├── test_router.py
│   │   ├── test_load_balancer.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_rate_limiter.py
│   │   ├── test_health_checker.py
│   │   └── test_retry.py
│   ├── integration/           # Integration tests (real components)
│   │   ├── test_inbound_listener.py
│   │   ├── test_outbound_listener.py
│   │   ├── test_pipeline.py
│   │   └── test_discovery.py
│   └── e2e/                   # End-to-end tests
│       └── test_sidecar_e2e.py
├── examples/
│   ├── basic-config.yaml
│   └── k8s-deployment.yaml
└── scripts/
    ├── build.sh
    ├── test.sh
    └── lint.sh
```

### 4.1 Directory Purpose

| Directory | Purpose |
|-----------|---------|
| `sidecar/` | Core application package (src layout) |
| `sidecar/config/` | Configuration loading and Pydantic validation |
| `sidecar/listeners/` | Async HTTP listeners (aiohttp) for inbound/outbound |
| `sidecar/pipeline/` | Request processing pipeline components |
| `sidecar/discovery/` | Service discovery mechanisms |
| `sidecar/health/` | Active and passive health checking logic |
| `sidecar/security/` | TLS, mTLS, and authentication features |
| `sidecar/telemetry/` | Prometheus metrics, OpenTelemetry tracing, structlog |
| `sidecar/connection/` | Connection pooling and httpx client |
| `sidecar/utils/` | Shared utilities (backoff, time, etc.) |
| `tests/` | **TDD: Tests written before implementation** |
| `tests/unit/` | Unit tests with mocked dependencies |
| `tests/integration/` | Integration tests for component interaction |
| `tests/e2e/` | End-to-end tests with real HTTP |
| `examples/` | Example configurations and K8s deployments |
| `docs/` | Architecture, configuration, and deployment docs |

---

## 5. Technology Stack

### 5.1 Primary: Python 3

**Rationale:**
- Team preference and existing Docker environment
- Rich async ecosystem with `asyncio`
- Rapid development with excellent testing support
- Strong typing with Pydantic for configuration safety
- Mature HTTP libraries (`aiohttp`, `httpx`)
- Easy integration with Prometheus, OpenTelemetry, and logging

**Core Dependencies:**

| Package | Purpose |
|---------|---------|
| `python>=3.10` | Runtime |
| `aiohttp` | Async HTTP server/client for proxying requests |
| `httpx` | Modern async HTTP client for outbound requests |
| `fastapi` | Async web framework for sidecar admin API |
| `uvicorn` | ASGI server for FastAPI |
| `pydantic` | Configuration validation and settings management |
| `pydantic-settings` | Environment-based configuration |
| `pyyaml` | YAML configuration file parsing |

**Testing Dependencies:**

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support for pytest |
| `pytest-cov` | Code coverage reporting |
| `httpx` (test client) | Async HTTP testing |
| `respx` | Mock async HTTP for httpx |
| `aioresponses` | Mock async HTTP for aiohttp |

**Observability Dependencies:**

| Package | Purpose |
|---------|---------|
| `prometheus-client` | Prometheus metrics |
| `opentelemetry-api` | OpenTelemetry tracing API |
| `opentelemetry-sdk` | OpenTelemetry SDK |
| `opentelemetry-exporter-otlp` | OTLP trace exporter |
| `structlog` | Structured logging |

**Additional Utilities:**

| Package | Purpose |
|---------|---------|
| `click` | CLI argument parsing |
| `python-dotenv` | Environment file loading |
| `tenacity` | Retry logic with backoff |
| `aioretry` | Async retry decorator |

**Project Setup (pyproject.toml):**
```toml
[project]
name = "service-mesh-sidecar"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "aiohttp>=3.9",
    "httpx>=0.26",
    "fastapi>=0.109",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "pyyaml>=6.0",
    "click>=8.1",
    "tenacity>=8.2",
    "prometheus-client>=0.19",
    "structlog>=24.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "respx>=0.21",
    "aioresponses>=0.7",
    "ruff>=0.2",
    "mypy>=1.8",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=sidecar --cov-report=term-missing"

[tool.ruff]
line-length = 88
target-version = "py310"
```

---

## 6. Implementation Phases (Test-Driven)

> **TDD Rule**: For each task below, write the test(s) **first**, then implement to pass them.

### Phase 1: Foundation (MVP)

**Goal:** Basic proxy that forwards requests with minimal features.

**TDD Workflow per Task:**
1. Write failing test in `tests/unit/` or `tests/integration/`
2. Run test → verify it fails (Red)
3. Implement minimal code to pass (Green)
4. Refactor if needed (Refactor)
5. Move to next task

**Tasks:**
- [ ] **Test**: `tests/unit/test_config.py` - Pydantic config schema validation
- [ ] **Test**: `tests/unit/test_main.py` - CLI argument parsing
- [ ] Project scaffolding: `pyproject.toml`, `sidecar/` package structure
- [ ] **Test**: `tests/integration/test_inbound_listener.py` - aiohttp inbound server
- [ ] **Test**: `tests/integration/test_outbound_listener.py` - aiohttp outbound client
- [ ] Basic HTTP proxy (inbound → backend, outbound → destination)
- [ ] **Test**: `tests/unit/test_config_loader.py` - YAML config loading
- [ ] Configuration file loading (YAML via Pydantic)
- [ ] CLI with basic options (config path, ports) using Click
- [ ] Basic structured logging with structlog
- [ ] Dockerfile and basic K8s manifests

**Deliverable:** Sidecar can proxy HTTP traffic between services. All tests pass.

---

### Phase 2: Routing & Load Balancing

**Goal:** Intelligent request routing and distribution.

**TDD Workflow per Task:**
1. Write failing test first (Red)
2. Implement to pass (Green)
3. Refactor (Refactor)

**Tasks:**
- [ ] **Test**: `tests/unit/test_router.py` - Path/header/host matching
- [ ] Path-based routing engine
- [ ] Header-based routing
- [ ] Host-based routing
- [ ] **Test**: `tests/unit/test_load_balancer.py` - Round-robin algorithm
- [ ] Round-robin load balancer
- [ ] **Test**: `tests/unit/test_load_balancer.py` - Least-connections algorithm
- [ ] Least-connections load balancer
- [ ] **Test**: `tests/unit/test_discovery.py` - DNS resolver
- [ ] Service discovery (DNS-based initially)
- [ ] **Test**: `tests/unit/test_connection_pool.py` - Connection pooling
- [ ] Connection pooling with httpx

**Deliverable:** Requests can be routed to multiple backends with load balancing. All tests pass.

---

### Phase 3: Reliability Features

**Goal:** Handle failures gracefully.

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_circuit_breaker.py` - State machine transitions
- [ ] Circuit breaker implementation (closed → open → half-open)
- [ ] **Test**: `tests/unit/test_retry.py` - Retry with exponential backoff
- [ ] Retry logic with backoff (tenacity)
- [ ] **Test**: `tests/unit/test_timeout.py` - Request timeout enforcement
- [ ] Request timeouts
- [ ] **Test**: `tests/unit/test_health_checker.py` - Active HTTP probes
- [ ] Active health checks (HTTP probes)
- [ ] **Test**: `tests/unit/test_health_tracker.py` - Passive failure tracking
- [ ] Passive health tracking (eject on failures)
- [ ] **Test**: `tests/unit/test_rate_limiter.py` - Token bucket algorithm
- [ ] Rate limiting (token bucket)

**Deliverable:** Sidecar protects services from cascading failures. All tests pass.

---

### Phase 4: Security

**Goal:** Secure communication.

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_tls.py` - TLS configuration loading
- [ ] TLS termination (inbound)
- [ ] TLS origination (outbound)
- [ ] **Test**: `tests/integration/test_mtls.py` - mTLS handshake
- [ ] mTLS support
- [ ] Certificate management (initial: file-based)
- [ ] **Test**: `tests/unit/test_auth.py` - API key / bearer token auth
- [ ] Basic authentication (API key, bearer token)

**Deliverable:** All inter-service traffic is encrypted. All tests pass.

---

### Phase 5: Observability

**Goal:** Full visibility into traffic.

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_metrics.py` - Prometheus metrics collection
- [ ] Prometheus metrics (request count, latency, errors)
- [ ] **Test**: `tests/unit/test_tracing.py` - OpenTelemetry span creation
- [ ] OpenTelemetry tracing integration
- [ ] **Test**: `tests/unit/test_logging.py` - Structured log output
- [ ] Structured JSON logging (structlog)
- [ ] Request/response logging (optional, debug mode)
- [ ] **Test**: `tests/integration/test_admin_api.py` - FastAPI health endpoints
- [ ] Health endpoint for sidecar itself (`/sidecar/health`)

**Deliverable:** Sidecar exposes rich telemetry for monitoring. All tests pass.

---

### Phase 6: Advanced Features

**Goal:** Production-ready enhancements.

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_router.py` - Weighted routing
- [ ] Weighted routing for canary/blue-green
- [ ] Consistent hashing for session affinity
- [ ] gRPC support (full protocol)
- [ ] HTTP/2 support
- [ ] **Test**: `tests/integration/test_config_reload.py` - Hot reload
- [ ] Dynamic configuration reload (SIGHUP, API)
- [ ] K8s-native discovery (endpoints API)
- [ ] SPIFFE/SPIRE integration for mTLS

**Deliverable:** Feature-complete sidecar for production use. All tests pass.

---

## 7. Configuration Schema

### 7.1 Example Configuration File

```yaml
# sidecar-config.yaml
version: "1.0"

# Server settings
server:
  inbound_port: 15000      # Traffic coming INTO the pod
  outbound_port: 15001     # Traffic going OUT of the pod
  admin_port: 15002        # Admin/metrics endpoint

# Logging
logging:
  level: info              # debug, info, warn, error
  format: json             # json, plain

# Service discovery
discovery:
  type: kubernetes         # kubernetes, dns, static
  namespace: default
  refresh_interval: 30s

# Outbound routing rules
routes:
  - name: user-service
    match:
      host: user-service.default.svc.cluster.local
    cluster:
      name: user-service
      endpoints:
        - address: user-service.default.svc.cluster.local
          port: 8080
      load_balancing:
        algorithm: round_robin
      health_check:
        type: http
        path: /health
        interval: 10s
      circuit_breaker:
        failure_threshold: 5
        timeout: 30s
      retry:
        max_attempts: 3
        retry_on: [5xx, connect_failure]

  - name: api-canary
    match:
      path_prefix: /api/v2
      headers:
        X-Canary: "true"
    cluster:
      name: api-service-v2
      endpoints:
        - address: api-service-v2.default.svc.cluster.local
          port: 8080
          weight: 100
      load_balancing:
        algorithm: weighted

# Rate limiting
rate_limits:
  - scope: global
    limit: 10000
    window: 1s
  - scope: client
    limit: 100
    window: 1s

# TLS settings
tls:
  mode: strict             # strict, permissive, disabled
  ca_cert: /etc/certs/ca.crt
  server_cert: /etc/certs/server.crt
  server_key: /etc/certs/server.key
  client_cert: /etc/certs/client.crt
  client_key: /etc/certs/client.key

# Telemetry
telemetry:
  metrics:
    enabled: true
    port: 9090
    path: /metrics
  tracing:
    enabled: true
    exporter: otlp           # otlp, jaeger, zipkin
    endpoint: http://otel-collector:4317
  logging:
    access_log: true
```

---

## 8. Testing Strategy (Test-Driven Development)

> **Core Principle**: Tests are written **before** implementation. Each feature follows the Red-Green-Refactor cycle.

### 8.1 TDD Workflow

For every feature or component:

1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Implement minimal code to make the test pass
3. **Refactor**: Clean up code while keeping tests green

**Example TDD Cycle for Circuit Breaker:**
```python
# tests/unit/test_circuit_breaker.py  (WRITE FIRST)
import pytest
from sidecar.pipeline.circuit_breaker import CircuitBreaker, State

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Circuit breaker should open after N consecutive failures."""
    cb = CircuitBreaker(failure_threshold=3)
    
    # Simulate failures
    for _ in range(3):
        await cb.record_failure()
    
    assert cb.state == State.OPEN
    assert not cb.allow_request()

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Circuit breaker should transition to half-open after timeout."""
    cb = CircuitBreaker(failure_threshold=2, timeout=0.1)
    
    await cb.record_failure()
    await cb.record_failure()
    assert cb.state == State.OPEN
    
    await asyncio.sleep(0.15)  # Wait for timeout
    assert cb.state == State.HALF_OPEN
```

### 8.2 Unit Tests (pytest + pytest-asyncio)

- Test each pipeline component in isolation with mocked dependencies
- Use `pytest-asyncio` for async function testing
- Use `respx` / `aioresponses` to mock HTTP calls
- Cover edge cases: timeouts, errors, malformed requests, race conditions

**Test File Structure:**
```python
# tests/unit/test_rate_limiter.py
import pytest
from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

@pytest.fixture
def rate_limiter():
    return TokenBucketRateLimiter(rate=10, burst=20)

@pytest.mark.asyncio
async def test_allows_requests_under_limit(rate_limiter):
    for _ in range(10):
        assert await rate_limiter.allow("client-1") is True

@pytest.mark.asyncio
async def test_rejects_when_bucket_empty(rate_limiter):
    for _ in range(20):
        await rate_limiter.allow("client-2")
    assert await rate_limiter.allow("client-2") is False
```

### 8.3 Integration Tests

- Test component interactions (e.g., router + load balancer)
- Test full request pipeline end-to-end in-process
- Test circuit breaker state transitions with real timing
- Test rate limiting accuracy under load

**Use real components, mock only external services:**
```python
# tests/integration/test_pipeline.py
import pytest
from sidecar.pipeline import RequestPipeline

@pytest.mark.asyncio
async def test_full_pipeline_flow():
    pipeline = RequestPipeline(config=test_config)
    # Real components, mock only discovery/backend
    with respx.mock:
        respx.get("http://backend:8080/health").mock(return_value=Response(200))
        response = await pipeline.process(request)
        assert response.status_code == 200
```

### 8.4 E2E Tests

- Deploy sidecar with mock backend services
- Verify routing, load balancing, failover behavior
- Verify mTLS handshake (if enabled)
- Verify telemetry collection (metrics, traces)
- Use Docker Compose for isolated test environment

### 8.5 Performance Tests

- Benchmark request throughput (locust, wrk)
- Measure latency overhead (target: <5ms p99 added by sidecar)
- Test under high connection counts
- Stress test rate limiter and circuit breaker

### 8.6 Security Tests

- Verify mTLS enforcement
- Test certificate validation
- Penetration testing for common vulnerabilities

### 8.7 Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sidecar --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only async tests
pytest -k "async"

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/test_circuit_breaker.py::test_circuit_breaker_opens_after_threshold
```

---

## 9. Deployment Considerations

### 9.1 Kubernetes Integration

**Sidecar Injection:**
- Use `initContainer` or `MutatingWebhook` for automatic injection
- Example pod spec with sidecar:

```yaml
spec:
  containers:
    - name: app
      image: my-service:latest
      ports:
        - containerPort: 8080
    - name: sidecar
      image: service-mesh-sidecar:latest
      args: ["--config", "/etc/sidecar/config.yaml"]
      ports:
        - containerPort: 15000
        - containerPort: 15001
        - containerPort: 15002
      volumeMounts:
        - name: sidecar-config
          mountPath: /etc/sidecar
  volumes:
    - name: sidecar-config
      configMap:
        name: sidecar-config
```

### 9.2 Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 100m | 250m |
| Memory | 128Mi | 256Mi |
| Disk | 50Mi | 100Mi |

### 9.3 Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /sidecar/health` | Liveness probe |
| `GET /sidecar/ready` | Readiness probe |
| `GET /sidecar/metrics` | Prometheus metrics |
| `GET /sidecar/config` | Current configuration (admin) |

---

## 10. Open Questions for Review

1. **Control Plane**: Should we build a centralized control plane (like Istio), or keep it config-file based?
2. **Scope**: Focus on HTTP/gRPC first, or support additional protocols (TCP, Redis, etc.)?
3. **K8s Dependency**: Tightly coupled to K8s, or support standalone/container-only deployments?
4. **mTLS Provider**: Build our own PKI, or integrate with existing (SPIFFE, cert-manager)?
5. **Observability Backend**: Assume Prometheus + Grafana + Jaeger, or support other backends?
6. **API Compatibility**: Should the sidecar be Envoy-compatible (xDS API) for interoperability?
7. **Async Framework**: Use FastAPI for admin API only, or also for proxy listeners? (aiohttp vs FastAPI)

---

## 11. Next Steps (Test-Driven Workflow)

1. **Review this plan** – Provide feedback on architecture, features, tech stack
2. **Answer open questions** – Confirm decisions (control plane, scope, etc.)
3. **Initialize Python project** – Create `pyproject.toml`, `sidecar/` package, `tests/` structure
4. **Setup dev environment** – Install deps: `pip install -e ".[dev]"` and run `pytest` (should show 0 tests)
5. **Start TDD cycle** – For each Phase 1 task:
   - Write test first → verify Red
   - Implement → verify Green
   - Refactor → verify Green
6. **Implement Phase 1** – Foundation/MVP (all tests must pass)
7. **Iterate** – Build features incrementally following TDD, gather feedback

**Quick Start Commands:**
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# TDD workflow
pytest tests/unit/test_config.py -v        # Write test, run (Red)
# ... implement ...
pytest tests/unit/test_config.py -v        # Run (Green)

# Run all tests
pytest

# Coverage
pytest --cov=sidecar --cov-report=term-missing
```

---

## Appendix A: Feature Comparison Matrix

| Feature | Phase | Priority | Complexity |
|---------|-------|----------|------------|
| Basic HTTP proxy | 1 | Must | Low |
| Path-based routing | 2 | Must | Medium |
| Round-robin LB | 2 | Must | Low |
| Least-connections LB | 2 | Should | Low |
| Circuit breaker | 3 | Must | Medium |
| Retry with backoff | 3 | Must | Low |
| Active health checks | 3 | Must | Medium |
| Token bucket rate limit | 3 | Should | Medium |
| TLS termination | 4 | Must | High |
| mTLS | 4 | Must | High |
| Prometheus metrics | 5 | Must | Low |
| OpenTelemetry tracing | 5 | Should | Medium |
| gRPC support | 6 | Should | High |
| K8s discovery | 6 | Should | Medium |
| Weighted routing | 6 | Nice | Low |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Sidecar** | Proxy deployed alongside each service instance |
| **Service Mesh** | Infrastructure layer for service-to-service communication |
| **Circuit Breaker** | Pattern to stop requests to failing services |
| **mTLS** | Mutual TLS – both client and server authenticate |
| **xDS** | Envoy's discovery service API protocol |
| **SPIFFE** | Standard for service identity in zero-trust networks |

---

*Document Version: 1.1*
*Updated: 2026-03-25*
*Status: Updated - Python 3 + TDD*
*Language: Python 3 (aiohttp, httpx, fastapi, uvicorn, pydantic, pytest, pytest-asyncio)*
*Approach: Test-Driven Development*
