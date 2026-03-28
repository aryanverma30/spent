"""
FastAPI application entry point.

This file does three things:
  1. Defines the app lifespan (startup / shutdown logic)
  2. Creates the FastAPI app instance
  3. Registers all routers under the /api/v1 prefix

The lifespan context manager is the modern way (FastAPI 0.93+) to run
code on startup and shutdown. It replaces the deprecated @app.on_event().

To run the app locally (outside Docker):
    uvicorn app.main:app --reload

The Swagger UI is available at: http://localhost:8000/docs
The ReDoc UI is available at:   http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.db import engine

# Import routers
from app.routes import transactions, summary, trends, insights


# ── Lifespan ──────────────────────────────────────────────────────────────────
# Code before `yield` runs on startup; code after `yield` runs on shutdown.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    print(f"Starting Spent API in {settings.environment} mode")
    yield
    # Shutdown — dispose the connection pool cleanly
    await engine.dispose()
    print("Database connection pool closed")


# ── App Instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Spent API",
    description="Personal budget tracker — log expenses, get AI categorization, visualize spending.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
# Allows the Scriptable widget (and any future web UI) to call the API
# from a different origin. Adjust `allow_origins` before going to production.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # TODO (production): restrict to your widget's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Router Registration ───────────────────────────────────────────────────────
# All routes are grouped under /api/v1 so we can version the API later.
#
# TODO: Register all four routers below.
# Each router is imported above. Use app.include_router() like this:
#
#   app.include_router(transactions.router, prefix="/api/v1")
#   app.include_router(summary.router,      prefix="/api/v1")
#   app.include_router(trends.router,       prefix="/api/v1")
#   app.include_router(insights.router,     prefix="/api/v1")
#
# After registering, your endpoints will be available at:
#   POST /api/v1/transactions
#   GET  /api/v1/transactions
#   GET  /api/v1/summary
#   GET  /api/v1/trends
#   GET  /api/v1/insights


# ── Health Check ──────────────────────────────────────────────────────────────
# A simple endpoint to confirm the app is running. Useful for Docker healthchecks.

@app.get("/health", tags=["meta"])
async def health_check():
    """Return a 200 OK when the API is running."""
    return {"status": "ok", "environment": settings.environment}
