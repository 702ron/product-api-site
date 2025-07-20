"""
Prometheus metrics collection for Amazon Product Intelligence Platform.
"""
import time
from typing import Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Info, generate_latest, 
    CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# API Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'Time spent processing API requests',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

api_requests_in_progress = Gauge(
    'api_requests_in_progress',
    'Number of API requests currently being processed'
)

# Queue System Metrics
queue_jobs_total = Counter(
    'queue_jobs_total',
    'Total number of queue jobs processed',
    ['job_type', 'status']
)

queue_job_duration = Histogram(
    'queue_job_duration_seconds',
    'Time spent processing queue jobs',
    ['job_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0]
)

queue_job_errors_total = Counter(
    'queue_job_errors_total',
    'Total number of queue job errors',
    ['job_type']
)

queue_pending_jobs = Gauge(
    'queue_pending_jobs',
    'Number of pending jobs in queue',
    ['priority']
)

queue_processing_jobs = Gauge(
    'queue_processing_jobs',
    'Number of jobs currently being processed'
)

queue_worker_active_jobs = Gauge(
    'queue_worker_active_jobs',
    'Number of active jobs per worker',
    ['job_type']
)

# Price Monitoring Metrics
price_monitor_checks_total = Counter(
    'price_monitor_checks_total',
    'Total number of price monitor checks',
    ['asin', 'marketplace']
)

price_monitor_alerts_total = Counter(
    'price_monitor_alerts_total', 
    'Total number of price alerts sent',
    ['asin', 'marketplace']
)

price_monitor_errors_total = Counter(
    'price_monitor_errors_total',
    'Total number of price monitor errors',
    ['asin', 'marketplace', 'error_type']
)

price_monitor_duration = Histogram(
    'price_monitor_duration_seconds',
    'Time spent checking prices',
    ['asin', 'marketplace'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

active_price_monitors = Gauge(
    'active_price_monitors',
    'Number of active price monitors',
    ['marketplace']
)

# Business Metrics
total_users = Gauge(
    'total_users',
    'Total number of registered users'
)

active_users_24h = Gauge(
    'active_users_24h',
    'Number of users active in the last 24 hours'
)

total_user_credits = Gauge(
    'total_user_credits',
    'Total credits across all users'
)

avg_user_credit_balance = Gauge(
    'avg_user_credit_balance',
    'Average credit balance per user'
)

daily_revenue = Gauge(
    'daily_revenue',
    'Daily revenue in dollars'
)

credits_purchased_total = Counter(
    'credits_purchased_total',
    'Total number of credits purchased',
    ['package_type']
)

credits_used_total = Counter(
    'credits_used_total',
    'Total number of credits used',
    ['operation_type']
)

# External API Metrics
external_api_calls_total = Counter(
    'external_api_calls_total',
    'Total number of external API calls',
    ['provider', 'status']
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'Time spent on external API calls',
    ['provider'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

external_api_rate_limit_remaining = Gauge(
    'external_api_rate_limit_remaining',
    'Remaining rate limit for external APIs',
    ['provider']
)

# Database Metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

database_connections_failed_total = Counter(
    'database_connections_failed_total',
    'Total number of failed database connections'
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Time spent executing database queries',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Cache Metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)

# Application Info
app_info = Info(
    'app_info',
    'Application information'
)

# Error Metrics
application_errors_total = Counter(
    'application_errors_total',
    'Total number of application errors',
    ['error_type', 'endpoint']
)

# Credit Refund Metrics
credit_refunds_total = Counter(
    'credit_refunds_total',
    'Total number of credit refunds issued',
    ['reason']
)

credit_refund_amount_total = Counter(
    'credit_refund_amount_total',
    'Total amount of credits refunded',
    ['reason']
)

# FNSKU Conversion Metrics
fnsku_conversions_total = Counter(
    'fnsku_conversions_total',
    'Total number of FNSKU conversions',
    ['status']
)

fnsku_conversion_confidence = Histogram(
    'fnsku_conversion_confidence',
    'FNSKU conversion confidence scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect API metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        api_requests_in_progress.inc()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract endpoint info
            method = request.method
            endpoint = self._get_endpoint_name(request)
            status = str(response.status_code)
            
            # Record metrics
            api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            api_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error
            endpoint = self._get_endpoint_name(request)
            application_errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint
            ).inc()
            raise
        finally:
            api_requests_in_progress.dec()
    
    def _get_endpoint_name(self, request: Request) -> str:
        """Extract meaningful endpoint name from request."""
        path = request.url.path
        
        # Clean up path for metrics
        if path.startswith('/api/v1/'):
            # Remove /api/v1 prefix and extract main endpoint
            clean_path = path[7:]  # Remove '/api/v1'
            parts = clean_path.split('/')
            if len(parts) >= 2:
                return f"/{parts[1]}/{parts[2]}" if len(parts) > 2 else f"/{parts[1]}"
            return clean_path
        
        return path if path != "/" else "/root"


def init_metrics():
    """Initialize application metrics with basic info."""
    app_info.info({
        'name': 'Amazon Product Intelligence Platform',
        'version': '1.0.0',
        'description': 'API-first, credit-based SaaS platform for Amazon product intelligence'
    })


async def update_business_metrics(db):
    """Update business metrics from database."""
    try:
        from sqlalchemy import text
        
        # Total users
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        total_users.set(result.scalar())
        
        # Active users in last 24 hours
        result = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id) 
            FROM query_logs 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """))
        active_users_24h.set(result.scalar() or 0)
        
        # Total credits and average balance
        result = await db.execute(text("SELECT SUM(credit_balance), AVG(credit_balance) FROM users"))
        total_credits, avg_balance = result.fetchone()
        total_user_credits.set(total_credits or 0)
        avg_user_credit_balance.set(avg_balance or 0)
        
        # Daily revenue (from purchases today)
        result = await db.execute(text("""
            SELECT COALESCE(SUM(amount), 0) * 0.01 as daily_revenue
            FROM credit_transactions 
            WHERE transaction_type = 'purchase' 
            AND DATE(created_at) = CURRENT_DATE
        """))
        daily_revenue.set(result.scalar() or 0)
        
    except Exception as e:
        # Don't fail the app if metrics update fails
        pass


def get_metrics():
    """Get current metrics in Prometheus format."""
    return generate_latest(REGISTRY)