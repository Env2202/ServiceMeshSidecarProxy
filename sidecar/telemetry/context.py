import contextvars
import time
import uuid
from dataclasses import dataclass
from typing import Optional

REQUEST_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')
START_TIME_CTX: contextvars.ContextVar[float] = contextvars.ContextVar('start_time')


@dataclass
class RequestContext:
    """Request context that holds request ID and timing information."""
    request_id: str
    start_time: float
    method: Optional[str] = None
    path: Optional[str] = None
    route: Optional[str] = None

    @classmethod
    def create(
        cls,
        method: Optional[str] = None,
        path: Optional[str] = None,
        existing_id: Optional[str] = None
    ) -> "RequestContext":
        """Create a new RequestContext.

        Args:
            method: HTTP method (optional)
            path: Request path (optional)
            existing_id: Existing request ID to use, or None to generate new

        Returns:
            RequestContext with request_id and start_time set
        """
        if existing_id:
            request_id = existing_id
        else:
            request_id = f"req-{uuid.uuid4().hex[:12]}"

        return cls(
            request_id=request_id,
            start_time=time.time(),
            method=method,
            path=path
        )

    def set_current(self) -> None:
        """Set this context as the current context for the async context."""
        REQUEST_ID_CTX.set(self.request_id)
        START_TIME_CTX.set(self.start_time)
