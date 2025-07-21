"""
JWT authentication and security utilities.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.core.exceptions import (
    AuthenticationError, AuthorizationError, InsufficientCreditsError,
    ResourceNotFoundError
)

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


# Re-export for backward compatibility
class JWTError(AuthenticationError):
    """Custom JWT authentication error."""
    pass


class UserNotFoundError(ResourceNotFoundError):
    """Exception raised when user is not found."""
    
    def __init__(self, user_id: str = None, message: str = "User not found"):
        super().__init__(
            message=message,
            resource_type="user",
            resource_id=user_id
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return bcrypt.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise JWTError("Could not validate credentials")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Get current user ID from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        # Extract user ID - try both 'sub' (standard) and 'user_id' (custom)
        user_id: str = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user object from database.
    
    Args:
        user_id: User ID from token
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user not found
    """
    try:
        # Find user by ID directly (standard database authentication)
        # User ID is already a string in the database, no need to convert to UUID
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
    
    except Exception as e:
        # Handle MultipleResultsFound and other database errors
        if "Multiple rows were found" in str(e):
            logger.error(f"Multiple users found for ID {user_id} - database integrity issue")
            # Get the first active user as a fallback
            result = await db.execute(
                select(User)
                .where(User.id == user_id)
                .where(User.is_active == True)
                .limit(1)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
        
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error occurred"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Active user object
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


def verify_supabase_jwt(token: str) -> dict:
    """
    Verify Supabase JWT token specifically.
    
    Args:
        token: Supabase JWT token
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid Supabase token: {str(e)}")


def create_user_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create access token for a user.
    
    Args:
        user: User object
        expires_delta: Token expiration time
        
    Returns:
        JWT access token
    """
    token_data = {
        "sub": str(user.id),
        "user_id": str(user.id),
        "email": user.email,
    }
    return create_access_token(token_data, expires_delta)


async def verify_user_has_credits(
    user: User,
    required_credits: int
) -> bool:
    """
    Verify user has sufficient credits for an operation.
    
    Args:
        user: User object
        required_credits: Credits required for operation
        
    Returns:
        True if user has sufficient credits
        
    Raises:
        InsufficientCreditsError: If user lacks credits
    """
    if user.credit_balance < required_credits:
        raise InsufficientCreditsError(
            f"Operation requires {required_credits} credits, "
            f"but user has {user.credit_balance} credits"
        )
    return True