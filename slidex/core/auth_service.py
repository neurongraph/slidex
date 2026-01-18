"""
Authentication service for Google SSO and session management.
"""

import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

import psycopg2
from psycopg2.extras import RealDictCursor

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import get_db_connection

class AuthService:
    """Service for handling users and sessions."""

    @staticmethod
    def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by Google ID."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM users WHERE google_id = %s",
                (google_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by User ID."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    @staticmethod
    def create_or_update_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user or update existing one from Google info.
        user_info is expected to come from Google OIDC.
        """
        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not google_id or not email:
            raise ValueError("Invalid user info: missing google_id or email")

        existing_user = AuthService.get_user_by_google_id(google_id)

        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if existing_user:
                # Update existing user
                cur.execute(
                    """
                    UPDATE users 
                    SET email = %s, name = %s, picture = %s, updated_at = NOW()
                    WHERE google_id = %s
                    RETURNING *
                    """,
                    (email, name, picture, google_id)
                )
                logger.debug(f"Updated user: {email}")
            else:
                # Create new user
                cur.execute(
                    """
                    INSERT INTO users (google_id, email, name, picture)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (google_id, email, name, picture)
                )
                logger.info(f"Created new user: {email}")
            
            result = cur.fetchone()
            return dict(result)

    @staticmethod
    def create_session(user_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session for the user.
        Returns the session_id (token).
        """
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=settings.session_expire_seconds)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sessions (session_id, user_id, data, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (session_id, user_id, psycopg2.extras.Json(data or {}), expires_at)
            )
        
        return session_id

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a valid session.
        Returns session dict if found and not expired, else None.
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT s.*, u.email, u.name, u.picture 
                FROM sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = %s AND s.expires_at > NOW()
                """,
                (session_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

    @staticmethod
    def delete_session(session_id: str) -> None:
        """Invalidate a session."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM sessions WHERE session_id = %s",
                (session_id,)
            )

    @staticmethod
    def cleanup_expired_sessions() -> None:
        """Remove expired sessions from database."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE expires_at < NOW()")


# Global auth service instance
auth_service = AuthService()
