"""HardForge Backend — FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import intent, feasibility, design, export, library, auth, conversation

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Load seed data on startup
    from engine.ts_database import DriverDatabase
    db = DriverDatabase()
    app.state.driver_db = db
    from backend.conversation.session_store import InMemorySessionStore
    store = InMemorySessionStore()
    app.state.session_store = store
    yield


app = FastAPI(
    title="HardForge API",
    description="AI-powered hardware design assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
