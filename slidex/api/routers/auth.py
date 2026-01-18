"""
Authentication router for Google SSO.
"""

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from slidex.config import settings
from slidex.core.auth_service import auth_service
from slidex.core.deps import get_current_user, get_current_user_optional
from slidex.logging_config import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Authlib configuration
# We don't use the .env file directly here because we have settings
# But Starlette Config expects a file or environ.
# We will manually register the client.

oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
else:
    logger.warning("Google OAuth credentials not configured. SSO will not work.")


@router.get("/login")
async def login(request: Request):
    """Redirect to Google for authentication."""
    if not oauth.google:
        raise HTTPException(500, "Google OAuth not configured")
        
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    """Handle callback from Google."""
    if not oauth.google:
        raise HTTPException(500, "Google OAuth not configured")
        
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            # Try parsing id_token if userinfo not directly in token dict
            # Depending on authlib version/provider response
            user_info = token.get('id_token')
            
        if not user_info:
             raise ValueError("Could not retrieve user info")
             
        # Create or update user
        user = auth_service.create_or_update_user(user_info)
        
        # Create session
        session_id = auth_service.create_session(str(user['user_id']))
        
        # Determine redirect URL (could be stored in state, default to root for now)
        response = RedirectResponse(url="/")
        
        # Determine secure flag
        # Allow insecure cookies on localhost, 0.0.0.0, or if debug mode is on
        is_localhost = settings.server_host in ["localhost", "127.0.0.1", "0.0.0.0"]
        is_secure = not is_localhost and not settings.server_debug
        
        # Set cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=settings.session_expire_seconds,
            httponly=True,
            secure=is_secure,
            samesite="lax"
        )
        
        logger.info(f"Login successful for {user['email']}. Session ID set (secure={is_secure})")
        
        return response
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        # Return a friendly error page or JSON
        return JSONResponse(
            status_code=400,
            content={"error": "Authentication failed", "details": str(e)}
        )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    user: dict = Depends(get_current_user_optional)
):
    """Logout current user."""
    # Remove session from DB
    session_id = request.cookies.get("session_id")
    if session_id:
        auth_service.delete_session(session_id)
    
    # Clear cookie
    response.delete_cookie("session_id")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user
