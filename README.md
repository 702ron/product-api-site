# Amazon Product Intelligence Platform

API-first, credit-based SaaS platform for Amazon product intelligence with queue-based bulk processing.

## Features

- **Product Data API**: Real-time Amazon product data retrieval
- **FNSKU Conversion**: Convert FNSKUs to ASINs with confidence scoring
- **Credit System**: Secure credit-based billing with Stripe integration
- **Queue System**: Redis-based queue for bulk operations
- **Monitoring**: Comprehensive metrics with Prometheus/Grafana
- **Authentication**: Supabase JWT authentication with social login

## Quick Start

1. Install dependencies:
   ```bash
   uv install
   ```

2. Configure environment:
   ```bash
   cp .env.production .env
   # Edit .env with your API keys
   ```

3. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```

4. Start the application:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. Start queue worker:
   ```bash
   uv run python app/workers/daemon.py
   ```

## API Documentation

Visit `/docs` for interactive API documentation.

## Queue System

The platform includes a Redis-based queue system for processing bulk operations:

- `/api/v1/products/bulk-async` - Bulk product queries
- `/api/v1/conversion/bulk-async` - Bulk FNSKU conversions
- `/api/v1/jobs/status/{job_id}` - Job status tracking

## Monitoring

- **Metrics**: `/metrics` (Prometheus format)
- **Health**: `/health`
- **API Docs**: `/docs`