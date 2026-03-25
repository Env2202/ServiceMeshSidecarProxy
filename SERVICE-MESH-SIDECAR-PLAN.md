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

### 1.2 Key Features (POC Scope)

| Feature | Description |
|---------|-------------|
| **Service Discovery** | DNS-based or static endpoint resolution |
| **Routing** | Path-based, header-based, and host-based routing |
| **Load Balancing** | Round-robin, least-connections |
| **Circuit Breaker** | Fail-fast patterns for downstream protection |
| **Rate Limiting** | Per-client and global rate limiting (token bucket) |
| **Health Checks** | Active HTTP probes and passive failure tracking |
| **Retry Logic** | Configurable retry with exponential backoff |
| **Timeout Handling** | Request and connection timeouts |
| **Telemetry** | Prometheus metrics only (request count, latency, errors) |

### 1.3 Non-Goals (Out of Scope for POC)

- Centralized control plane (config-file based only)
- Service mesh visualization UI
- Multi-datacenter/multi-region federation
- Non-HTTP protocols (gRPC, TCP, Redis, etc.)
- Kubernetes integration (no K8s client, no sidecar injection)
- mTLS / TLS termination (plain HTTP only)
- Distributed tracing (Prometheus metrics only)
- Envoy/xDS API compatibility

> **POC Scope**: Simple HTTP proxy sidecar with config-file based routing, load balancing, circuit breaker, rate limiting, health checks, and Prometheus metrics. Deployable standalone or in containers.

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
│                                  │  │  (Security: Deferred)   │  │  │
│                                  │  ├─────────────────────────┤  │  │
│                                  │  │  Telemetry (Prometheus  │  │  │
│                                  │  │  Metrics + Logging)     │  │  │
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
5. Establishes plain HTTP connection to backend (no TLS in POC)
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
│  │  │              Connection Pool (plain HTTP)               │ ││
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

### 3.7 Security (Deferred for POC)

> **POC Decision**: Security features are skipped. Plain HTTP only.

**Features (Post-POC):**
- TLS termination (inbound)
- TLS origination (outbound)
- mTLS between services
- Configurable TLS modes
- SPIFFE/SPIRE integration

**Note**: The architecture is designed to add security later. For POC, all traffic is plain HTTP.

### 3.8 Telemetry (POC: Prometheus Metrics Only)

**Metrics (Prometheus format):**
- Request count, latency (p50, p99), error rates
- Circuit breaker state transitions
- Rate limit hits
- Connection pool stats
- Health check results

**Tracing (Deferred):**
- OpenTelemetry integration *(Post-POC)*
- W3C Trace Context propagation *(Post-POC)*

**Logging:**
- Structured JSON logs (structlog)
- Configurable log levels per component
- Request/response logging (debug mode)

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
- [ ] **Test**: `tests/unit/test_main.py` - CLI argument parsing (click)
- [ ] Project scaffolding: `pyproject.toml`, `sidecar/` package structure
- [ ] **Test**: `tests/integration/test_inbound_listener.py` - aiohttp inbound server (:15000)
- [ ] **Test**: `tests/integration/test_outbound_listener.py` - aiohttp outbound client (:15001)
- [ ] Basic HTTP proxy (inbound → backend, outbound → destination)
- [ ] **Test**: `tests/unit/test_config_loader.py` - YAML config loading
- [ ] Configuration file loading (YAML via Pydantic)
- [ ] CLI with basic options (config path, ports) using Click
- [ ] Basic structured logging with structlog
- [ ] Dockerfile (container-only, no K8s-specific)

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

### Phase 4: Security (SKIPPED FOR POC)

> **POC Decision**: Security features (TLS, mTLS) are deferred. Plain HTTP only.

**Goal:** Secure communication. *(Out of scope for POC)*

**Deferred Tasks:**
- TLS termination (inbound)
- TLS origination (outbound)
- mTLS support
- Certificate management
- Authentication (API key, bearer token)

**Note**: Phase 4 tasks can be added post-POC if needed. The architecture is designed to accommodate security layers later.

---

**Deliverable (POC):** N/A - skipped.

---

### Phase 5: Observability (Prometheus Metrics Only)

**Goal:** Visibility into traffic via Prometheus metrics.

> **POC Decision**: Prometheus metrics only. OpenTelemetry tracing deferred.

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_metrics.py` - Prometheus metrics collection
- [ ] Prometheus metrics (request count, latency p50/p99, errors, circuit breaker state)
- [ ] **Test**: `tests/unit/test_logging.py` - Structured log output
- [ ] Structured JSON logging with structlog
- [ ] Request/response logging (debug mode)
- [ ] **Test**: `tests/integration/test_admin_api.py` - FastAPI admin endpoints
- [ ] Admin endpoints: `/sidecar/health`, `/sidecar/ready`, `/sidecar/metrics`

**Deferred (Post-POC):**
- OpenTelemetry tracing integration
- Distributed tracing (W3C Trace Context propagation)

**Deliverable:** Sidecar exposes Prometheus metrics at `/sidecar/metrics`. All tests pass.

---

### Phase 6: Advanced Features (MOSTLY POST-POC)

> **POC Decision**: Focus on core features. Advanced features deferred.

**Goal:** Production-ready enhancements. *(Mostly out of scope for POC)*

**Tasks (TDD per feature):**
- [ ] **Test**: `tests/unit/test_router.py` - Weighted routing *(Nice to have)*
- [ ] Weighted routing for canary/blue-green *(Nice to have)*
- [ ] Consistent hashing for session affinity *(Post-POC)*
- [ ] gRPC support *(Post-POC - HTTP only for POC)*
- [ ] HTTP/2 support *(Post-POC - HTTP/1.1 only)*
- [ ] **Test**: `tests/integration/test_config_reload.py` - Hot reload *(Post-POC)*
- [ ] Dynamic configuration reload (SIGHUP, API) *(Post-POC)*
- [ ] K8s-native discovery *(Post-POC - DNS/static only)*
- [ ] SPIFFE/SPIRE integration *(Post-POC)*

**POC Deliverable:** Core sidecar with config-file based routing, LB, CB, rate limiting, health checks, and Prometheus metrics. All core tests pass.

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
- Verify HTTP proxy flow (no mTLS in POC)
- Verify telemetry collection (metrics, traces)
- Use Docker Compose for isolated test environment

### 8.5 Performance Tests

- Benchmark request throughput (locust, wrk)
- Measure latency overhead (target: <5ms p99 added by sidecar)
- Test under high connection counts
- Stress test rate limiter and circuit breaker

### 8.6 Security Tests

- (Security tests deferred for POC - plain HTTP)
- Basic auth tests (if added post-POC)
- Penetration testing (post-POC)

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

### 9.1 Deployment (POC: Container/Standalone Only)

> **POC Decision**: No Kubernetes integration. Deploy as standalone process or container.

**Standalone:**
```bash
python3 -m sidecar --config ./sidecar-config.yaml
```

**Container (Docker):**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "-m", "sidecar", "--config", "/config/sidecar-config.yaml"]
```

**Example docker-compose.yml:**
```yaml
version: "3.8"
services:
  my-service:
    image: my-service:latest
    ports:
      - "8080:8080"
    depends_on:
      - sidecar
  sidecar:
    image: service-mesh-sidecar:latest
    ports:
      - "15000:15000"  # inbound
      - "15001:15001"  # outbound
      - "15002:15002"  # admin/metrics
    volumes:
      - ./sidecar-config.yaml:/config/sidecar-config.yaml
    command: ["--config", "/config/sidecar-config.yaml"]
```

### 9.2 Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 100m | 250m |
| Memory | 128Mi | 256Mi |
| Disk | 50Mi | 100Mi |

### 9.3 Health Endpoints (FastAPI Admin API)

| Endpoint | Purpose |
|----------|---------|
| `GET /sidecar/health` | Liveness probe |
| `GET /sidecar/ready` | Readiness probe |
| `GET /sidecar/metrics` | Prometheus metrics |
| `GET /sidecar/config` | Current configuration (debug) |

---

## 10. Design Decisions (POC Scope)

The following decisions have been made for this POC:

| # | Decision | Choice |
|---|----------|--------|
| 1 | **Control Plane** | Config-file based (YAML). No centralized control plane. |
| 2 | **Scope** | HTTP only. This is a POC; no gRPC, TCP, or other protocols. |
| 3 | **K8s Dependency** | None. Standalone or container-only deployment. |
| 4 | **mTLS** | Skipped for POC. Plain HTTP only. |
| 5 | **Observability** | Prometheus metrics only. No tracing (OpenTelemetry deferred). |
| 6 | **API Compatibility** | No Envoy/xDS compatibility. Simple custom YAML config. |
| 7 | **Async Framework** | FastAPI for admin API only; aiohttp handles async proxy listeners. |

**Implications for Implementation:**
- No K8s-specific code (no client-go equivalent, no sidecar injection)
- No TLS/mTLS code paths
- No gRPC protocol support
- No distributed tracing (metrics only via prometheus-client)
- Simpler config schema (no xDS, no SPIFFE)
- Clear separation: `aiohttp` for proxy, `fastapi/uvicorn` for `/sidecar/*` admin endpoints

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
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# TDD workflow
python3 -m pytest tests/unit/test_config.py -v    # Write test, run (Red)
# ... implement ...
python3 -m pytest tests/unit/test_config.py -v    # Run (Green)

# Run all tests
python3 -m pytest

# Coverage
python3 -m pytest --cov=sidecar --cov-report=term-missing
```

---

## Appendix A: Feature Comparison Matrix (POC Scope)

| Feature | Phase | Priority | Complexity | Status |
|---------|-------|----------|------------|--------|
| Basic HTTP proxy | 1 | Must | Low | ✅ In Scope |
| Path-based routing | 2 | Must | Medium | ✅ In Scope |
| Round-robin LB | 2 | Must | Low | ✅ In Scope |
| Least-connections LB | 2 | Should | Low | ✅ In Scope |
| Circuit breaker | 3 | Must | Medium | ✅ In Scope |
| Retry with backoff | 3 | Must | Low | ✅ In Scope |
| Active health checks | 3 | Must | Medium | ✅ In Scope |
| Token bucket rate limit | 3 | Should | Medium | ✅ In Scope |
| TLS termination | 4 | - | High | ❌ Skipped (POC) |
| mTLS | 4 | - | High | ❌ Skipped (POC) |
| Prometheus metrics | 5 | Must | Low | ✅ In Scope |
| OpenTelemetry tracing | 5 | - | Medium | ❌ Deferred |
| gRPC support | 6 | - | High | ❌ Skipped (POC) |
| K8s discovery | 6 | - | Medium | ❌ Skipped (POC) |
| Weighted routing | 6 | Nice | Low | ⚪ Nice to have |
| Consistent hashing | 6 | - | Medium | ❌ Skipped (POC) |
| HTTP/2 | 6 | - | Medium | ❌ Skipped (POC) |

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

*Document Version: 1.2*
*Updated: 2026-03-25*
*Status: Finalized for POC*
*Language: Python 3 (aiohttp, httpx, fastapi, uvicorn, pydantic, pytest, pytest-asyncio)*
*Approach: Test-Driven Development*
*POC Scope: HTTP only, config-file based, no K8s, no mTLS, Prometheus metrics only*
