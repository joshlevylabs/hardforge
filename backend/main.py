"""HardForge Backend — FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import intent, feasibility, design, export, library, auth, conversation
from backend.middleware.rate_limit import RateLimitMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Load seed data on startup
    from engine.ts_database import DriverDatabase
    db = DriverDatabase()
    app.state.driver_db = db
    from backend.conversation.session_store import SQLiteSessionStore
    store = SQLiteSessionStore()
    app.state.session_store = store
    from backend.database import init_db
    init_db()
    yield


app = FastAPI(
    title="HardForge API",
    description="AI-powered hardware design assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins
_frontend_url = os.getenv("FRONTEND_URL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url] if _frontend_url else [],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — 60 req/min general, 10 req/min for AI routes
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, ai_requests_per_minute=10)

# Register route modules
app.include_router(intent.router, prefix="/api", tags=["AI Pipeline"])
app.include_router(feasibility.router, prefix="/api", tags=["AI Pipeline"])
app.include_router(design.router, prefix="/api", tags=["Design"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(library.router, prefix="/api", tags=["Library"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(conversation.router, prefix="/api", tags=["Conversation"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "hardforge-backend"}
