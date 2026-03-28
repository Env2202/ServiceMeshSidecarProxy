# Proposal 2 — mTLS with Automatic Certificate Rotation

## Overview

Implement mutual TLS (mTLS) on both the inbound listener (`:15000`) and the outbound
HTTP client, replacing the stubs in `sidecar/security/tls.py` and `sidecar/security/auth.py`.
A background watcher continuously polls certificate expiry and hot-swaps the `ssl.SSLContext`
without restarting the event loop. For the POC, certs are file-based; the design is
compatible with SPIFFE/SPIRE for production use.

---

## What problem does this solve?

In a service mesh, sidecar proxies are the security boundary between services. Without mTLS:

- Any process on the network can send traffic to a service pretending to be a trusted peer.
- Traffic between services travels in plaintext — visible to anyone who can sniff the network.
- There is no cryptographic proof of *which* service is making a call.

**mTLS** (mutual TLS) means both sides of a connection present and verify a certificate:

- The sidecar verifies the backend's cert before forwarding traffic.
- The backend verifies the sidecar's cert before accepting the connection.
- All traffic is encrypted in transit.

**Certificate rotation** ensures certs are short-lived (hours, not years). If a cert is
compromised, it expires quickly. The challenge is rotating without dropping in-flight requests.

---

## Core Concepts

### TLS vs mTLS

Regular TLS: only the *server* presents a certificate (like HTTPS on a website). The client
verifies the server but stays anonymous.

mTLS: *both* sides present certificates. The server also verifies the client. This is how
zero-trust service mesh works — every call is authenticated.

### X.509 Certificates

A cert is a signed document that says "this public key belongs to this identity, signed by
authority X". The relevant fields for a sidecar:

- **Subject** — who this cert belongs to (e.g. `CN=sidecar.service-a`)
- **SAN (Subject Alternative Name)** — additional identity URIs. SPIFFE uses
  `URI:spiffe://cluster.local/ns/default/sa/service-a` here.
- **Not Before / Not After** — validity window. Short-lived certs use windows of hours.
- **Issuer** — the CA (Certificate Authority) that signed this cert.

### ssl.SSLContext (Python)

Python's `ssl.SSLContext` is the object you attach to a server or HTTP client to enable
TLS. To enable mTLS:

```python
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(certfile="cert.pem", keyfile="key.pem")  # our identity
ctx.load_verify_locations(cafile="ca.pem")                   # trusted CAs
ctx.verify_mode = ssl.CERT_REQUIRED                          # require client cert
```

For hot rotation, you create a *new* `SSLContext` with the fresh cert and replace it on
the server. Existing connections (already in TLS handshake) continue with the old context;
new connections use the new one.

### SPIFFE (Secure Production Identity Framework for Everyone)

SPIFFE is a standard for workload identity in cloud-native environments. Instead of
hostnames, services are identified by URIs called SVIDs:

```
spiffe://trust-domain/ns/namespace/sa/service-account
```

The SPIFFE Workload API is a gRPC socket that a running workload queries to get its current
X.509 cert + private key. The socket rotates certs automatically.

For the POC we use **file-based certs** (generated with `openssl`) but the code structure
mirrors the Workload API pattern so it can be swapped in later.

### Hot-Swap Without Restart

aiohttp's `AppRunner` / `TCPSite` accepts an `ssl_context` argument at startup. The trick
for rotation is: aiohttp resolves `ssl_context` per-connection, so replacing the object
that a wrapper points to is sufficient — no server restart needed.

```python
class RotatingSSLContext:
    """Wrapper whose inner context can be replaced atomically."""
    def __init__(self): self._ctx: ssl.SSLContext = None
    def update(self, new_ctx): self._ctx = new_ctx   # atomic reference replace
    def __getattr__(self, name): return getattr(self._ctx, name)
```

---

## Implementation Steps

1. **Generate test certs** (for development/testing only):
   ```bash
   # CA
   openssl req -new -x509 -days 1 -keyout ca.key -out ca.pem -subj "/CN=TestCA"
   # Sidecar cert signed by CA
   openssl req -new -keyout sidecar.key -out sidecar.csr -subj "/CN=sidecar"
   openssl x509 -req -in sidecar.csr -CA ca.pem -CAkey ca.key -out sidecar.pem -days 1
   ```

2. **Update `sidecar/config/settings.py`** — add `TLSConfig`:
   ```python
   class TLSConfig(BaseModel):
       enabled: bool = False
       cert_file: str = ""
       key_file: str = ""
       ca_bundle: str = ""
       rotation_check_interval: int = 60   # seconds between expiry checks
       rotation_threshold: int = 300       # rotate when < 5 min remaining
       spiffe_socket: str = ""             # path to SPIFFE workload API socket (optional)
   ```

3. **Implement `sidecar/security/tls.py`**:
   - `build_ssl_context(config: TLSConfig) -> ssl.SSLContext` — loads cert/key/CA,
     sets `verify_mode = CERT_REQUIRED`.
   - `RotatingSSLContext` — thin wrapper with an `update(new_ctx)` method.
   - `CertWatcher` — async background task that:
     - Reads the cert file periodically.
     - Parses `Not After` with `cryptography` library.
     - When remaining validity < `rotation_threshold`, reloads cert files and calls
       `RotatingSSLContext.update()`.
     - Emits a structured log and updates the Prometheus `cert_expiry_seconds` gauge.

4. **Implement `sidecar/security/auth.py`** — SPIFFE SAN validation:
   - After TLS handshake, inspect the peer certificate's SAN extension.
   - Extract `spiffe://...` URI and compare against allowed identities from config.
   - Reject connections whose SPIFFE ID is not in the trust list.

5. **Update `sidecar/listeners/inbound.py`** — pass `RotatingSSLContext` to `TCPSite`:
   ```python
   tls = RotatingSSLContext()
   tls.update(build_ssl_context(config.tls))
   site = web.TCPSite(runner, host, port, ssl_context=tls)
   ```

6. **Update `sidecar/connection/http_client.py`** — inject client cert into outbound
   `httpx.AsyncClient`:
   ```python
   ssl_ctx = build_ssl_context(config.tls)   # same cert, client mode
   client = httpx.AsyncClient(verify=ssl_ctx)
   ```

7. **Update `sidecar/telemetry/metrics.py`** — add gauge:
   ```python
   cert_expiry_seconds = Gauge(
       "sidecar_cert_expiry_seconds",
       "Seconds until the current TLS certificate expires"
   )
   ```

8. **Start `CertWatcher`** in `sidecar/main.py` as an `asyncio` background task.

9. **Write `tests/unit/test_tls.py`**:
   - `build_ssl_context` returns correct `verify_mode`.
   - `RotatingSSLContext.update()` replaces the inner context.
   - `CertWatcher` detects an expired cert and calls `update()`.

10. **Write `tests/integration/test_mtls_handshake.py`**:
    - Start inbound listener with mTLS.
    - Connect with a valid client cert — expect `200`.
    - Connect without cert — expect `ssl.SSLError`.
    - Connect with a cert signed by an unknown CA — expect rejection.
    - Simulate cert rotation mid-test — expect no connection drop.

---

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_tls.py` | Unit tests for SSLContext builder and cert watcher |
| `tests/integration/test_mtls_handshake.py` | Integration tests for mTLS enforcement |
| `certs/` (gitignored) | Local dev certs generated by openssl |

## Files to Modify

| File | Change |
|------|--------|
| `sidecar/security/tls.py` | Full implementation replacing stub |
| `sidecar/security/auth.py` | SPIFFE SAN validation |
| `sidecar/config/settings.py` | Add `TLSConfig` model |
| `sidecar/listeners/inbound.py` | Pass `RotatingSSLContext` to `TCPSite` |
| `sidecar/connection/http_client.py` | Inject client cert into `httpx.AsyncClient` |
| `sidecar/telemetry/metrics.py` | Add `cert_expiry_seconds` gauge |
| `sidecar/main.py` | Start `CertWatcher` background task |
| `pyproject.toml` | Add `cryptography>=41.0` package |
| `examples/basic-config.yaml` | Add `tls:` section |

---

## New Dependencies

```
cryptography>=41.0    # parse X.509 cert expiry date
```

(`httpx` and `aiohttp` already handle the TLS socket layer via Python's built-in `ssl`.)

---

## Configuration

Add to `examples/basic-config.yaml`:

```yaml
tls:
  enabled: true
  cert_file: certs/sidecar.pem
  key_file: certs/sidecar.key
  ca_bundle: certs/ca.pem
  rotation_check_interval: 60    # check every 60 seconds
  rotation_threshold: 300        # rotate when < 5 minutes remain
  # spiffe_socket: /run/spire/sockets/agent.sock   # uncomment for SPIFFE
```

---

## Complexity Hotspots

| Area | Why it's tricky |
|------|----------------|
| Hot-swap without restart | aiohttp resolves `ssl_context` per-accept; replacing the wrapped context must be atomic to avoid a race between the watcher and an accept() call |
| In-flight connections | Connections already established before rotation must complete normally; only new connections use the new cert |
| Client cert in httpx | `httpx.AsyncClient` takes `ssl.SSLContext` but must be configured for client-mode mTLS, not server-mode |
| SPIFFE SAN parsing | X.509 SAN extension parsing requires the `cryptography` library; the URI format must exactly match the SPIFFE spec |
| Test cert lifecycle | Test certs must be generated per test run with very short validity (minutes) so expiry-triggered rotation can be tested quickly |

---

## Verification

1. Generate local dev certs (see step 1 above).
2. Start sidecar with `tls.enabled: true`.
3. Confirm plain HTTP connection is rejected:
   ```
   curl http://localhost:15000/health
   # expected: connection reset / SSL error
   ```
4. Confirm mTLS connection works:
   ```
   curl --cacert certs/ca.pem --cert certs/client.pem --key certs/client.key \
        https://localhost:15000/health
   # expected: {"status": "healthy"}
   ```
5. Simulate rotation: replace `certs/sidecar.pem` with a new cert, wait one
   `rotation_check_interval`. Confirm `cert_expiry_seconds` gauge updates in Prometheus.
6. Run integration tests: `pytest tests/integration/test_mtls_handshake.py -v`
