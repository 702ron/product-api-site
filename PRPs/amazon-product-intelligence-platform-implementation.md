# Amazon Product Intelligence Platform - Implementation Task PRP

> Comprehensive task breakdown for shipping the complete Amazon Product Intelligence Platform based on PRD requirements

## Context & Architecture Analysis

```yaml
context:
  docs:
    - url: amazon-product-intelligence-platform-prd.md
      focus: Complete feature set, API specifications, business requirements
    - url: PRPs/ai_docs/fastapi_production_patterns.md
      focus: FastAPI best practices and patterns
    - url: PRPs/ai_docs/stripe_credit_system_patterns.md
      focus: Credit system implementation patterns

  current_state:
    - foundation: Solid FastAPI structure with models, services, endpoints (skeleton)
    - database: Complete schema with proper relationships
    - testing: Comprehensive test structure in place
    - tooling: Production-ready development environment
    - deployment: Docker configuration and Alembic migrations

  patterns:
    - file: app/main.py
      copy: Middleware and router registration pattern
    - file: app/models/models.py
      copy: Database model pattern with relationships
    - file: app/services/credit_service.py
      copy: Service layer pattern with async operations
    - file: app/api/v1/endpoints/auth.py
      copy: FastAPI endpoint pattern with dependency injection

  gotchas:
    - issue: "Supabase auth integration requires specific JWT handling"
      fix: "Use app.core.security patterns for token validation"
    - issue: "Stripe webhooks need idempotent processing"
      fix: "Check WebhookLog table before processing events"
    - issue: "Amazon APIs have strict rate limiting"
      fix: "Implement caching and queue system for bulk operations"
    - issue: "Credit deduction must be atomic with API calls"
      fix: "Use database transactions and rollback on API failures"
```

## Phase 1: Core Backend Implementation (Weeks 1-4)

### Backend Service Implementation

```
READ app/services/amazon_service.py:
  - UNDERSTAND: Current service structure and patterns
  - IDENTIFY: Missing implementation methods
  - NOTE: Async patterns and error handling approach

UPDATE app/services/amazon_service.py:
  - IMPLEMENT: get_product_by_asin method with external API integration
  - ADD: Rate limiting with exponential backoff
  - ADD: Response caching with TTL
  - VALIDATE: python -c "from app.services.amazon_service import amazon_service; print('Service loads')"
  - IF_FAIL: Check import dependencies and async patterns

UPDATE app/services/credit_service.py:
  - IMPLEMENT: deduct_credits method with atomic transactions
  - ADD: refund_credits method for failed operations
  - ADD: get_usage_analytics method
  - VALIDATE: uv run pytest app/tests/test_credits.py -v
  - IF_FAIL: Check database transaction handling

UPDATE app/services/fnsku_service.py:
  - IMPLEMENT: convert_fnsku_to_asin method
  - ADD: confidence scoring algorithm
  - ADD: bulk conversion processing
  - VALIDATE: uv run pytest app/tests/test_conversion.py -v
  - IF_FAIL: Check FNSKU validation patterns

UPDATE app/services/payment_service.py:
  - IMPLEMENT: create_checkout_session method
  - ADD: process_webhook_event method with idempotency
  - ADD: handle_payment_success method
  - VALIDATE: uv run pytest app/tests/test_payments.py -k payment_service -v
  - IF_FAIL: Check Stripe SDK integration
```

### API Endpoint Implementation

```
UPDATE app/api/v1/endpoints/products.py:
  - IMPLEMENT: get_product_by_asin endpoint with credit deduction
  - ADD: bulk_product_query endpoint with queue processing
  - ADD: get_product_cache_stats endpoint for monitoring
  - VALIDATE: uv run pytest app/tests/test_products.py -v
  - IF_FAIL: Check service layer integration and schema validation

UPDATE app/api/v1/endpoints/conversion.py:
  - IMPLEMENT: convert_fnsku_to_asin endpoint
  - ADD: bulk_fnsku_conversion endpoint
  - ADD: validate_fnsku endpoint
  - VALIDATE: uv run pytest app/tests/test_conversion.py -v
  - IF_FAIL: Check FNSKU validation regex and service calls

UPDATE app/api/v1/endpoints/payments.py:
  - IMPLEMENT: create_payment_session endpoint
  - ADD: stripe_webhook endpoint with signature verification
  - ADD: get_payment_history endpoint
  - VALIDATE: uv run pytest app/tests/test_payments.py -v
  - IF_FAIL: Check Stripe webhook signature validation

UPDATE app/api/v1/endpoints/credits.py:
  - IMPLEMENT: get_credit_balance endpoint
  - ADD: get_usage_history endpoint with pagination
  - ADD: get_usage_analytics endpoint
  - VALIDATE: uv run pytest app/tests/test_credits.py -v
  - IF_FAIL: Check pagination implementation and credit calculations
```

### External API Integration

```
CREATE app/external/amazon_api.py:
  - IMPLEMENT: AmazonAPIClient class with multiple providers
  - ADD: rate_limited_request method with backoff
  - ADD: parse_product_response method
  - VALIDATE: python -c "from app.external.amazon_api import AmazonAPIClient; print('Client created')"
  - IF_FAIL: Check API credentials and request formatting

CREATE app/external/stripe_client.py:
  - IMPLEMENT: StripeClient class with webhook handling
  - ADD: create_checkout_session method
  - ADD: verify_webhook_signature method
  - VALIDATE: python -c "from app.external.stripe_client import StripeClient; print('Client created')"
  - IF_FAIL: Check Stripe SDK installation and configuration

UPDATE app/core/config.py:
  - ADD: AMAZON_API_KEY, STRIPE_SECRET_KEY, REDIS_URL settings
  - ADD: rate limiting configuration
  - ADD: cache TTL settings
  - VALIDATE: python -c "from app.core.config import settings; print(settings.amazon_api_key[:8])"
  - IF_FAIL: Check environment variable loading
```

## Phase 2: Caching & Performance (Week 5)

### Redis Integration

```
CREATE app/core/cache.py:
  - IMPLEMENT: RedisCache class with async operations
  - ADD: get, set, delete methods with TTL
  - ADD: cache_key generation methods
  - VALIDATE: python -c "from app.core.cache import redis_cache; print('Cache client created')"
  - IF_FAIL: Check Redis connection and aioredis installation

UPDATE app/services/amazon_service.py:
  - ADD: cache integration to get_product_by_asin
  - IMPLEMENT: cache-aside pattern with TTL
  - ADD: cache invalidation on errors
  - VALIDATE: uv run pytest app/tests/test_amazon_service.py::test_caching -v
  - IF_FAIL: Check cache key generation and TTL settings

UPDATE app/api/deps.py:
  - ADD: cache dependency injection
  - IMPLEMENT: cache warming for popular products
  - ADD: cache statistics tracking
  - VALIDATE: uv run pytest app/tests/test_deps.py -v
  - IF_FAIL: Check dependency injection pattern
```

### Queue System for Bulk Operations

```
CREATE app/core/queue.py:
  - IMPLEMENT: AsyncQueue class using Redis
  - ADD: enqueue, dequeue methods
  - ADD: job status tracking
  - VALIDATE: python -c "from app.core.queue import async_queue; print('Queue created')"
  - IF_FAIL: Check Redis pub/sub implementation

CREATE app/workers/bulk_processor.py:
  - IMPLEMENT: BulkProductProcessor class
  - ADD: process_bulk_asin_job method
  - ADD: job progress updates
  - VALIDATE: python -c "from app.workers.bulk_processor import BulkProductProcessor; print('Worker created')"
  - IF_FAIL: Check async worker pattern and error handling

UPDATE app/api/v1/endpoints/products.py:
  - UPDATE: bulk_product_query to use queue system
  - ADD: get_bulk_job_status endpoint
  - ADD: download_bulk_results endpoint
  - VALIDATE: uv run pytest app/tests/test_products.py::test_bulk_processing -v
  - IF_FAIL: Check job queuing and status tracking
```

## Phase 3: Frontend Dashboard (Weeks 6-8)

### React Dashboard Setup

```
CREATE frontend/package.json:
  - IMPLEMENT: React 18 + TypeScript + Vite configuration
  - ADD: Dependencies: @tanstack/react-query, axios, recharts
  - ADD: Development dependencies: eslint, prettier, vitest
  - VALIDATE: cd frontend && npm install && npm run build
  - IF_FAIL: Check Node.js version and dependency conflicts

CREATE frontend/src/lib/api.ts:
  - IMPLEMENT: API client with axios and auth interceptors
  - ADD: request/response interceptors for auth
  - ADD: error handling with retry logic
  - VALIDATE: cd frontend && npm run typecheck
  - IF_FAIL: Check TypeScript configuration and types

CREATE frontend/src/components/AuthProvider.tsx:
  - IMPLEMENT: Authentication context with Supabase
  - ADD: login, logout, signup methods
  - ADD: token refresh handling
  - VALIDATE: cd frontend && npm run test -- AuthProvider
  - IF_FAIL: Check Supabase client configuration
```

### Dashboard Components

```
CREATE frontend/src/pages/Dashboard.tsx:
  - IMPLEMENT: Main dashboard with credit balance
  - ADD: Usage statistics charts
  - ADD: Recent query history
  - VALIDATE: cd frontend && npm run build
  - IF_FAIL: Check component imports and API integration

CREATE frontend/src/pages/ProductQuery.tsx:
  - IMPLEMENT: ASIN query form with validation
  - ADD: Real-time results display
  - ADD: Export functionality (CSV/JSON)
  - VALIDATE: cd frontend && npm run test -- ProductQuery
  - IF_FAIL: Check form validation and API calls

CREATE frontend/src/pages/CreditManagement.tsx:
  - IMPLEMENT: Credit purchase interface
  - ADD: Stripe checkout integration
  - ADD: Payment history display
  - VALIDATE: cd frontend && npm run test -- CreditManagement
  - IF_FAIL: Check Stripe integration and webhook handling

CREATE frontend/src/pages/FNSKUConverter.tsx:
  - IMPLEMENT: FNSKU to ASIN conversion interface
  - ADD: Bulk upload functionality
  - ADD: Confidence score display
  - VALIDATE: cd frontend && npm run test -- FNSKUConverter
  - IF_FAIL: Check file upload handling and validation
```

## Phase 4: Monitoring & Analytics (Week 9)

### Monitoring Implementation

```
CREATE app/monitoring/metrics.py:
  - IMPLEMENT: PrometheusMetrics class
  - ADD: API response time metrics
  - ADD: Credit usage metrics
  - ADD: Error rate tracking
  - VALIDATE: python -c "from app.monitoring.metrics import metrics; print('Metrics initialized')"
  - IF_FAIL: Check prometheus_client installation

UPDATE app/main.py:
  - ADD: metrics middleware for request tracking
  - ADD: /metrics endpoint for Prometheus
  - ADD: health check with dependency status
  - VALIDATE: curl http://localhost:8000/metrics | grep api_requests_total
  - IF_FAIL: Check metrics middleware registration

CREATE app/monitoring/alerts.py:
  - IMPLEMENT: AlertManager class
  - ADD: credit balance alerts
  - ADD: API error rate alerts
  - ADD: external API failure alerts
  - VALIDATE: uv run pytest app/tests/test_monitoring.py -v
  - IF_FAIL: Check alert condition logic
```

### Analytics Dashboard

```
CREATE app/api/v1/endpoints/analytics.py:
  - IMPLEMENT: get_usage_analytics endpoint
  - ADD: get_revenue_metrics endpoint
  - ADD: get_api_performance_metrics endpoint
  - VALIDATE: uv run pytest app/tests/test_analytics.py -v
  - IF_FAIL: Check database aggregation queries

UPDATE frontend/src/pages/Analytics.tsx:
  - IMPLEMENT: Usage analytics charts
  - ADD: Revenue dashboard for admins
  - ADD: Performance metrics display
  - VALIDATE: cd frontend && npm run test -- Analytics
  - IF_FAIL: Check chart component integration
```

## Phase 5: Production Deployment (Week 10)

### Security Hardening

```
UPDATE app/core/security.py:
  - IMPLEMENT: JWT token validation with Supabase
  - ADD: API key authentication for service accounts
  - ADD: request rate limiting per user
  - VALIDATE: uv run pytest app/tests/test_security.py -v
  - IF_FAIL: Check JWT library integration

UPDATE app/middleware/security.py:
  - IMPLEMENT: CORS configuration for production
  - ADD: CSRF protection for state-changing operations
  - ADD: SQL injection protection validation
  - VALIDATE: bandit -r app/ -ll
  - IF_FAIL: Check security scan results

CREATE app/core/validation.py:
  - IMPLEMENT: input validation schemas
  - ADD: ASIN format validation
  - ADD: FNSKU format validation
  - ADD: request size limits
  - VALIDATE: uv run pytest app/tests/test_validation.py -v
  - IF_FAIL: Check validation regex patterns
```

### Deployment Configuration

```
UPDATE docker-compose.yml:
  - ADD: production environment configuration
  - ADD: Redis service configuration
  - ADD: PostgreSQL with persistent volumes
  - VALIDATE: docker-compose up -d && curl http://localhost:8000/health
  - IF_FAIL: Check service dependencies and health checks

CREATE kubernetes/manifests/:
  - IMPLEMENT: deployment, service, ingress manifests
  - ADD: ConfigMap for application configuration
  - ADD: Secret for API keys and database credentials
  - VALIDATE: kubectl apply -f kubernetes/manifests/ --dry-run=client
  - IF_FAIL: Check YAML syntax and resource limits

CREATE .github/workflows/deploy.yml:
  - IMPLEMENT: CI/CD pipeline with tests
  - ADD: automated deployment on main branch
  - ADD: security scanning and dependency updates
  - VALIDATE: Commit and check GitHub Actions status
  - IF_FAIL: Check workflow syntax and secrets configuration
```

## Validation Checkpoints

```
CHECKPOINT phase1_backend:
  - RUN: uv run pytest app/tests/ -v --cov=app
  - REQUIRE: >95% test coverage, all tests passing
  - RUN: ruff check && mypy app/
  - REQUIRE: No linting or type errors
  - RUN: bandit -r app/ -ll
  - REQUIRE: No high or medium security issues
  - CONTINUE: Only when all validation passes

CHECKPOINT phase2_performance:
  - START: docker-compose up -d redis
  - RUN: uv run pytest app/tests/test_performance.py -v
  - REQUIRE: API response time <200ms for cached requests
  - RUN: redis-cli ping
  - REQUIRE: Redis connectivity confirmed
  - CONTINUE: Only when performance targets met

CHECKPOINT phase3_frontend:
  - RUN: cd frontend && npm run build
  - REQUIRE: Build succeeds without warnings
  - RUN: cd frontend && npm run test
  - REQUIRE: All component tests passing
  - RUN: cd frontend && npm run e2e
  - REQUIRE: End-to-end tests passing
  - CONTINUE: Only when frontend fully functional

CHECKPOINT phase4_monitoring:
  - START: docker-compose up -d prometheus
  - RUN: curl http://localhost:8000/metrics
  - REQUIRE: Metrics endpoint returns Prometheus format
  - RUN: uv run pytest app/tests/test_monitoring.py -v
  - REQUIRE: All monitoring tests passing
  - CONTINUE: Only when monitoring operational

CHECKPOINT phase5_production:
  - RUN: docker-compose -f docker-compose.prod.yml up -d
  - RUN: ./scripts/integration_test.sh
  - REQUIRE: All integration tests passing
  - RUN: ./scripts/security_audit.sh
  - REQUIRE: Security audit passes
  - RUN: ./scripts/performance_test.sh
  - REQUIRE: Load test targets met (1000 req/s, <200ms p95)
  - CONTINUE: Only when production-ready
```

## Debug Patterns & Troubleshooting

```
DEBUG api_integration_failure:
  - CHECK: External API credentials in environment
  - TEST: curl with API key manually
  - READ: Service logs for authentication errors
  - FIX: Update API key or request format

DEBUG credit_deduction_mismatch:
  - CHECK: Database transaction isolation level
  - TEST: Concurrent credit deduction scenario
  - READ: CreditTransaction table for anomalies
  - FIX: Add database locks or retry logic

DEBUG cache_inconsistency:
  - CHECK: Redis connection and memory usage
  - TEST: Cache TTL and eviction policies
  - READ: Cache hit/miss ratios in metrics
  - FIX: Adjust TTL or implement cache warming

DEBUG payment_webhook_failure:
  - CHECK: Stripe webhook signature verification
  - TEST: Webhook endpoint with test events
  - READ: WebhookLog table for processing status
  - FIX: Update webhook signature validation

DEBUG frontend_auth_issues:
  - CHECK: Supabase configuration and JWT tokens
  - TEST: Login flow with browser dev tools
  - READ: Network tab for API request failures
  - FIX: Update token refresh logic or CORS settings
```

## Success Criteria

### Technical Validation
- [ ] All API endpoints return <200ms response time (95th percentile)
- [ ] Test coverage >95% with all tests passing
- [ ] Zero critical security vulnerabilities in audit
- [ ] Frontend loads and functions in <3 seconds
- [ ] Database queries optimized with proper indexing
- [ ] Cache hit rate >80% for product data requests
- [ ] Queue system processes 1000+ jobs/minute
- [ ] Monitoring dashboard shows real-time metrics

### Business Validation
- [ ] Credit purchase flow works end-to-end
- [ ] ASIN queries return accurate product data
- [ ] FNSKU conversion achieves >90% accuracy
- [ ] Bulk processing handles 100+ ASINs efficiently
- [ ] User onboarding completes in <5 minutes
- [ ] Payment processing integrates seamlessly
- [ ] Analytics provide actionable insights
- [ ] Documentation covers all user scenarios

### Operational Validation
- [ ] Deployment pipeline automates testing and deployment
- [ ] Monitoring alerts trigger on system issues
- [ ] Database backups and recovery procedures tested
- [ ] Load balancing handles traffic spikes
- [ ] Security measures protect against common attacks
- [ ] Error handling provides meaningful user feedback
- [ ] Logging captures sufficient debugging information
- [ ] Performance metrics meet SLA requirements

## Final Integration Test Commands

```bash
# Complete system validation
./scripts/full_system_test.sh

# Performance benchmarking
artillery run load-tests/complete-user-flow.yml
k6 run performance-tests/bulk-processing-test.js

# Security validation
npm audit --audit-level high
safety check --full-report
bandit -r app/ -ll

# Business logic validation
uv run pytest app/tests/integration/ -v
uv run python scripts/validate_credit_flow.py
uv run python scripts/validate_product_accuracy.py

# Deployment validation
docker-compose -f docker-compose.prod.yml up -d
curl -X POST http://localhost:8000/api/v1/products/asin \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"asin": "B08N5WRWNW", "marketplace": "US"}'
```

---

## Implementation Priority

**Week 1-2**: Core backend services and API implementations
**Week 3-4**: External API integrations and credit system
**Week 5**: Caching and queue system for performance
**Week 6-7**: Frontend dashboard and user interface
**Week 8**: Advanced features and bulk processing
**Week 9**: Monitoring, analytics, and observability
**Week 10**: Production deployment and security hardening

This PRP provides a comprehensive roadmap for implementing the complete Amazon Product Intelligence Platform while maintaining the existing codebase structure and following established patterns.