# Proposal 3 — Dynamic xDS-based Configuration with Hot-Reload

## Overview

Add a gRPC xDS control plane client so the sidecar can receive live route, cluster, and
endpoint updates from an Envoy-compatible control plane without restarting. This replaces
the static YAML-only loader in `sidecar/config/loader.py` with a layered system: xDS
(live) → local YAML (fallback) → hardcoded defaults. All pipeline components switch from
reading a static config object to reading from a versioned, atomically-updated
`ConfigSnapshot`.

---

## What problem does this solve?

Right now the sidecar reads its config once at startup from a YAML file. In production:

- Adding a new route means restarting every sidecar instance — causing brief downtime.
- Changing a rate limit or circuit breaker threshold requires a full redeploy.
- Canary deployments (gradually shifting traffic between two backends) require external
  scripts to regenerate YAML files and restart instances.

**Dynamic configuration** solves this. A central **control plane** holds the desired state
of all sidecars. Each sidecar subscribes to a stream and receives updates within seconds —
no restart, no downtime. This is how Envoy Proxy (used in Istio, AWS App Mesh) works. The
protocol it uses is called **xDS**.

---

## Core Concepts

### What is xDS?

xDS ("X Discovery Service") is a family of gRPC APIs originally designed by the Envoy
Proxy project, now a CNCF standard. "xDS" is an umbrella term for four related APIs:

| API | Name | What it configures |
|-----|------|--------------------|
| LDS | Listener Discovery Service | Which ports to listen on and how |
| RDS | Route Discovery Service | URL → cluster routing rules |
| CDS | Cluster Discovery Service | Cluster names and load balancing policy |
| EDS | Endpoint Discovery Service | IP:port list for a cluster |

For this sidecar the most relevant are **RDS** (routes), **CDS** (clusters), and **EDS**
(endpoints), mapping directly to the existing `RouteConfig`, cluster names, and endpoint
lists.

### State-of-the-World vs Delta xDS

There are two streaming protocols:

- **State-of-the-World (SotW)** — the server sends the *full* current config every time
  anything changes. Simple to implement but expensive for large configs.
- **Delta xDS** — the server sends only *what changed* (added/removed resources). More
  complex but efficient for large meshes.

For this implementation we start with SotW and note where Delta would be plugged in.

### gRPC Streaming

xDS uses gRPC **bidirectional streaming**. The sidecar opens a long-lived stream to the
control plane:

```
Sidecar                              Control Plane
  │── DiscoveryRequest ────────────────────►│
  │   (subscribe to RDS resources)          │
  │◄─────────────────── DiscoveryResponse ──│
  │   (full list of routes)                 │
  │── ACK (version nonce) ─────────────────►│
  │   (I applied this config)               │
  │◄─────────────────── DiscoveryResponse ──│
  │   (updated routes after a change)       │
  │── ACK ──────────────────────────────────►│
```

If the sidecar receives a bad config it sends a **NACK** (negative acknowledgement) and
keeps the previous config. If the stream drops, the sidecar reconnects with exponential
backoff.

### ConfigSnapshot — Atomic Live Reload

All pipeline components (router, load balancer, rate limiter) currently hold a reference
to static config. To support live updates, they instead hold a reference to a shared
`ConfigSnapshot` object. Updates are applied with an `asyncio.Lock`:

```
xDS client receives new routes
        │
        ▼
ConfigSnapshot.apply_update(new_routes)
   ├── validate with Pydantic
   ├── async with self._lock:
   │       self._routes = new_routes
   │       self._version += 1
   │       notify observers
   └── log "Config updated to version N"

Router.match(request)
   └── reads self._snapshot.routes  ← always sees latest, no restart needed
```

The lock ensures no request reads a half-updated snapshot. Observers (pipeline components
that need to react, like resetting circuit breakers on cluster changes) are notified after
the lock is released.

### Fallback Chain

```
                  ┌─────────────────────┐
                  │  xDS control plane   │  (primary, live)
                  └────────┬────────────┘
                           │ unreachable?
                  ┌────────▼────────────┐
                  │  local YAML file     │  (fallback, static)
                  └────────┬────────────┘
                           │ missing?
                  ┌────────▼────────────┐
                  │  hardcoded defaults  │  (last resort)
                  └─────────────────────┘
```

---

## Implementation Steps

1. **Install packages**:
   ```
   grpcio>=1.59
   grpcio-tools>=1.59
   protobuf>=4.24
   ```
   (The xDS v3 proto files are available from the `envoyproxy/data-plane-api` repo or
   via the `xds` Python package.)

2. **Create `sidecar/config/snapshot.py`**:
   - `ConfigSnapshot` dataclass: holds versioned routes, clusters, endpoints.
   - `apply_routes(routes: list[RouteConfig])` — acquires lock, validates, replaces.
   - `apply_endpoints(cluster: str, endpoints: list[Endpoint])` — same pattern.
   - `subscribe(observer: Callable)` — register a callback for change notifications.
   - `get_version() -> int` — current version number (used in ACK/NACK).

3. **Create `sidecar/config/xds_client.py`**:
   - `XdsClient(server_address, node_id, snapshot: ConfigSnapshot)` class.
   - `connect()` — opens gRPC channel, subscribes to RDS + CDS + EDS streams.
   - Per-stream loop:
     - Send `DiscoveryRequest` with the current version nonce.
     - On `DiscoveryResponse`: parse resources, call `snapshot.apply_*()`.
     - On success: send ACK. On `ValidationError`: send NACK, log warning, keep old config.
   - Reconnect with exponential backoff on stream error (`tenacity` already in the project).
   - Update `xds_connected` Prometheus gauge on connect/disconnect.

4. **Update `sidecar/config/loader.py`** — add `XdsConfigLoader`:
   - Tries to connect to xDS on startup.
   - If connection fails within a timeout, falls back to `YamlConfigLoader`.
   - Returns a shared `ConfigSnapshot` in both cases.

5. **Update `sidecar/config/settings.py`** — add `XdsConfig`:
   ```python
   class XdsConfig(BaseModel):
       enabled: bool = False
       server_address: str = "localhost:18000"
       node_id: str = "sidecar-node-1"
       connect_timeout: int = 5        # seconds before falling back to YAML
       reconnect_backoff_max: int = 30 # seconds
   ```

6. **Update `sidecar/pipeline/router.py`** — accept `ConfigSnapshot` instead of static
   `list[RouteConfig]`:
   ```python
   # Before
   def __init__(self, routes: list[RouteConfig]):
       self._routes = routes

   # After
   def __init__(self, snapshot: ConfigSnapshot):
       self._snapshot = snapshot

   def match(self, request) -> Route | None:
       for route in self._snapshot.routes:   # always reads current version
           ...
   ```

7. **Update `sidecar/pipeline/load_balancer.py`** — same pattern; read endpoints from
   `snapshot.get_endpoints(cluster)`.

8. **Update `sidecar/pipeline/rate_limit.py`** — read rate limit config from snapshot.

9. **Update `sidecar/listeners/inbound.py`** — expose `GET /config` admin endpoint:
   ```json
   {
     "version": 7,
     "xds_connected": true,
     "xds_server": "localhost:18000",
     "routes": 3,
     "clusters": 2
   }
   ```

10. **Update `sidecar/telemetry/metrics.py`** — add:
    ```python
    config_reload_total = Counter("sidecar_config_reload_total", "Number of config updates applied")
    xds_connected = Gauge("sidecar_xds_connected", "1 if connected to xDS server, 0 otherwise")
    ```

11. **Write `tests/unit/test_snapshot.py`**:
    - `apply_routes` updates the snapshot atomically.
    - Concurrent readers see a consistent snapshot (no torn read).
    - Observer callbacks are called after an update.
    - Invalid config (fails Pydantic validation) is rejected; old config remains.

12. **Write `tests/integration/test_xds_hot_reload.py`**:
    - Start a minimal in-process gRPC server that implements `AggregatedDiscoveryService`.
    - Start the sidecar pointing at it.
    - Send requests; confirm they route to cluster A.
    - Push an updated route config from the test server; wait one event loop tick.
    - Send requests again; confirm they now route to cluster B.
    - Disconnect the xDS server; confirm the sidecar continues with the last known config.

---

## Files to Create

| File | Purpose |
|------|---------|
| `sidecar/config/snapshot.py` | Versioned, observable config snapshot |
| `sidecar/config/xds_client.py` | gRPC xDS streaming client |
| `tests/unit/test_snapshot.py` | Unit tests for snapshot atomicity and observer |
| `tests/integration/test_xds_hot_reload.py` | Integration tests for live config updates |

## Files to Modify

| File | Change |
|------|--------|
| `sidecar/config/loader.py` | Add `XdsConfigLoader`; fallback chain logic |
| `sidecar/config/settings.py` | Add `XdsConfig` model |
| `sidecar/pipeline/router.py` | Accept `ConfigSnapshot` instead of static route list |
| `sidecar/pipeline/load_balancer.py` | Read endpoints from snapshot |
| `sidecar/pipeline/rate_limit.py` | Read rate limit config from snapshot |
| `sidecar/listeners/inbound.py` | Add `GET /config` admin endpoint |
| `sidecar/telemetry/metrics.py` | Add `config_reload_total` counter + `xds_connected` gauge |
| `sidecar/main.py` | Start `XdsClient` background task if enabled |
| `pyproject.toml` | Add `grpcio`, `grpcio-tools`, `protobuf` |
| `examples/basic-config.yaml` | Add `xds:` section |

---

## New Dependencies

```
grpcio>=1.59
grpcio-tools>=1.59
protobuf>=4.24
```

---

## Configuration

Add to `examples/basic-config.yaml`:

```yaml
xds:
  enabled: true
  server_address: localhost:18000    # address of the xDS control plane
  node_id: sidecar-node-1            # identifies this sidecar to the control plane
  connect_timeout: 5                 # seconds before falling back to YAML
  reconnect_backoff_max: 30          # max seconds between reconnect attempts
```

---

## Complexity Hotspots

| Area | Why it's tricky |
|------|----------------|
| gRPC streaming lifecycle | The stream must be kept alive indefinitely; reconnect logic must not block the event loop |
| ACK/NACK protocol | The version nonce in ACK must exactly match the response nonce, or the control plane will resend the same update in a loop |
| Atomic snapshot update | Multiple pipeline components read the snapshot concurrently; `asyncio.Lock` prevents torn reads but adds latency if held too long |
| Pydantic validation on live update | xDS resources use protobuf types; converting proto → Pydantic models without data loss requires careful mapping |
| In-process test server | Implementing a minimal gRPC ADS server for tests requires setting up `grpcio` servicer; state must be injectable from the test |
| Fallback timing | The `connect_timeout` must be short enough to not delay startup but long enough to survive a transient network blip |

---

## Verification

1. Start a minimal xDS control plane (e.g. `go-control-plane` example server, or the
   in-process test server):
   ```bash
   # example with go-control-plane
   docker run -p 18000:18000 envoyproxy/go-control-plane-example
   ```
2. Configure the sidecar with `xds.enabled: true` pointing at port `18000`.
3. Start the sidecar; confirm `GET http://localhost:15002/config` returns `"xds_connected": true`.
4. Send a request: `curl http://localhost:15000/some/path` — confirm routing matches the
   xDS-provided route.
5. Push a route change from the control plane (new cluster mapping).
6. Send the same request again — confirm the new route is used **without restarting the sidecar**.
7. Stop the control plane; confirm the sidecar continues serving with the last known config.
8. Run tests: `pytest tests/integration/test_xds_hot_reload.py -v`
