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
├── Cargo.toml                 # or go.mod, package.json, etc.
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   └── deployment.md
├── src/
│   ├── main.rs               # Entry point
│   ├── config/
│   │   ├── mod.rs
│   │   ├── loader.rs         # Load from file/env/K8s ConfigMap
│   │   └── schema.rs         # Configuration schema (serde, etc.)
│   ├── listeners/
│   │   ├── mod.rs
│   │   ├── inbound.rs        # :15000 inbound listener
│   │   └── outbound.rs       # :15001 outbound listener
│   ├── pipeline/
│   │   ├── mod.rs
│   │   ├── auth.rs           # Authentication middleware
│   │   ├── rate_limit.rs     # Rate limiting middleware
│   │   ├── router.rs         # Routing engine
│   │   ├── load_balancer.rs  # LB algorithms
│   │   ├── circuit_breaker.rs
│   │   ├── retry.rs          # Retry handler
│   │   └── timeout.rs        # Timeout enforcement
│   ├── discovery/
│   │   ├── mod.rs
│   │   ├── resolver.rs       # DNS-based or K8s-based discovery
│   │   └── endpoint.rs       # Endpoint representation
│   ├── health/
│   │   ├── mod.rs
│   │   ├── checker.rs        # Active health checking
│   │   └── tracker.rs        # Passive health tracking
│   ├── security/
│   │   ├── mod.rs
│   │   ├── tls.rs            # TLS/mTLS handling
│   │   └── auth.rs           # Authentication providers
│   ├── telemetry/
│   │   ├── mod.rs
│   │   ├── metrics.rs        # Prometheus metrics
│   │   ├── tracing.rs        # OpenTelemetry tracing
│   │   └── logging.rs        # Structured logging
│   ├── connection/
│   │   ├── mod.rs
│   │   ├── pool.rs           # Connection pooling
│   │   └── http.rs           # HTTP client/server
│   └── utils/
│       ├── mod.rs
│       ├── backoff.rs        # Retry backoff utilities
│       └── time.rs           # Time utilities
├── tests/
│   ├── integration/
│   │   ├── routing_test.rs
│   │   ├── load_balance_test.rs
│   │   └── circuit_breaker_test.rs
│   └── e2e/
│       └── mesh_e2e_test.rs
├── examples/
│   ├── basic-config.yaml
│   └── k8s-deployment.yaml
└── scripts/
    ├── build.sh
    └── test.sh
```

### 4.1 Directory Purpose

| Directory | Purpose |
|-----------|---------|
| `src/` | Core application code |
| `src/config/` | Configuration loading and validation |
| `src/listeners/` | Network listeners for inbound/outbound |
| `src/pipeline/` | Request processing pipeline components |
| `src/discovery/` | Service discovery mechanisms |
| `src/health/` | Health checking logic |
| `src/security/` | TLS, auth, and security features |
| `src/telemetry/` | Metrics, tracing, logging |
| `src/connection/` | Connection management |
| `tests/` | Integration and E2E tests |
| `examples/` | Example configurations and deployments |
| `docs/` | Documentation |

---

## 5. Technology Stack

### 5.1 Recommended: Rust

**Rationale:**
- High performance (zero-cost abstractions)
- Memory safety without garbage collection
- Excellent async runtime (Tokio)
- Strong ecosystem for network programming
- Growing service mesh ecosystem (Linkerd, Envoy uses similar patterns)

**Key Crates:**
| Crate | Purpose |
|-------|---------|
| `tokio` | Async runtime |
| `hyper` | HTTP/1.1 and HTTP/2 client/server |
| `tower` | Middleware framework |
| `tonic` | gRPC support |
| `rustls` | TLS implementation |
| `prometheus` | Metrics |
| `opentelemetry` | Tracing |
| `serde` + `serde_yaml` | Configuration |
| `clap` | CLI argument parsing |

### 5.2 Alternative: Go

**Rationale:**
- Excellent concurrency model (goroutines)
- Strong Kubernetes ecosystem
- Faster development iteration
- Good libraries: Envoy proxy patterns, Istio components in Go

**Key Packages:**
| Package | Purpose |
|---------|---------|
| `net/http` | HTTP handling |
| `google.golang.org/grpc` | gRPC |
| `k8s.io/client-go` | Kubernetes API |
| `go.uber.org/zap` | Logging |
| `prometheus/client_golang` | Metrics |

### 5.3 Alternative: Node.js / TypeScript

**Rationale:**
- Rapid prototyping
- Good async I/O
- Easier to find contributors

**Key Packages:**
| Package | Purpose |
|---------|---------|
| `express` / `fastify` | HTTP framework |
| `@grpc/grpc-js` | gRPC |
| `prom-client` | Prometheus metrics |
| `@opentelemetry/*` | Tracing |

---

## 6. Implementation Phases

### Phase 1: Foundation (MVP)

**Goal:** Basic proxy that forwards requests with minimal features.

**Tasks:**
- [ ] Project scaffolding and build setup
- [ ] Basic HTTP proxy (inbound → backend, outbound → destination)
- [ ] Configuration file loading (YAML)
- [ ] CLI with basic options (config path, ports)
- [ ] Basic logging
- [ ] Dockerfile and basic K8s manifests

**Deliverable:** Sidecar can proxy HTTP traffic between services.

---

### Phase 2: Routing & Load Balancing

**Goal:** Intelligent request routing and distribution.

**Tasks:**
- [ ] Path-based routing engine
- [ ] Header-based routing
- [ ] Round-robin load balancer
- [ ] Least-connections load balancer
- [ ] Service discovery (DNS-based initially)
- [ ] Connection pooling

**Deliverable:** Requests can be routed to multiple backends with load balancing.

---

### Phase 3: Reliability Features

**Goal:** Handle failures gracefully.

**Tasks:**
- [ ] Circuit breaker implementation
- [ ] Retry logic with backoff
- [ ] Request timeouts
- [ ] Active health checks (HTTP probes)
- [ ] Passive health tracking (eject on failures)
- [ ] Rate limiting (token bucket)

**Deliverable:** Sidecar protects services from cascading failures.

---

### Phase 4: Security

**Goal:** Secure communication.

**Tasks:**
- [ ] TLS termination (inbound)
- [ ] TLS origination (outbound)
- [ ] mTLS support
- [ ] Certificate management (initial: file-based)
- [ ] Basic authentication (API key, bearer token)

**Deliverable:** All inter-service traffic is encrypted.

---

### Phase 5: Observability

**Goal:** Full visibility into traffic.

**Tasks:**
- [ ] Prometheus metrics (request count, latency, errors)
- [ ] OpenTelemetry tracing integration
- [ ] Structured JSON logging
- [ ] Request/response logging (optional, debug mode)
- [ ] Health endpoint for sidecar itself (`/sidecar/health`)

**Deliverable:** Sidecar exposes rich telemetry for monitoring.

---

### Phase 6: Advanced Features

**Goal:** Production-ready enhancements.

**Tasks:**
- [ ] Weighted routing for canary/blue-green
- [ ] Consistent hashing for session affinity
- [ ] gRPC support (full protocol)
- [ ] HTTP/2 support
- [ ] Dynamic configuration reload (SIGHUP, API)
- [ ] K8s-native discovery (endpoints API)
- [ ] SPIFFE/SPIRE integration for mTLS

**Deliverable:** Feature-complete sidecar for production use.

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

## 8. Testing Strategy

### 8.1 Unit Tests

- Test each pipeline component in isolation
- Mock dependencies (backend servers, discovery)
- Cover edge cases (timeouts, errors, malformed requests)

### 8.2 Integration Tests

- Test component interactions
- Test full request pipeline
- Test circuit breaker state transitions
- Test rate limiting accuracy

### 8.3 E2E Tests

- Deploy sidecar with mock services
- Verify routing, load balancing, failover
- Verify mTLS handshake
- Verify telemetry collection

### 8.4 Performance Tests

- Benchmark request throughput
- Measure latency overhead (target: <1ms p99)
- Test under high connection counts
- Stress test rate limiter and circuit breaker

### 8.5 Security Tests

- Verify mTLS enforcement
- Test certificate validation
- Penetration testing for common vulnerabilities

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

1. **Language Choice**: Rust (performance, safety) vs Go (ecosystem, simplicity) vs other?
2. **Control Plane**: Should we build a centralized control plane (like Istio), or keep it config-file based?
3. **Scope**: Focus on HTTP/gRPC first, or support additional protocols (TCP, Redis, etc.)?
4. **K8s Dependency**: Tightly coupled to K8s, or support standalone/container-only deployments?
5. **mTLS Provider**: Build our own PKI, or integrate with existing (SPIFFE, cert-manager)?
6. **Observability Backend**: Assume Prometheus + Grafana + Jaeger, or support other backends?
7. **API Compatibility**: Should the sidecar be Envoy-compatible (xDS API) for interoperability?

---

## 11. Next Steps

1. **Review this plan** – Provide feedback on architecture, features, tech stack
2. **Decide on language** – Based on team expertise and requirements
3. **Create project skeleton** – Initialize repo with chosen language
4. **Implement Phase 1** – Foundation/MVP
5. **Iterate** – Build features incrementally, gather feedback

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

*Document Version: 1.0*
*Created: 2026-03-25*
*Status: Draft - Awaiting Review*
