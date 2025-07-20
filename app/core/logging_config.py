"""
Enhanced logging configuration for Amazon Product Intelligence Platform.
"""
import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_data['response_time'] = record.response_time
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def setup_logging() -> None:
    """Setup logging configuration based on environment."""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = "DEBUG" if settings.debug else "INFO"
    
    # Common formatter config
    formatters = {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "()": "app.core.logging_config.JSONFormatter"
        }
    }
    
    # Handler configurations
    handlers: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "detailed" if settings.debug else "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
    }
    
    # Logger configurations
    loggers = {
        "app": {
            "level": log_level,
            "handlers": ["console", "file", "error_file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "sqlalchemy.engine": {
            "level": "INFO" if settings.debug else "WARNING",
            "handlers": ["file"],
            "propagate": False
        },
        "stripe": {
            "level": "INFO",
            "handlers": ["file"],
            "propagate": False
        },
        "httpx": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False
        }
    }
    
    # Root logger
    root_logger = {
        "level": log_level,
        "handlers": ["console", "file"]
    }
    
    # Complete logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers,
        "root": root_logger
    }
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger("app.core.logging")
    logger.info("Logging configuration initialized", extra={
        "log_level": log_level,
        "debug_mode": settings.debug,
        "environment": getattr(settings, 'environment', 'development')
    })


def get_logger(name: str) -> logging.Logger:
    """Get logger with consistent naming."""
    return logging.getLogger(f"app.{name}")


def log_api_request(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: int,
    response_time: float,
    user_id: str = None,
    request_id: str = None,
    ip_address: str = None
) -> None:
    """Log API request with structured data."""
    logger.info(
        f"{method} {endpoint} - {status_code} - {response_time:.3f}s",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            "user_id": user_id,
            "request_id": request_id,
            "ip_address": ip_address
        }
    )


def log_business_event(
    logger: logging.Logger,
    event_type: str,
    event_data: Dict[str, Any],
    user_id: str = None
) -> None:
    """Log business events for analytics."""
    logger.info(
        f"Business event: {event_type}",
        extra={
            "event_type": event_type,
            "event_data": event_data,
            "user_id": user_id,
            "category": "business"
        }
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    details: Dict[str, Any],
    ip_address: str = None,
    user_id: str = None
) -> None:
    """Log security-related events."""
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "details": details,
            "ip_address": ip_address,
            "user_id": user_id,
            "category": "security"
        }
    )


def log_external_api_call(
    logger: logging.Logger,
    provider: str,
    endpoint: str,
    status_code: int,
    response_time: float,
    credits_used: int = None
) -> None:
    """Log external API calls for monitoring."""
    logger.info(
        f"External API call: {provider} {endpoint} - {status_code} - {response_time:.3f}s",
        extra={
            "provider": provider,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time": response_time,
            "credits_used": credits_used,
            "category": "external_api"
        }
    )