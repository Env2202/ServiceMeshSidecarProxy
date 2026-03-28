# tests/unit/test_outbound_headers.py
# Phase 5: Outbound Header Injection Tests
# TDD: Write failing tests first, then implement

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from sidecar.telemetry.context import RequestContext


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear Prometheus registry between tests to avoid duplicates."""
    from prometheus_client import REGISTRY
    # Collect all collectors to unregister
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except:
            pass
    yield


def create_test_config():
    """Create a test configuration with required ports."""
    from sidecar.config.settings import SidecarConfig
    return SidecarConfig(
        server={
            "inbound_port": 15000,
            "outbound_port": 15001,
            "admin_port": 15002
        }
    )


def setup_client_with_router(client):
    """Set up a basic router for the client."""
    from sidecar.pipeline.router import Router, Route, RouteMatch
    route = Route(
        name="test-route",
        match=RouteMatch(path_prefix="/"),
        cluster="test-cluster"
    )
    client.router = Router([route])


class TestOutboundHeaderInjection:
    """Tests for X-Request-ID header injection in outbound requests."""

    @pytest.mark.asyncio
    async def test_outbound_injects_request_id_header(self):
        """Outbound client should inject X-Request-ID header."""
        from sidecar.listeners.outbound import OutboundClient

        # Set up request context
        ctx = RequestContext.create(existing_id="outbound-test-123")
        ctx.set_current()

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        # Mock the httpx client
        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            result = await client.forward(request)

            # Verify the mock was called
            assert mock_get.called, "HTTP client get was not called"
            # Verify X-Request-ID header was passed
            call_args = mock_get.call_args
            assert call_args is not None
            passed_headers = call_args.kwargs.get('headers', {})
            assert passed_headers.get('X-Request-ID') == 'outbound-test-123'

    @pytest.mark.asyncio
    async def test_outbound_header_matches_context_request_id(self):
        """Header value should match current context request_id."""
        from sidecar.listeners.outbound import OutboundClient

        ctx = RequestContext.create(existing_id="custom-request-id-456")
        ctx.set_current()

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            await client.forward(request)

            call_args = mock_get.call_args
            passed_headers = call_args.kwargs.get('headers', {})
            assert passed_headers.get('X-Request-ID') == 'custom-request-id-456'

    @pytest.mark.asyncio
    async def test_outbound_no_header_without_context(self):
        """No X-Request-ID header when no context exists."""
        from sidecar.listeners.outbound import OutboundClient

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        # Mock the httpx client
        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            await client.forward(request)

            # Verify no X-Request-ID header was passed
            call_args = mock_get.call_args
            passed_headers = call_args.kwargs.get('headers', {})
            assert 'X-Request-ID' not in passed_headers

    @pytest.mark.asyncio
    async def test_outbound_works_without_context_no_error(self):
        """Outbound client should work without context (no error)."""
        from sidecar.listeners.outbound import OutboundClient

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            # Should not raise
            result = await client.forward(request)

            assert result["status_code"] == 200


class TestOutboundRequestIdPropagation:
    """Tests for request ID propagation through outbound client."""

    @pytest.mark.asyncio
    async def test_request_id_propagated_to_backend(self):
        """Request ID should be propagated to backend service."""
        from sidecar.listeners.outbound import OutboundClient

        ctx = RequestContext.create(existing_id="propagation-test-789")
        ctx.set_current()

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            await client.forward(request)

            call_args = mock_get.call_args
            passed_headers = call_args.kwargs.get('headers', {})
            assert passed_headers.get('X-Request-ID') == 'propagation-test-789'

    @pytest.mark.asyncio
    async def test_different_request_ids_per_call(self):
        """Each outbound call should use the correct request ID from context."""
        from sidecar.listeners.outbound import OutboundClient

        config = create_test_config()
        client = OutboundClient(config)
        setup_client_with_router(client)

        # First call with one request ID
        ctx1 = RequestContext.create(existing_id="first-request-id")
        ctx1.set_current()

        with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)

            request = type('Request', (), {'path': '/api/test'})()
            await client.forward(request)

            call_args = mock_get.call_args
            passed_headers = call_args.kwargs.get('headers', {})
            assert passed_headers.get('X-Request-ID') == 'first-request-id'
