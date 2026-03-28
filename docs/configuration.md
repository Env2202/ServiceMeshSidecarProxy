# Service Mesh Sidecar Proxy - Configuration

## Overview

This document describes the configuration options for the service mesh sidecar proxy, with emphasis on **logging** and **request ID propagation** settings.

## Configuration File Format

Configuration is provided via YAML file:

```bash
python -m sidecar --config ./sidecar-config.yaml
```

## Full Configuration Example

```yaml
version: "1.0"

# Server settings
server:
  inbound_port: 15000      # Traffic coming INTO the pod
  outbound_port: 15001     # Traffic going OUT of the pod
  admin_port: 15002        # Admin/metrics endpoint

# Logging configuration
logging:
  level: info              # debug, info, warning, error
  format: json             # json, console
  # Request ID settings
  request_id_header: "X-Request-ID"  # Header name for request ID

# Service discovery
discovery:
  type: static             # static, dns, kubernetes
  
# Routing rules
routes:
  - name: user-service
    match:
      path_prefix: /api/users
    cluster:
      name: users
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

# Rate limiting
rate_limits:
  - scope: client
    limit: 100
    window: 1s
```

## Logging Configuration

### Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `debug` | Detailed information | Development, troubleshooting |
| `info` | General information | Production default |
| `warning` | Warning messages | Deprecations, recoverable issues |
| `error` | Error messages | Failures, exceptions |

### Log Formats

#### JSON Format (Recommended for Production)

```yaml
logging:
  level: info
  format: json
```

Output:
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

#### Console Format (Recommended for Development)

```yaml
logging:
  level: debug
  format: console
```

Output:
```
2024-01-15 09:23:45 [info     ] Route matched                  cluster=users component=router path=/api/users/123 request_id=req-a1b2c3d4e5f6 route=user-service
```

### Request ID Header

The request ID header name is configurable:

```yaml
logging:
  request_id_header: "X-Request-ID"  # Default
  # Or use custom header name:
  # request_id_header: "X-Correlation-ID"
  # request_id_header: "X-Trace-ID"
```

**Important**: The header name must match between services for proper propagation.

## Request ID Propagation

### Header Flow

The request ID flows through the system via HTTP headers:

```
Client Request
    │
    │ X-Request-ID: req-abc123 (client-provided or generated)
    ▼
┌──────────────┐
│   Inbound    │──► Extracts/generates request ID
│   Listener   │──► Creates RequestContext
└──────────────┘
    │
    │ All logs include request_id
    ▼
┌──────────────┐
│   Pipeline   │──► Router, Load Balancer, Circuit Breaker, Rate Limiter
└──────────────┘
    │
    │ X-Request-ID: req-abc123 (forwarded to backend)
    ▼
┌──────────────┐
│   Outbound   │──► Injects header into outgoing requests
│   Client     │
└──────────────┘
    │
    │ X-Request-ID: req-abc123
    ▼
┌──────────────┐
│   Backend    │──► Receives same request ID
│   Service    │
└──────────────┘
```

### Request ID Format

Request IDs are auto-generated in format: `req-<12-char-hex>`

- Example: `req-a1b2c3d4e5f6`
- Total length: 16 characters
- URL-safe, no special characters

You can provide your own request ID in the header:

```bash
curl -H "X-Request-ID: my-custom-id-123" http://localhost:15000/api/users
```

## Environment Variables

Configuration can be overridden via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SIDECAR_LOG_LEVEL` | Log level | `info` |
| `SIDECAR_LOG_FORMAT` | Log format | `json` |
| `SIDECAR_REQUEST_ID_HEADER` | Request ID header name | `X-Request-ID` |
| `SIDECAR_INBOUND_PORT` | Inbound listener port | `15000` |
| `SIDECAR_OUTBOUND_PORT` | Outbound listener port | `15001` |
| `SIDECAR_ADMIN_PORT` | Admin API port | `15002` |

Example:
```bash
export SIDECAR_LOG_LEVEL=debug
export SIDECAR_LOG_FORMAT=console
python -m sidecar --config ./config.yaml
```

## Minimal Configuration

For testing or simple deployments:

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
  - name: default
    match:
      path_prefix: /
    cluster:
      name: backend
      endpoints:
        - address: localhost
          port: 8080
```

## Configuration Validation

The sidecar validates configuration on startup and will fail fast with clear error messages if:

- Required fields are missing
- Port numbers are invalid
- Log level is not one of: debug, info, warning, error
- Log format is not one of: json, console

## Runtime Configuration

Currently, configuration is loaded once at startup. Dynamic configuration reload is not supported in the POC version.
