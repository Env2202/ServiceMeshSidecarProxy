# Service Mesh Sidecar Proxy - Logging & Tracing

## Overview

This document describes the **structured logging** and **request ID propagation** features of the service mesh sidecar proxy. These features enable comprehensive observability and debugging capabilities for microservices communication.

## Features

- ✅ **Request ID Propagation**: Unique ID assigned to each request and propagated through all components
- ✅ **Structured Logging**: JSON-formatted logs with consistent schema
- ✅ **Contextual Logging**: Automatic inclusion of request_id in all log entries
- ✅ **Component Identification**: Each log entry includes the component name
- ✅ **Header Forwarding**: Request ID forwarded to downstream services via HTTP headers

## Quick Start

### Basic Usage

```python
from sidecar.telemetry.context import RequestContext
from sidecar.telemetry.logging import configure_logging, get_logger

# Configure logging
configure_logging(level="info", format="json")

# Create request context
ctx = RequestContext.create(method="GET", path="/api/users")
ctx.set_current()

# Get logger - request_id is automatically bound
logger = get_logger("my_component")
logger.info("Processing request", user_id=123)
```

Output:
```json
{
  "request_id": "req-a1b2c3d4e5f6",
  "component": "my_component",
  "event": "Processing request",
  "user_id": 123,
  "timestamp": "2024-01-15T09:23:45.125Z",
  "level": "info"
}
```

## Request ID Propagation

### How It Works

1. **Inbound**: Request arrives at `:15000`
   - Extract `X-Request-ID` from headers (if present)
   - Or generate new unique ID: `req-<12-char-hex>`
   - Create `RequestContext` and set as current

2. **Pipeline**: Request flows through components
   - Router logs routing decisions with request_id
   - Load balancer logs endpoint selection with request_id
   - Circuit breaker logs state checks with request_id
   - Rate limiter logs decisions with request_id

3. **Outbound**: Request forwarded to backend
   - `X-Request-ID` header injected into outgoing request
   - Backend service receives same request ID

4. **Response**: Response returned to client
   - `X-Request-ID` header included in response
   - Request completion logged with duration

### Request ID Format

- **Format**: `req-<12-character-hex>`
- **Example**: `req-a1b2c3d4e5f6`
- **Length**: 16 characters
- **Characteristics**: URL-safe, human-readable, unique

### Custom Request ID

Clients can provide their own request ID:

```bash
curl -H "X-Request-ID: my-custom-id-123" http://localhost:15000/api/users
```

The sidecar will:
1. Use the provided ID instead of generating one
2. Propagate this ID through all components
3. Return the same ID in the response header
4. Forward the ID to downstream services

## Structured Logging

### Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| `debug` | Detailed debugging | Endpoint selection, internal state |
| `info` | Normal operations | Request started/completed, routing decisions |
| `warning` | Recoverable issues | Rate limit approached, circuit breaker opening |
| `error` | Failures | Request failures, connection errors |

### Log Formats

#### JSON Format (Production)

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

#### Console Format (Development)

```yaml
logging:
  level: debug
  format: console
```

Output:
```
2024-01-15 09:23:45 [info     ] Route matched                  cluster=users component=router path=/api/users/123 request_id=req-a1b2c3d4e5f6 route=user-service
```

### Standard Log Fields

Every log entry includes:

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | ISO 8601 timestamp | `2024-01-15T09:23:45.125Z` |
| `level` | Log level | `info`, `debug`, `warning`, `error` |
| `component` | Source component | `router`, `load_balancer`, `circuit_breaker` |
| `event` | Log message/event | `Route matched`, `Request completed` |
| `request_id` | Request ID (when in context) | `req-a1b2c3d4e5f6` |
| `logger` | Logger name | `sidecar` |

### Component-Specific Fields

Components add their own contextual fields:

**Router**:
- `route`: Matched route name
- `cluster`: Target cluster
- `path`: Request path

**Load Balancer**:
- `algorithm`: Load balancing algorithm used
- `endpoint`: Selected endpoint
- `index`: Endpoint index (for round-robin)

**Circuit Breaker**:
- `state`: Current state (CLOSED, OPEN, HALF_OPEN)
- `failure_count`: Number of consecutive failures
- `cluster`: Target cluster

**Rate Limiter**:
- `key`: Client key
- `allowed`: Whether request was allowed
- `remaining_tokens`: Tokens remaining in bucket

## Using the Logger

### Basic Logging

```python
from sidecar.telemetry.logging import get_logger

logger = get_logger("my_component")

logger.debug("Debug information", detail="value")
logger.info("Informational message")
logger.warning("Warning message", threshold=100)
logger.error("Error occurred", error=str(exception))
```

### Logging with Context

```python
from sidecar.telemetry.context import RequestContext
from sidecar.telemetry.logging import get_logger

# Create and set context
ctx = RequestContext.create(method="POST", path="/api/orders")
ctx.set_current()

# All logs now include request_id automatically
logger = get_logger("order_service")
logger.info("Processing order", order_id=12345)
```

Output:
```json
{
  "request_id": "req-84b126b43907",
  "component": "order_service",
  "event": "Processing order",
  "order_id": 12345,
  "timestamp": "2024-01-15T09:23:45.125Z",
  "level": "info"
}
```

### Logging Without Context

The logger works outside request context (e.g., background tasks):

```python
logger = get_logger("background_task")
logger.info("Starting background job")
```

Output (no request_id):
```json
{
  "component": "background_task",
  "event": "Starting background job",
  "timestamp": "2024-01-15T09:23:45.125Z",
  "level": "info"
}
```

## Log Aggregation Examples

### Query by Request ID

**Elasticsearch / Kibana**:
```
request_id: "req-a1b2c3d4e5f6"
```

**Grafana Loki**:
```
{job="sidecar"} |= "req-a1b2c3d4e5f6"
```

**Splunk**:
```
request_id="req-a1b2c3d4e5f6"
```

### Query by Component

```
component: "router" AND level: "error"
```

### Query by Time Range

```
request_id: "req-a1b2c3d4e5f6" AND timestamp: [2024-01-15T09:00:00 TO 2024-01-15T10:00:00]
```

## Correlating Logs Across Services

When the sidecar forwards requests to downstream services, the `X-Request-ID` header is included. Downstream services should:

1. Extract the `X-Request-ID` header from incoming requests
2. Include the same ID in their logs
3. Forward the header to any further downstream services

Example downstream service (Python):

```python
from flask import Flask, request
import logging

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    request_id = request.headers.get('X-Request-ID', 'unknown')
    logging.info(f"Getting users", extra={"request_id": request_id})
    return {"users": []}
```

## Demo Scripts

Two demo scripts are provided to showcase the logging feature:

### 1. Request ID Propagation Demo

```bash
python3 scripts/demo_request_id.py
```

Demonstrates:
- Request context creation
- Structured logging with JSON output
- Component logging (router, load balancer, circuit breaker, rate limiter)
- Log capture and verification

### 2. Full Proxy Demo

```bash
python3 test_proxy_demo.py
```

Demonstrates:
- Complete request lifecycle
- Request ID propagation through all components
- Routing, load balancing, circuit breaker, rate limiting
- Metrics collection

## Troubleshooting

### No Request ID in Logs

**Symptom**: Logs don't contain `request_id` field

**Solutions**:
1. Ensure `RequestContext` is created and `set_current()` is called
2. Verify you're using `get_logger()` from `sidecar.telemetry.logging`
3. Check that middleware is registered (for inbound requests)

### Request ID Not Propagating

**Symptom**: Downstream services don't receive the request ID

**Solutions**:
1. Verify `X-Request-ID` header name matches between services
2. Check outbound client is configured to inject headers
3. Ensure context is set before making outbound requests

### Too Much Log Output

**Solution**: Increase log level

```yaml
logging:
  level: warning  # Only warnings and errors
```

### Logs Not in JSON Format

**Solution**: Verify configuration

```yaml
logging:
  format: json
```

## Performance Considerations

- **Overhead**: < 1ms per request for logging
- **Memory**: Context variables are lightweight
- **Concurrency**: Context is properly isolated between concurrent requests
- **JSON Serialization**: Minimal overhead with structlog

## Future Enhancements

### OpenTelemetry Tracing (Post-POC)

When OpenTelemetry is added, it will integrate with the existing request context:

```python
# Future enhancement
from sidecar.telemetry.tracing import start_span
from sidecar.telemetry.context import REQUEST_ID_CTX

with start_span("process_request") as span:
    request_id = REQUEST_ID_CTX.get()
    span.set_attribute("request.id", request_id)
```

### Distributed Context Propagation (Post-POC)

W3C Trace Context support for interoperability with other tracing systems.

## References

- [Architecture Documentation](./architecture.md)
- [Configuration Guide](./configuration.md)
- [Deployment Guide](./deployment.md)
- [Request ID Execution Plan](./request-id-execution-plan.md)