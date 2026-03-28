# Service Mesh Sidecar Proxy - Deployment

## Overview

This document describes how to deploy the service mesh sidecar proxy, with focus on **logging configuration** and **observability** in production environments.

## Deployment Modes

### 1. Standalone (Development/Testing)

```bash
# Install dependencies
pip install -e ".[dev]"

# Run with configuration
python -m sidecar --config ./sidecar-config.yaml
```

### 2. Docker (Production)

```bash
# Build image
docker build -t sidecar .

# Run with configuration
docker run -d \
  --name sidecar \
  -p 15000:15000 \
  -p 15001:15001 \
  -p 15002:15002 \
  -v ./config.yaml:/config/sidecar-config.yaml \
  -e SIDECAR_LOG_LEVEL=info \
  -e SIDECAR_LOG_FORMAT=json \
  sidecar
```

### 3. Docker Compose (Multi-Service)

```yaml
version: "3.8"
services:
  my-service:
    image: my-service:latest
    ports:
      - "8080:8080"
    network_mode: "service:sidecar"  # Share network with sidecar
    depends_on:
      - sidecar

  sidecar:
    image: sidecar:latest
    ports:
      - "15000:15000"  # inbound
      - "15001:15001"  # outbound
      - "15002:15002"  # admin/metrics
    volumes:
      - ./sidecar-config.yaml:/config/sidecar-config.yaml
    environment:
      - SIDECAR_LOG_LEVEL=info
      - SIDECAR_LOG_FORMAT=json
    command: ["--config", "/config/sidecar-config.yaml"]
```

## Logging Configuration

### Production Logging Setup

For production deployments, use **JSON format** with **info level**:

```yaml
logging:
  level: info
  format: json
  request_id_header: "X-Request-ID"
```

This produces structured logs that can be easily parsed by log aggregators:

```json
{
  "request_id": "req-a1b2c3d4e5f6",
  "component": "inbound",
  "event": "Request completed",
  "method": "GET",
  "path": "/api/users",
  "status": 200,
  "duration_ms": 45.23,
  "timestamp": "2024-01-15T09:23:45.168Z",
  "level": "info"
}
```

### Development Logging Setup

For development, use **console format** with **debug level**:

```yaml
logging:
  level: debug
  format: console
```

This produces human-readable logs:
```
2024-01-15 09:23:45 [info     ] Request completed              component=inbound duration_ms=45.23 method=GET path=/api/users request_id=req-a1b2c3d4e5f6 status=200
```

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

Configure Filebeat to collect JSON logs:

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/sidecar/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

Query logs by request ID in Kibana:
```
request_id: "req-a1b2c3d4e5f6"
```

### Grafana Loki

Configure Promtail to scrape logs:

```yaml
# promtail-config.yml
scrape_configs:
  - job_name: sidecar
    static_configs:
      - targets:
          - localhost
        labels:
          job: sidecar
          __path__: /var/log/sidecar/*.log
    pipeline_stages:
      - json:
          expressions:
            request_id: request_id
            component: component
            level: level
```

Query in Grafana:
```
{job="sidecar"} |= "req-a1b2c3d4e5f6"
```

### Fluentd / Fluent Bit

Example Fluent Bit configuration:

```ini
[INPUT]
    Name tail
    Path /var/log/sidecar/app.log
    Parser json
    Tag sidecar

[FILTER]
    Name grep
    Match sidecar
    Regex request_id req-.*

[OUTPUT]
    Name es
    Match sidecar
    Host elasticsearch
    Port 9200
    Index sidecar-logs
```

## Health Checks

The sidecar exposes health endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET /sidecar/health` | Liveness probe |
| `GET /sidecar/ready` | Readiness probe |
| `GET /sidecar/metrics` | Prometheus metrics |

### Kubernetes Health Probes (Post-POC)

```yaml
livenessProbe:
  httpGet:
    path: /sidecar/health
    port: 15002
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /sidecar/ready
    port: 15002
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Monitoring

### Prometheus Metrics

The sidecar exposes Prometheus metrics at `/sidecar/metrics`:

```
# Request count by method, route, status
sidecar_requests_total{method="GET",route="user-service",status="200"} 1024

# Request duration histogram
sidecar_request_duration_seconds_bucket{le="0.1"} 500

# Circuit breaker state
sidecar_circuit_breaker_state{cluster="users"} 0

# Rate limit hits
sidecar_rate_limit_hits_total{client="default"} 15
```

### Grafana Dashboard

Key metrics to visualize:
- Request rate (requests per second)
- Error rate (percentage of 5xx responses)
- Latency percentiles (p50, p95, p99)
- Circuit breaker state changes
- Rate limit hits

## Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 100m | 250m |
| Memory | 128Mi | 256Mi |
| Disk | 50Mi | 100Mi |

## Troubleshooting

### Enable Debug Logging

```bash
export SIDECAR_LOG_LEVEL=debug
python -m sidecar --config ./config.yaml
```

### Check Request ID Propagation

```bash
# Send request with custom ID
curl -v -H "X-Request-ID: test-123" http://localhost:15000/api/users

# Verify response header includes same ID
# < X-Request-ID: test-123
```

### View Logs by Request ID

```bash
# If using JSON logging
cat /var/log/sidecar/app.log | jq 'select(.request_id == "req-a1b2c3d4e5f6")'
```

### Common Issues

| Issue | Solution |
|-------|----------|
| No request ID in logs | Ensure request context middleware is enabled |
| Request ID not propagating | Check `X-Request-ID` header name matches between services |
| High memory usage | Reduce log level or enable log rotation |
| Slow requests | Check circuit breaker state and backend health |

## Security Considerations

- No mTLS in POC (plain HTTP only)
- No authentication/authorization in POC
- Run as non-root user in production
- Use read-only filesystem where possible
- Mount configuration as read-only volume

## POC Limitations

- No Kubernetes integration (standalone/container only)
- No TLS/mTLS
- No distributed tracing (OpenTelemetry deferred)
- No dynamic configuration reload
- Single instance only (no clustering)
