"""Reusable dependency functions for API routes"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import User
from app.core.security import verify_token
from app.core.logging import logger


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate the current authenticated user from Bearer token.
    
    This is a reusable dependency that can be applied to any route requiring authentication.
    
    Args:
        authorization: Authorization header (Bearer <token>)
        db: Database session
    
    Returns:
        User object if token is valid
    
    Raises:
        HTTPException: 401 if token is missing, invalid, or user not found
    """
    if not authorization:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid authorization header format: {authorization[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    # Verify token and extract user_id
    user_id = verify_token(token)
    if not user_id:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()
    
    if not user:
        logger.warning(f"User not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    logger.debug(f"User authenticated: {user.email}")
    return user
