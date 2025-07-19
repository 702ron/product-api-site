# FastAPI Production Patterns for Credit-Based API Platforms

## Project Structure (2025 Best Practices)

```
app/
├── main.py                    # Entry point with CORS, middleware
├── api/
│   ├── v1/                   # API versioning
│   │   └── endpoints/
│   │       ├── auth.py       # Supabase JWT auth
│   │       ├── credits.py    # Credit management
│   │       ├── products.py   # ASIN product data
│   │       ├── conversion.py # FNSKU conversion
│   │       └── payments.py   # Stripe webhook handling
│   └── deps.py              # FastAPI dependencies
├── core/
│   ├── config.py            # Pydantic settings
│   ├── security.py          # JWT verification
│   └── database.py          # Async SQLAlchemy setup
├── models/                  # Database models
├── schemas/                 # Pydantic request/response models
├── services/               # Business logic
│   ├── credit_service.py   # Credit deduction logic
│   ├── amazon_service.py   # External API calls
│   └── payment_service.py  # Stripe integration
├── crud/                   # Database operations
└── tests/                  # Test files
```

## Key Dependencies

```toml
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
supabase = "^2.3.0"
stripe = "^7.8.0"
httpx = "^0.25.0"
redis = "^5.0.0"
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
pydantic = "^2.5.0"
python-jose = "^3.3.0"
slowapi = "^0.1.9"
```

## Authentication Pattern

```python
# core/security.py
async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, "Invalid authentication")
        return user_id
    except JWTError:
        raise HTTPException(401, "Invalid authentication")

# Usage in endpoints
@router.get("/credits")
async def get_user_credits(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await credit_service.get_balance(db, user_id)
```

## Error Handling Patterns

```python
# Custom exceptions
class InsufficientCreditsError(Exception):
    pass

class ExternalAPIError(Exception):
    pass

# Global exception handler
@app.exception_handler(InsufficientCreditsError)
async def insufficient_credits_handler(request, exc):
    return JSONResponse(
        status_code=402,
        content={"error": "insufficient_credits", "message": str(exc)}
    )
```

## Async Database Pattern

```python
# core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)

async def get_db():
    async with AsyncSession(engine) as session:
        try:
            yield session
        finally:
            await session.close()
```

## Rate Limiting Implementation

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/product/asin")
@limiter.limit("100/minute")
async def get_product_data(
    request: Request,
    asin: str,
    user_id: str = Depends(get_current_user)
):
    # Implementation
    pass
```

## Critical Gotchas

- **Async/Await**: Use async functions for all I/O operations
- **Connection Pooling**: Always configure proper pool sizes
- **JWT Validation**: Verify tokens on every protected endpoint
- **Error Handling**: Never catch all exceptions - be specific
- **Rate Limiting**: Implement both global and user-specific limits
- **Logging**: Use structured logging, never print statements
- **Type Hints**: Required on all functions for mypy compliance