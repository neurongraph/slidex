import pytest
from fastapi.testclient import TestClient
from slidex.api.app import app

client = TestClient(app)

def test_web_route_redirects_to_login():
    """Verify that root and other web routes redirect to /auth/login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/auth/login"

    response = client.get("/decks", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/auth/login"

def test_api_route_returns_401():
    """Verify that API routes return 401 Unauthorized."""
    response = client.get("/api/decks")
    assert response.status_code == 401
    assert response.json() == {"error": "Not authenticated", "detail": "Authentication required"}

def test_exempt_routes():
    """Verify that exempt routes are still accessible."""
    # Health check should be 200
    response = client.get("/health")
    assert response.status_code == 200
    
    # Auth login should be accessible (redirects to Google)
    response = client.get("/auth/login", follow_redirects=False)
    # Authlib might return a 302 or similar for the Google redirect
    assert response.status_code in [200, 302, 303, 307]

    # Favicon check (it might not exist, but it shouldn't be redirected)
    response = client.get("/favicon.ico", follow_redirects=False)
    assert response.status_code != 307 or response.headers.get("location") != "/auth/login"
