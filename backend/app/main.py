"""FastAPI application entry point with lifespan, middleware, and router registration."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.db import engine
from app.routes import transactions, summary, trends, insights, ai, charts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    print(f"[Spent] Starting in {settings.environment} mode")
    yield
    await engine.dispose()
    print("[Spent] Engine disposed, shutting down")


app = FastAPI(
    title="Spent API",
    description="Personal spending tracker — log expenses via Telegram, visualize with charts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to known origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core CRUD
app.include_router(transactions.router, prefix="/api/v1")

# Analytics
app.include_router(summary.router, prefix="/api/v1")
app.include_router(trends.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")

# AI parsing
app.include_router(ai.router, prefix="/api/v1")

# Charts (PNG images)
app.include_router(charts.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint for load balancers and uptime monitors."""
    return {"status": "ok", "environment": settings.environment}
