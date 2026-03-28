# Service Mesh Sidecar Proxy - Architecture

## Overview

This document describes the architecture of the service mesh sidecar proxy, with particular focus on the **Request ID Propagation** and **Structured Logging** features.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Application Pod                                  │
│  ┌─────────────────────┐         ┌───────────────────────────────────┐ │
│  │   Main Application  │         │       Sidecar Proxy               │ │
│  │   (Business Logic)  │◄────────│   (Communication Layer)           │ │
│  │                     │  loopback│                                   │ │
│  │   Listens on :8080  │         │   Listens on :15000 (inbound)     │ │
│  │                     │         │   Listens on :15001 (outbound)    │ │
│  └─────────────────────┘         │   Admin on :15002                 │ │
│                                  │                                   │ │
│                                  │  ┌─────────────────────────────┐  │ │
│                                  │  │  Request ID Propagation     │  │ │
│                                  │  │  ├─ Context Management      │  │ │
│                                  │  │  ├─ Structured Logging      │  │ │
│                                  │  │  └─ Header Forwarding       │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Routing Engine             │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Load Balancer              │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Circuit Breaker            │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Rate Limiter               │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Health Checker             │  │ │
│                                  │  ├─────────────────────────────┤  │ │
│                                  │  │  Metrics (Prometheus)       │  │ │
│                                  │  └─────────────────────────────┘  │ │
│                                  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Request ID Propagation Architecture

### Request Flow with Request ID

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW WITH REQUEST ID                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐ │
│  │   Client     │────►│   Inbound    │────►│  RequestContext (async context)  │ │
│  │              │     │  Listener    │     │  • request_id: "req-abc123"      │ │
│  └──────────────┘     └──────────────┘     │  • start_time: timestamp         │ │
│                            │               └──────────────────────────────────┘ │
│                            │                         │                          │
│                            ▼                         ▼                          │
│                     ┌──────────────┐     ┌──────────────────────────────────┐  │
│                     │ Extract/     │     │  Structured Logger (structlog)   │  │
│                     │ Generate ID  │     │  • request_id bound to context   │  │
│                     │ (Header/UUID)│     │  • component name auto-added     │  │
│                     └──────────────┘     └──────────────────────────────────┘  │
│                            │                                                     │
│                            ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         PIPELINE COMPONENTS                               │   │
│  │  ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐  │   │
│  │  │ Router  │──►│Rate Limit│──►│Load Bal│──►│ Circuit  │──►│  Retry   │  │   │
│  │  │         │   │          │   │         │   │ Breaker  │   │          │  │   │
│  │  │ "route: │   │"rate:    │   │"select: │   │"state:   │   │"attempt: │  │   │
│  │  │ users"  │   │ allowed" │   │ ep-1"   │   │ CLOSED"  │   │ 1/3"     │  │   │
│  │  └─────────┘   └──────────┘   └─────────┘   └──────────┘   └──────────┘  │   │
│  │       │                                                          │       │   │
│  │       └──────────────────────────────────────────────────────────┘       │   │
│  │                              │                                           │   │
│  │                              ▼                                           │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │   │
│  │  │                     Outbound HTTP Client                          │    │   │
│  │  │  • Inject X-Request-ID header into outgoing request               │    │   │
│  │  │  • Forward to backend service                                     │    │   │
│  │  └──────────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          ▼                                       │
│  ┌──────────────┐     ┌─────────────────────────────────────────────────────┐   │
│  │   Backend    │◄────│  Logs with request_id: "req-abc123" at each stage   │   │
│  │   Service    │     │  • Response includes X-Request-ID header              │   │
│  └──────────────┘     └─────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Request Context (`sidecar.telemetry.context`)

The request context module uses Python's `contextvars` to propagate request IDs through async call chains:

- **`RequestContext`**: Dataclass holding request_id, start_time, method, path, route
- **`REQUEST_ID_CTX`**: ContextVar storing the current request ID
- **`START_TIME_CTX`**: ContextVar storing request start time for duration calculation

**Why contextvars?**
- Works seamlessly with asyncio (essential for this sidecar)
- Propagates through async/await calls automatically
- No need to pass request_id through every function signature
- Isolates concurrent requests (each has its own context)

### 2. Structured Logging (`sidecar.telemetry.logging`)

Uses `structlog` for structured JSON logging with automatic request ID binding:

- **`get_logger(component)`**: Returns a logger with request_id automatically bound from context
- **`configure_logging()`**: Sets up structlog with JSON/console formatters
- **`RequestIDProcessor`**: Custom processor that injects request_id into every log entry

### 3. Inbound Middleware (`sidecar.listeners.middleware`)

Aiohttp middleware that:
1. Extracts `X-Request-ID` from incoming headers (or generates new UUID)
2. Creates and sets up `RequestContext`
3. Logs request start with context
4. Adds `X-Request-ID` to response headers
5. Logs request completion with duration

### 4. Pipeline Components

All pipeline components use structured logging:

| Component | Log Events |
|-----------|------------|
| Router | Route matched, No route found |
| Load Balancer | Endpoint selected |
| Circuit Breaker | State transitions, Request allowed/denied |
| Rate Limiter | Request allowed/denied |

### 5. Outbound Client (`sidecar.listeners.outbound`)

Injects `X-Request-ID` header into outgoing HTTP requests to propagate the request ID to downstream services.

## Data Flow

### Inbound Request (Ingress)

1. **Request Arrival**: Client sends request to `:15000`
2. **Middleware Processing**:
   - Extract or generate `request_id`
   - Create `RequestContext` and set as current
   - Log request start
3. **Pipeline Processing**:
   - Router matches route (logs with request_id)
   - Rate limiter checks limits (logs with request_id)
   - Load balancer selects endpoint (logs with request_id)
   - Circuit breaker checks state (logs with request_id)
4. **Forwarding**: Request forwarded to application on `:8080`
5. **Response**: Response returned with `X-Request-ID` header
6. **Completion**: Request completion logged with duration

### Outbound Request (Egress)

1. **Request Arrival**: Application sends request to `:15001`
2. **Context Extraction**: Get `request_id` from current context
3. **Header Injection**: Add `X-Request-ID` header to outgoing request
4. **Forwarding**: Request sent to backend service
5. **Response**: Response returned to application

## Log Format

### JSON Format (Production)

```json
{
  "request_id": "req-a1b2c3d4e5f6",
  "component": "router",
  "event": "Route matched",
  "route": "user-service",
  "cluster": "users",
  "path": "/api/users/123",
  "timestamp": "2024-01-15T09:23:45.125Z",
  "level": "info",
  "logger": "sidecar"
}
```

### Console Format (Development)

```
2024-01-15 09:23:45 [info     ] Route matched                  cluster=users component=router path=/api/users/123 request_id=req-a1b2c3d4e5f6 route=user-service
```

## Request ID Format

Request IDs are generated in the format: `req-<12-character-hex>`

Examples:
- `req-a1b2c3d4e5f6`
- `req-84b126b43907`

This format is:
- Human-readable (starts with "req-")
- URL-safe (no special characters)
- Compact (16 characters total)
- Unique enough for practical purposes (48 bits of entropy)

## Context Isolation

The architecture ensures context isolation between concurrent requests:

```python
# Each concurrent request has its own context
async def handle_request(request_id):
    ctx = RequestContext.create(existing_id=request_id)
    ctx.set_current()
    # All logs here include this request_id
    await process_request()
    # Context is isolated - no leakage to other requests

# Run multiple requests concurrently
await asyncio.gather(
    handle_request("req-1"),
    handle_request("req-2"),
    handle_request("req-3")
)
# Each request's logs have their own request_id
```

## Integration Points

| File | Purpose |
|------|---------|
| `sidecar/telemetry/context.py` | Request context and contextvars |
| `sidecar/telemetry/logging.py` | Structured logging with structlog |
| `sidecar/listeners/middleware.py` | Request ID middleware |
| `sidecar/listeners/inbound.py` | Inbound listener with middleware |
| `sidecar/listeners/outbound.py` | Outbound client with header injection |
| `sidecar/pipeline/router.py` | Router with logging |
| `sidecar/pipeline/load_balancer.py` | Load balancer with logging |
| `sidecar/pipeline/circuit_breaker.py` | Circuit breaker with logging |
| `sidecar/pipeline/rate_limit.py` | Rate limiter with logging |

## POC Scope

- HTTP only
- Config-file based routing
- No K8s, no mTLS
- **Request ID propagation with structured logging** ✅
- Prometheus metrics only (no OpenTelemetry tracing)
