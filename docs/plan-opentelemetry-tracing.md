# Proposal 1 — OpenTelemetry Distributed Tracing

## Overview

Replace the stub in `sidecar/telemetry/tracing.py` with a full OpenTelemetry (OTel)
implementation that instruments every stage of the request pipeline with spans, propagates
trace context across service boundaries via HTTP headers, and exports completed traces to a
configurable backend (Jaeger, Grafana Tempo, or stdout).

---

## What problem does this solve?

The sidecar currently has structured **logs** (what happened inside one proxy instance) and
**metrics** (Prometheus counters/histograms). But in a real service mesh, one user request
passes through many sidecars. If that request is slow or fails, you have no way to:

- see the full path it took across all services
- know which specific hop (routing? circuit breaker? downstream call?) was slow
- correlate logs from Service A's sidecar with logs from Service B's sidecar

**Distributed tracing** solves this by producing a single **trace** — a timeline of the
entire request journey — composed of **spans** (one per operation). In a trace viewer like
Jaeger you would see:

```
[Total: 245ms]
  └─ inbound-proxy            0ms → 245ms
       ├─ router.match         1ms →   2ms   route=backend-service
       ├─ rate_limit.check     2ms →   3ms   allowed=true
       ├─ circuit_breaker      3ms →   4ms   state=CLOSED
       ├─ load_balancer        4ms →   5ms   endpoint=10.0.0.3:8080
       └─ http.outbound        5ms → 240ms   status=200
```

---

## Core Concepts

### Trace and Span

- **Trace** — the complete journey of one request. Identified by a `trace_id` (128-bit hex,
  e.g. `4bf92f3577b34da6a3ce929d0e0e4736`). A trace is just a collection of spans that all
  share the same `trace_id`.
- **Span** — one named, timed operation within a trace. Each span carries:
  - `span_id` — unique ID for this span
  - `parent_span_id` — which span created this one (spans form a tree)
  - `name` — e.g. `"circuit_breaker.allow_request"`
  - `start_time` / `end_time`
  - `attributes` — key/value metadata (`http.method=GET`, `cb.state=CLOSED`)
  - `events` — timestamped notes mid-span (`"rate limit token consumed"`)
  - `status` — `OK` or `ERROR`

### Context Propagation

When the sidecar receives a request, the upstream caller may have already started a trace.
To continue that trace (rather than start a new one), the caller encodes `trace_id` +
`parent_span_id` into HTTP headers. The sidecar reads these headers on inbound, creates a
child span, does its work, then writes updated headers when forwarding to the backend.

**W3C TraceContext** (modern standard):
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^^  ── trace_id (32 hex chars) ──     ─ span_id ─      flags
tracestate:  vendor=key:value
```

**B3** (older, used by Zipkin / some Jaeger setups):
```
X-B3-TraceId: 4bf92f3577b34da6a3ce929d0e0e4736
X-B3-SpanId:  00f067aa0ba902b7
X-B3-Sampled: 1
```

The sidecar must support both formats.

### OpenTelemetry SDK Components

```
Your code
  tracer.start_as_current_span("router.match")
        │
        ▼
  TracerProvider      (global singleton, set up once at startup)
  ├── Sampler         (should this span be recorded?)
  └── SpanProcessor   (batch + forward completed spans)
              │
              ▼
        Exporter      (where to send spans)
        ├── OTLPSpanExporter  → Jaeger / Grafana Tempo (production)
        ├── ConsoleSpanExporter → stdout (dev/debug)
        └── InMemorySpanExporter → tests
```

- **TracerProvider** — configured once at startup in `tracing.py`; factory for `Tracer` objects.
- **Tracer** — one per component (`get_tracer("circuit_breaker")`); used to open spans.
- **Sampler** — controls what fraction of traces to record:
  - `ALWAYS_ON` — every request (dev / low traffic)
  - `TraceIdRatioBased(0.1)` — 10% of requests (production)
  - `ParentBased(root_sampler)` — follow the upstream caller's decision (most common in a mesh)
- **Exporter** — ships span data. OTLP (OpenTelemetry Protocol over gRPC) is the default since
  all modern backends support it.

### Fit with Existing `contextvars`

The codebase already uses `contextvars` to carry `request_id` through async coroutines
(`sidecar/telemetry/context.py`). OTel uses the same mechanism internally:
`tracer.start_as_current_span()` stores the active span in a `ContextVar`. This means:

- No manual span passing between functions — it flows automatically.
- `REQUEST_ID_CTX` and OTel's internal context vars coexist without collision.
- `asyncio.create_task()` copies context automatically (Python 3.7+), so traces survive
  across task boundaries.

### Minimal Change per Component

Each pipeline file needs only a few lines. Example for `circuit_breaker.py`:

```python
# BEFORE
async def record_failure(self):
    self.failure_count += 1
    if self.failure_count >= self.failure_threshold:
        logger.warning("Circuit breaker OPENED")
        self.state = State.OPEN

# AFTER
from opentelemetry import trace
from opentelemetry.trace import StatusCode

async def record_failure(self):
    span = trace.get_current_span()
    span.add_event("failure_recorded", {"count": self.failure_count + 1})
    self.failure_count += 1
    if self.failure_count >= self.failure_threshold:
        logger.warning("Circuit breaker OPENED")   # existing log stays
        self.state = State.OPEN
        span.set_attribute("cb.state_transition", "CLOSED→OPEN")
        span.set_status(StatusCode.ERROR, "Circuit breaker opened")
```

Logs and spans are complementary — both are kept.

---

## Implementation Steps

1. **Install packages** — add to `pyproject.toml` / `requirements.txt`:
   ```
   opentelemetry-api>=1.20
   opentelemetry-sdk>=1.20
   opentelemetry-exporter-otlp-proto-grpc>=1.20
   opentelemetry-propagator-b3>=1.20
   ```

2. **Implement `sidecar/telemetry/tracing.py`** — replace the 4-line stub:
   - `configure_tracing(config: TracingConfig)` — sets up `TracerProvider`, exporter,
     sampler, and registers both W3C and B3 propagators globally.
   - `get_tracer(component: str) -> Tracer` — thin wrapper around `trace.get_tracer()`.
   - `shutdown_tracing()` — flushes the exporter on process exit (prevents span loss).

3. **Update `sidecar/config/settings.py`** — add `TracingConfig` Pydantic model:
   ```python
   class TracingConfig(BaseModel):
       enabled: bool = False
       service_name: str = "sidecar-proxy"
       exporter: Literal["otlp", "console", "none"] = "none"
       otlp_endpoint: str = "localhost:4317"
       sampler: Literal["always_on", "always_off", "ratio", "parent_based"] = "parent_based"
       sample_ratio: float = 1.0
   ```

4. **Update `sidecar/listeners/middleware.py`** — in `request_context_middleware`:
   - Before creating `RequestContext`: extract `traceparent` / B3 headers using OTel's
     `propagate.extract(request.headers)` to get a parent span context.
   - Start a root span for the request using `tracer.start_as_current_span()` with the
     extracted parent context.
   - On response: inject current span context into outbound headers with
     `propagate.inject(response.headers)`.
   - Close span in the `finally` block so it records even on exception.

5. **Update `sidecar/pipeline/router.py`** — after route match, call
   `span.set_attribute("route.name", route.name)` and
   `span.set_attribute("route.cluster", route.cluster)`.

6. **Update `sidecar/pipeline/load_balancer.py`** — after endpoint selection, call
   `span.set_attribute("lb.endpoint", f"{endpoint.host}:{endpoint.port}")` and
   `span.set_attribute("lb.algorithm", self.__class__.__name__)`.

7. **Update `sidecar/pipeline/circuit_breaker.py`** — in `allow_request()`, add
   `span.set_attribute("cb.state", self.state.value)`. In `record_failure()`, add event
   and set ERROR status when opening. In `record_success()`, add event on HALF_OPEN→CLOSED.

8. **Update `sidecar/pipeline/rate_limit.py`** — in `check()`, add
   `span.set_attribute("rate_limit.allowed", allowed)` and an event when throttled.

9. **Update `sidecar/connection/http_client.py`** — inject `traceparent` into outbound
   request headers using `propagate.inject(headers)` before forwarding.

10. **Update `sidecar/main.py`** — call `configure_tracing(config.tracing)` at startup
    and `shutdown_tracing()` in the shutdown handler.

11. **Write `tests/unit/test_tracing.py`** — test TracerProvider setup, exporter
    selection, sampler behavior, `get_tracer()` returns non-null tracer.

12. **Write `tests/integration/test_tracing_pipeline.py`** — use `InMemorySpanExporter`;
    send a request through the pipeline; assert:
    - A root span named `"inbound.request"` was produced.
    - Child spans for `router.match`, `circuit_breaker.allow`, `load_balancer.select` exist.
    - Child spans share the root span's `trace_id`.
    - `cb.state` attribute is present on the circuit breaker span.

---

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_tracing.py` | Unit tests for tracing setup |
| `tests/integration/test_tracing_pipeline.py` | Integration tests for span propagation |

## Files to Modify

| File | Change |
|------|--------|
| `sidecar/telemetry/tracing.py` | Full implementation replacing the stub |
| `sidecar/config/settings.py` | Add `TracingConfig` model |
| `sidecar/listeners/middleware.py` | Header extraction/injection, root span lifecycle |
| `sidecar/pipeline/router.py` | Route name/cluster span attributes |
| `sidecar/pipeline/load_balancer.py` | Endpoint + algorithm span attributes |
| `sidecar/pipeline/circuit_breaker.py` | State transition span events and status |
| `sidecar/pipeline/rate_limit.py` | Rate limit verdict span attribute |
| `sidecar/connection/http_client.py` | Inject `traceparent` into outbound headers |
| `sidecar/main.py` | Call configure/shutdown tracing |
| `pyproject.toml` | Add 4 OTel packages |
| `examples/basic-config.yaml` | Add `tracing:` section |

---

## Configuration

Add to `examples/basic-config.yaml`:

```yaml
tracing:
  enabled: true
  service_name: sidecar-proxy
  exporter: otlp              # otlp | console | none
  otlp_endpoint: localhost:4317
  sampler: parent_based       # always_on | always_off | ratio | parent_based
  sample_ratio: 1.0           # only used when sampler=ratio
```

---

## Complexity Hotspots

| Area | Why it's tricky |
|------|----------------|
| Header extraction | Must handle W3C + B3 simultaneously; malformed headers must not crash |
| Span lifecycle in aiohttp | Must close the root span in `finally` even when the handler raises |
| Exporter shutdown | `TracerProvider.force_flush()` must be called on process exit or the last spans batch is lost |
| `ParentBased` sampler | Must propagate the upstream sampling decision — if upstream says "don't sample", the sidecar must not record either |
| Testing | `InMemorySpanExporter` setup; asserting parent/child relationships by `trace_id` + `parent_span_id` |

---

## Verification

1. Start a local Jaeger instance:
   ```
   docker run -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
   ```
2. Start the sidecar with `tracing.enabled: true` and `otlp_endpoint: localhost:4317`.
3. Send a request: `curl http://localhost:15000/some/path`
4. Open `http://localhost:16686`, search for service `sidecar-proxy`.
5. Confirm:
   - A trace appears with child spans per pipeline stage.
   - `cb.state`, `route.name`, `lb.endpoint` attributes are set correctly.
   - `traceparent` header is present in the forwarded request to the backend.
6. Run integration tests: `pytest tests/integration/test_tracing_pipeline.py -v`
