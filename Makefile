# Makefile for Amazon Product Intelligence Platform

.PHONY: help build dev test lint format clean docker-build docker-up docker-down docker-logs

# Default target
help:
	@echo "Available commands:"
	@echo "  help         Show this help message"
	@echo "  install      Install dependencies"
	@echo "  dev          Start development server"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  lint         Run linting tools"
	@echo "  format       Format code"
	@echo "  security     Run security checks"
	@echo "  clean        Clean up build artifacts"
	@echo "  docker-build Build Docker images"
	@echo "  docker-dev   Start development environment"
	@echo "  docker-prod  Start production environment"
	@echo "  docker-down  Stop Docker containers"
	@echo "  docker-logs  Show Docker logs"
	@echo "  migrate      Run database migrations"
	@echo "  migrate-down Run database migration rollback"

# Development commands
install:
	pip install -r requirements.txt
	pre-commit install

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

dev-https:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --ssl-keyfile=./ssl/key.pem --ssl-certfile=./ssl/cert.pem

# Testing commands
test:
	pytest app/tests/ -v

test-cov:
	pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=85

test-unit:
	pytest app/tests/ -v -m "unit"

test-integration:
	pytest app/tests/ -v -m "integration"

test-parallel:
	pytest app/tests/ -v -n auto

# Code quality commands
lint:
	ruff check app/
	mypy app/

lint-fix:
	ruff check app/ --fix

format:
	black app/
	isort app/

security:
	bandit -r app/
	safety check

# Database commands
migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-history:
	alembic history

migrate-current:
	alembic current

# Docker commands
docker-build:
	docker build -t amazon-product-api .

docker-build-dev:
	docker build -f Dockerfile.dev -t amazon-product-api:dev .

docker-dev:
	docker-compose -f docker-compose.dev.yml up -d

docker-prod:
	docker-compose up -d

docker-down:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

docker-logs:
	docker-compose logs -f

docker-logs-api:
	docker-compose logs -f api

docker-clean:
	docker system prune -f
	docker volume prune -f

# Production deployment commands
deploy-staging:
	docker-compose -f docker-compose.staging.yml up -d

deploy-production:
	docker-compose -f docker-compose.yml up -d --build

# Monitoring commands
monitor-up:
	docker-compose --profile monitoring up -d

monitor-down:
	docker-compose --profile monitoring down

# Backup commands
backup:
	docker-compose --profile backup run --rm db-backup

restore:
	@read -p "Enter backup file path: " backup_file; \
	docker exec -i amazon-product-db psql -U postgres -d amazon_product_db < $$backup_file

# Utility commands
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

logs:
	tail -f logs/app.log

setup-env:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"

ssl-cert:
	mkdir -p ssl
	openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# CI/CD commands
ci-test:
	pytest app/tests/ -v --cov=app --cov-report=xml

ci-lint:
	ruff check app/
	mypy app/
	bandit -r app/ -f json -o bandit-report.json

ci-security:
	safety check --json --output safety-report.json

# Performance testing
perf-test:
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

# API documentation
docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

# Database seeding
seed-db:
	python scripts/seed_database.py

# Health checks
health-check:
	curl -f http://localhost:8000/health || exit 1

health-check-docker:
	docker exec amazon-product-api curl -f http://localhost:8000/health || exit 1