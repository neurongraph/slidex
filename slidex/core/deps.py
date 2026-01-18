"""
FastAPI dependencies for authentication.
"""

from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyCookie

from slidex.core.auth_service import auth_service
from slidex.logging_config import logger

# Cookie scheme to make Swagger UI happy (optional)
cookie_scheme = APIKeyCookie(name="session_id", auto_error=False)

async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session cookie.
    Returns None if not authenticated.
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
        
    session = auth_service.get_session(session_id)
    if not session:
        return None
        
    # Start returning user info
    # The session query joins with user table, so we have user details
    return {
        "user_id": str(session["user_id"]),
        "email": session["email"],
        "name": session["name"],
        "picture": session["picture"],
        "session_id": session_id
    }

async def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get current authenticated user or raise 401.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user
