# utils/logging_config.py - GCP Cloud Run optimized logging
import structlog
import logging
import sys
import os
from typing import Any


def setup_logging():
    """Setup structured logging optimized for GCP Cloud Run"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
    )

    # Configure structlog for GCP-compatible JSON logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Add GCP-specific fields
            _add_gcp_fields,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _add_gcp_fields(logger, method_name, event_dict):
    """Add GCP-specific logging fields for Cloud Run"""
    
    # Add service information
    event_dict["service"] = os.getenv("K_SERVICE", "avestoai-backend")
    event_dict["version"] = os.getenv("K_REVISION", "unknown")
    
    # Add trace information if available (for request correlation)
    trace_header = os.getenv("HTTP_X_CLOUD_TRACE_CONTEXT")
    if trace_header:
        try:
            trace_id = trace_header.split("/")[0]
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "unknown")
            event_dict["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace_id}"
        except (IndexError, AttributeError):
            pass
    
    # Add severity mapping for GCP
    if "level" in event_dict:
        level_mapping = {
            "debug": "DEBUG",
            "info": "INFO", 
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL"
        }
        event_dict["severity"] = level_mapping.get(event_dict["level"].lower(), "INFO")
    
    return event_dict
