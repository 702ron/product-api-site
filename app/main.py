"""
FastAPI application entry point with middleware, CORS, and error handling.
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import logging

from app.core.config import settings
from app.core.database import init_db, close_db
from app.monitoring import PrometheusMiddleware, init_metrics, get_metrics


# Configure enhanced logging
from app.core.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Amazon Product Intelligence Platform...")
    await init_db()
    logger.info("Database initialized")
    
    # Initialize metrics
    init_metrics()
    logger.info("Metrics initialized")
    
    # Initialize queue system and register handlers (temporarily disabled)
    # from app.core.queue import queue_manager
    # from app.workers.bulk_processor import register_handlers
    # await queue_manager.connect()
    # await register_handlers()
    logger.info("Queue system temporarily disabled for testing")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    # await queue_manager.disconnect()
    logger.info("Queue system disconnected (was disabled)")
    await close_db()
    logger.info("Database connections closed")


# FastAPI application instance
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API-first, credit-based SaaS platform for Amazon product intelligence",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to all requests."""
    from app.api.deps import get_request_id
    request_id = await get_request_id(request)
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Rate limiting middleware
@app.middleware("http")
async def rate_limiting(request: Request, call_next):
    """Apply rate limiting to API requests."""
    from app.api.deps import rate_limiter
    
    # Skip rate limiting for development - allow most API calls
    skip_paths = [
        "/health", "/", "/docs", "/redoc", "/openapi.json", "/metrics",
        "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/logout",
        "/api/v1/credits/", "/api/v1/monitoring/", "/api/v1/products/",
        "/api/v1/conversion/", "/api/v1/payments/"
    ]
    
    # Skip rate limiting if path starts with any skip path
    if any(request.url.path.startswith(skip_path) for skip_path in skip_paths):
        return await call_next(request)
    
    try:
        # Apply very lenient rate limiting for development
        await rate_limiter.check_rate_limit(
            request, 
            calls_per_minute=1000,  # Very high limit for development
            calls_per_second=100    # Very high limit for development
        )
        response = await call_next(request)
        return response
    except HTTPException as e:
        # Rate limit exceeded, return error response with CORS headers
        from fastapi.responses import JSONResponse
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
        # Merge with existing headers
        headers = {**cors_headers, **(e.headers or {})}
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers=headers
        )


# Content validation middleware
@app.middleware("http")
async def validate_content(request: Request, call_next):
    """Validate request content type and size."""
    from app.api.deps import validate_content_type, validate_request_size
    
    # Skip validation for GET requests and static endpoints
    if request.method == "GET" or request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    try:
        # Validate content type and size
        await validate_content_type(request)
        await validate_request_size(request)
        response = await call_next(request)
        return response
    except HTTPException as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )


# Maintenance mode middleware
@app.middleware("http")
async def check_maintenance(request: Request, call_next):
    """Check if API is in maintenance mode."""
    from app.api.deps import check_maintenance_mode
    
    # Skip maintenance check for health endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    try:
        await check_maintenance_mode()
        response = await call_next(request)
        return response
    except HTTPException as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers=e.headers
        )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    start_time = time.time()
    
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(f"Response status: {response.status_code}, Time: {process_time:.3f}s")
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Amazon Product Intelligence Platform API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST
    return Response(get_metrics(), media_type=CONTENT_TYPE_LATEST)


# Include API routers
from app.api.v1.endpoints import auth, credits, payments, products, conversion, jobs, monitoring, users
from app.api.v1.endpoints.admin import users as admin_users, system

app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(credits.router, prefix="/api/v1/credits", tags=["credits"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(conversion.router, prefix="/api/v1/conversion", tags=["conversion"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

# Admin routes
app.include_router(admin_users.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(system.router, prefix="/api/v1/admin", tags=["admin"])

# Global exception handlers
from app.core.exception_handlers import add_exception_handlers
add_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )