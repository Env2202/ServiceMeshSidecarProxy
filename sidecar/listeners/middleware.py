import time
from aiohttp import web

from ..telemetry.context import RequestContext
from ..telemetry.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"

logger = get_logger("middleware")


@web.middleware
async def request_context_middleware(request: web.Request, handler):
    """Middleware that extracts or generates request ID and sets up request context.

    This middleware:
    1. Extracts X-Request-ID from incoming headers or generates a new one
    2. Sets up request context for the async call chain
    3. Adds X-Request-ID to response headers
    4. Logs request start and completion
    """
    # Extract existing request ID or generate new one
    request_id = request.headers.get(REQUEST_ID_HEADER)

    # Create and set context
    context = RequestContext.create(
        method=request.method,
        path=request.path,
        existing_id=request_id
    )
    context.set_current()

    request_logger = get_logger("inbound")
    request_logger.info(
        "Request started",
        method=request.method,
        path=request.path,
        remote=request.remote,
        user_agent=request.headers.get("User-Agent")
    )

    try:
        response = await handler(request)

        # Add request ID to response headers
        response.headers[REQUEST_ID_HEADER] = context.request_id

        duration = time.time() - context.start_time
        request_logger.info(
            "Request completed",
            status=response.status,
            duration_ms=round(duration * 1000, 2)
        )

        return response

    except Exception as e:
        request_logger.error("Request failed", error=str(e))
        raise