# Request ID Propagation - Execution Plan

## Overview

This document outlines the phased implementation plan for adding request ID propagation with structured logging and tracing to the service mesh sidecar proxy. The implementation follows **Test-Driven Development (TDD)** principles.

---

## TDD Workflow

For every phase and task:
1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Implement minimal code to make the test pass
3. **Refactor**: Clean up code while keeping tests green
4. **Validate**: Verify against acceptance criteria

---

## Phase 1: Foundation - Request Context Infrastructure

**Goal**: Establish the core infrastructure for request context propagation using `contextvars`.

### Tasks

#### Task 1.1: Create Request Context Module
- **Test First**: `tests/unit/test_request_context.py`
  - Test `RequestContext.create()` generates unique IDs
  - Test `RequestContext.create()` accepts existing ID
  - Test context vars are set correctly
  - Test context retrieval across async boundaries
  
- **Implementation**: `sidecar/telemetry/context.py`
  - Create `RequestContext` dataclass
  - Define `REQUEST_ID_CTX` and `START_TIME_CTX` context variables
  - Implement `create()`, `set_current()` methods

#### Task 1.2: Context Propagation Tests
- **Test First**: `tests/unit/test_context_propagation.py`
  - Test context persists through single async function
  - Test context persists through multiple async calls
  - Test concurrent requests have isolated contexts
  - Test context cleanup after request completion

### Acceptance Criteria

- [ ] `RequestContext.create()` generates unique request IDs in format `req-<12-char-hex>`
- [ ] `RequestContext.create(existing_id="custom-id")` uses provided ID
- [ ] Context variables correctly store and retrieve request_id across async/await boundaries
- [ ] Concurrent async requests maintain isolated contexts (no cross-contamination)
- [ ] All unit tests pass with >90% code coverage
- [ ] Code passes linting (ruff) and type checking (mypy)

---

## Phase 2: Structured Logging with Request Context

**Goal**: Implement structured logging using structlog with automatic request ID binding.

### Tasks

#### Task 2.1: Logging Configuration Tests
- **Test First**: `tests/unit/test_logging_config.py`
  - Test `configure_logging()` sets up structlog correctly
  - Test JSON formatter produces valid JSON output
  - Test console formatter produces readable output
  - Test log level filtering works

#### Task 2.2: Context-Aware Logger Tests
- **Test First**: `tests/unit/test_context_logger.py`
  - Test `get_logger()` returns BoundLogger
  - Test logger includes request_id when in context
  - Test logger works without context (background tasks)
  - Test component name is bound correctly
  - Test log output contains all expected fields

#### Task 2.3: Log Output Format Tests
- **Test First**: `tests/unit/test_log_output.py`
  - Test JSON output contains: timestamp, level, event, request_id, component
  - Test log messages can include extra fields
  - Test exception info is properly serialized

### Implementation

- `sidecar/telemetry/logging.py` - Replace placeholder
  - `configure_logging()` function
  - `get_logger(component)` function with context binding
  - Structlog processors for request context

### Acceptance Criteria

- [ ] `configure_logging()` initializes structlog with JSON and console formatters
- [ ] `get_logger("component")` returns a BoundLogger with component name bound
- [ ] When inside a request context, all log entries automatically include `request_id` field
- [ ] When outside request context, logger works without request_id (no errors)
- [ ] JSON log output is valid JSON with fields: `timestamp`, `level`, `event`, `component`, `request_id` (when available)
- [ ] Log levels (debug, info, warning, error) filter correctly
- [ ] All unit tests pass with >90% code coverage

---

## Phase 3: Inbound Request ID Middleware

**Goal**: Create middleware to extract/generate request IDs at the entry point.

### Tasks

#### Task 3.1: Middleware Tests
- **Test First**: `tests/integration/test_request_id_middleware.py`
  - Test middleware extracts `X-Request-ID` from incoming headers
  - Test middleware generates new ID when header is missing
  - Test middleware sets up request context before handler
  - Test middleware adds `X-Request-ID` to response headers
  - Test middleware logs request start and completion

#### Task 3.2: Request Lifecycle Tests
- **Test First**: `tests/integration/test_request_lifecycle.py`
  - Test context is available throughout request lifecycle
  - Test context is cleaned up after request (no leakage)
  - Test concurrent requests maintain separate contexts

### Implementation

- `sidecar/listeners/middleware.py` - New file
  - `request_context_middleware` - aiohttp middleware
  - Request ID extraction/generation logic
  - Request start/completion logging
  - Response header injection

- Update `sidecar/listeners/inbound.py`
  - Register middleware with aiohttp app

### Acceptance Criteria

- [ ] Middleware extracts `X-Request-ID` header from incoming requests when present
- [ ] Middleware generates new unique request ID when header is absent
- [ ] Request context is established before request handler executes
- [ ] Response includes `X-Request-ID` header with the same ID
- [ ] Request start is logged with: method, path, remote, user_agent, request_id
- [ ] Request completion is logged with: status, duration_ms, request_id
- [ ] Failed requests are logged with error details and request_id
- [ ] Concurrent requests maintain isolated contexts (test with 100 concurrent requests)
- [ ] All integration tests pass

---

## Phase 4: Pipeline Component Logging

**Goal**: Add structured logging to all pipeline components with request context.

### Tasks

#### Task 4.1: Router Logging Tests
- **Test First**: `tests/unit/test_router_logging.py`
  - Test router logs route matching decisions
  - Test router logs when no route matches
  - Test logs include request_id from context

#### Task 4.2: Load Balancer Logging Tests
- **Test First**: `tests/unit/test_load_balancer_logging.py`
  - Test load balancer logs endpoint selection
  - Test logs include algorithm name
  - Test logs include selected endpoint

#### Task 4.3: Circuit Breaker Logging Tests
- **Test First**: `tests/unit/test_circuit_breaker_logging.py`
  - Test CB logs state transitions
  - Test CB logs request allow/deny decisions
  - Test logs include cluster name and state

#### Task 4.4: Rate Limiter Logging Tests
- **Test First**: `tests/unit/test_rate_limiter_logging.py`
  - Test rate limiter logs allow/deny decisions
  - Test logs include client key and rate limit info

### Implementation

Update each pipeline component to use structured logging:

- `sidecar/pipeline/router.py` - Add router logging
- `sidecar/pipeline/load_balancer.py` - Add load balancer logging
- `sidecar/pipeline/circuit_breaker.py` - Add circuit breaker logging
- `sidecar/pipeline/rate_limit.py` - Add rate limiter logging
- `sidecar/pipeline/retry.py` - Add retry logging

### Acceptance Criteria

- [ ] Router logs route matching with: route_name, cluster, path, request_id
- [ ] Router logs 404 when no route matches with: path, request_id
- [ ] Load balancer logs endpoint selection with: algorithm, endpoint, request_id
- [ ] Circuit breaker logs state checks with: cluster, state, allowed, request_id
- [ ] Circuit breaker logs state transitions with: cluster, old_state, new_state
- [ ] Rate limiter logs decisions with: client_key, allowed, limit, request_id
- [ ] Retry handler logs attempts with: attempt_number, max_attempts, request_id
- [ ] All logs include request_id when called within request context
- [ ] All unit tests pass

---

## Phase 5: Outbound Request ID Propagation

**Goal**: Forward request ID to downstream services via HTTP headers.

### Tasks

#### Task 5.1: Outbound Header Injection Tests
- **Test First**: `tests/unit/test_outbound_headers.py`
  - Test outbound client injects `X-Request-ID` header
  - Test header value matches current context request_id
  - Test works without context (no header added, no error)

#### Task 5.2: End-to-End Propagation Tests
- **Test First**: `tests/integration/test_e2e_propagation.py`
  - Test request ID from inbound flows to outbound
  - Test downstream service receives correct header
  - Test response chain maintains request ID

### Implementation

- `sidecar/listeners/outbound.py` - Modify `OutboundClient`
  - Extract request_id from context
  - Inject `X-Request-ID` header in outgoing requests

### Acceptance Criteria

- [ ] Outbound HTTP requests include `X-Request-ID` header when in request context
- [ ] Header value matches the request_id from inbound request
- [ ] Outbound client works correctly when no context exists (no header added)
- [ ] Request ID propagates end-to-end: Client → Inbound → Outbound → Backend
- [ ] All integration tests pass

---

## Phase 6: Metrics Integration (Optional Enhancement)

**Goal**: Tag metrics with request ID for advanced correlation (optional).

### Tasks

#### Task 6.1: Metrics Tagging Tests
- **Test First**: `tests/unit/test_metrics_tags.py`
  - Test metrics can include request_id tag
  - Test metrics collection respects cardinality limits

### Implementation

- `sidecar/telemetry/metrics.py` - Optional enhancement
  - Add request_id tagging (with cardinality limits)

### Acceptance Criteria

- [ ] Metrics can be tagged with request_id (optional, off by default)
- [ ] Cardinality limits prevent metric explosion
- [ ] All tests pass

---

## Phase 7: Integration & E2E Testing

**Goal**: Validate the complete request flow with logging and tracing.

### Tasks

#### Task 7.1: Full Flow Integration Tests
- **Test First**: `tests/integration/test_full_flow.py`
  - Test complete request lifecycle with all components
  - Test logs capture flow through all pipeline stages
  - Test request ID consistency across all logs

#### Task 7.2: E2E Tests
- **Test First**: `tests/e2e/test_request_id_e2e.py`
  - Test with real HTTP requests
  - Test request ID propagation to mock backend
  - Test log output format and content

### Acceptance Criteria

- [ ] Complete request flow logs at all pipeline stages with consistent request_id
- [ ] Log sequence shows: inbound → router → load_balancer → circuit_breaker → outbound
- [ ] Each log entry contains appropriate component-specific fields
- [ ] Request ID in response header matches request ID in all logs
- [ ] E2E test validates request ID received by downstream service
- [ ] All integration and E2E tests pass

---

## Phase 8: Documentation & Configuration

**Goal**: Document the feature and add configuration options.

### Tasks

#### Task 8.1: Configuration Schema Update
- Add to `sidecar/config/settings.py`:
  - `request_id_header`: str (default: "X-Request-ID")
  - `logging.request_id_enabled`: bool (default: true)
  - `logging.format`: str (default: "json")

#### Task 8.2: Documentation
- Update `docs/configuration.md` with new logging options
- Update `docs/architecture.md` with request flow diagram
- Add `docs/logging-tracing.md` with usage examples

### Acceptance Criteria

- [ ] Configuration schema accepts `request_id_header` option
- [ ] Configuration schema accepts `logging.format` option (json/plain)
- [ ] Documentation explains how request ID propagation works
- [ ] Documentation includes example log outputs
- [ ] Documentation explains how to query logs by request_id
- [ ] All configuration tests pass

---

## Test File Structure

```
tests/
├── unit/
│   ├── test_request_context.py          # Phase 1
│   ├── test_context_propagation.py      # Phase 1
│   ├── test_logging_config.py           # Phase 2
│   ├── test_context_logger.py           # Phase 2
│   ├── test_log_output.py               # Phase 2
│   ├── test_router_logging.py           # Phase 4
│   ├── test_load_balancer_logging.py    # Phase 4
│   ├── test_circuit_breaker_logging.py  # Phase 4
│   ├── test_rate_limiter_logging.py     # Phase 4
│   ├── test_outbound_headers.py         # Phase 5
│   └── test_metrics_tags.py             # Phase 6 (optional)
├── integration/
│   ├── test_request_id_middleware.py    # Phase 3
│   ├── test_request_lifecycle.py        # Phase 3
│   ├── test_e2e_propagation.py          # Phase 5
│   └── test_full_flow.py                # Phase 7
└── e2e/
    └── test_request_id_e2e.py           # Phase 7
```

---

## Implementation File Structure

```
sidecar/
├── telemetry/
│   ├── __init__.py
│   ├── context.py        # NEW: RequestContext, contextvars
│   ├── logging.py        # UPDATE: Structured logging with context
│   ├── metrics.py        # EXISTING (minor updates)
│   └── tracing.py        # EXISTING (placeholder for future)
├── listeners/
│   ├── __init__.py
│   ├── inbound.py        # UPDATE: Add middleware
│   ├── outbound.py       # UPDATE: Header injection
│   └── middleware.py     # NEW: Request context middleware
└── pipeline/
    ├── router.py         # UPDATE: Add logging
    ├── load_balancer.py  # UPDATE: Add logging
    ├── circuit_breaker.py # UPDATE: Add logging
    ├── rate_limit.py     # UPDATE: Add logging
    └── retry.py          # UPDATE: Add logging
```

---

## Definition of Done

The feature is complete when:

1. **All Phases Complete**: All 8 phases implemented and tested
2. **Test Coverage**: >90% code coverage for new code
3. **TDD Compliance**: All tests written before implementation
4. **CI/CD**: All tests pass in CI pipeline
5. **Documentation**: Complete documentation in `docs/` folder
6. **Code Quality**: Passes ruff linting and mypy type checking
7. **Acceptance Criteria**: All acceptance criteria in each phase are met
8. **E2E Validation**: End-to-end tests demonstrate working request ID propagation

---

## Success Metrics

- Request ID is present in 100% of request logs
- Request ID propagates correctly to downstream services
- Log correlation by request_id is possible across all components
- No measurable performance degradation (< 1ms overhead per request)
- Zero context leaks between concurrent requests

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Context leaks between requests | Extensive concurrent request testing in Phase 1 & 3 |
| Performance overhead | Benchmark tests in Phase 7 |
| Breaking existing logging | Maintain backward compatibility, gradual rollout |
| Memory leaks | Context cleanup validation in all tests |
| Header conflicts | Configurable header name in Phase 8 |
