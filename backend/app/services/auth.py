"""Bearer-token authentication for the /api/v1 routes."""
import secrets

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


async def require_api_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """Reject requests that don't carry the configured API token.

    With no API_TOKEN configured, requests are allowed in development (so local
    dev and tests work without setup) and refused in production (fail closed).
    """
    if not settings.api_token:
        if settings.is_development:
            return
        raise HTTPException(status_code=503, detail="API_TOKEN is not configured on the server")

    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), settings.api_token.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
