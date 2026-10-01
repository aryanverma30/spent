"""FastAPI application entry point with lifespan, middleware, and router registration."""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import ai, budgets, categories, charts, dashboard, insights, summary, transactions
from app.services.auth import require_api_token
from app.services.db import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    logger.info("[Spent] Starting in %s mode", settings.environment)
    yield
    await engine.dispose()
    logger.info("[Spent] Engine disposed, shutting down")


app = FastAPI(
    title="Spent API",
    description="Personal spending tracker — log expenses via Telegram, visualize with charts.",
    version="1.0.0",
    lifespan=lifespan,
)

# allow_origins=["*"] is intentional for a self-hosted, single-user deployment
# where the API is only reachable from the owner's own devices (Telegram bot,
# iOS widget, local browser).  If this app were ever exposed as a multi-tenant
# service or consumed by a third-party frontend, replace "*" with an explicit
# list of trusted origins (e.g. ["https://yourapp.example.com"]).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every /api/v1 route requires the bearer token (see services/auth.py).
_api_auth = [Depends(require_api_token)]

# Core CRUD
app.include_router(transactions.router, prefix="/api/v1", dependencies=_api_auth)

# Analytics
app.include_router(summary.router, prefix="/api/v1", dependencies=_api_auth)
app.include_router(insights.router, prefix="/api/v1", dependencies=_api_auth)
app.include_router(categories.router, prefix="/api/v1", dependencies=_api_auth)
app.include_router(budgets.router, prefix="/api/v1", dependencies=_api_auth)

# AI parsing
app.include_router(ai.router, prefix="/api/v1", dependencies=_api_auth)

# Charts (PNG images)
app.include_router(charts.router, prefix="/api/v1", dependencies=_api_auth)

# Web dashboard — served at / (no prefix, tapping widget opens this).
# The page itself holds no data; its API calls carry the token.
app.include_router(dashboard.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint for load balancers and uptime monitors."""
    return {"status": "ok", "environment": settings.environment}
