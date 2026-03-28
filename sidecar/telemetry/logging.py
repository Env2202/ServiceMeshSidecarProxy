import logging
import sys
from typing import Optional

import structlog

from .context import REQUEST_ID_CTX


def add_request_id_processor(logger, method_name, event_dict):
    """Structlog processor that adds request_id from context to log entries."""
    try:
        request_id = REQUEST_ID_CTX.get()
        if request_id:
            event_dict["request_id"] = request_id
    except LookupError:
        pass
    return event_dict


def get_logger(component: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with component bound.

    Args:
        component: Optional component name to include in logs

    Returns:
        A BoundLogger with component bound
    """
    logger = structlog.get_logger(component or "sidecar")
    return logger.bind(component=component or "sidecar")


def configure_logging(level: str = "info", format: str = "json") -> None:
    """Configure structlog with processors for request context.

    Args:
        level: Log level (debug, info, warning, error)
        format: Output format (json or console)
    """
    # Map string level to logging level
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }

    log_level = level_map.get(level.lower(), logging.INFO)

    # Configure structlog processors
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_request_id_processor,  # Add request_id from context
    ]

    if format == "json":
        formatter = structlog.processors.JSONRenderer()
    else:
        formatter = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [formatter],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,  # Don't cache to allow reconfiguration
    )

    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add a stream handler to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter_std = logging.Formatter("%(message)s")
    handler.setFormatter(formatter_std)
    root_logger.addHandler(handler)
