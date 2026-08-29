"""
FastAPI Server Entry Point for GrowthPilot
Initializes Database, Supabase RLS, Redis Event Worker, and mounts APIs.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.db.models import init_db
from backend.app.db.database import setup_supabase_rls
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.agents.orchestrator import run_full_pipeline
from backend.app.integrations.redis_client import start_redis_worker
from backend.app.api.routes import router as api_router

app = FastAPI(
    title="GrowthPilot - AI Commerce Growth Agent",
    description="Autonomous multi-agent system closing the loop between e-commerce analytics, Razorpay, Supabase, and Redis.",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Mount frontend directory if built static files exist
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup():
    """Initializes database, Supabase RLS, seeds data, starts Redis background worker, and runs initial pipeline."""
    print("Initializing GrowthPilot Backend (Phase 2: Supabase + Redis + Razorpay)...")
    init_db()
    setup_supabase_rls()
    seed_database(force=False)
    start_redis_worker()
    run_full_pipeline()
    print("GrowthPilot Backend startup complete. Pipeline & Redis worker ready.")


@app.get("/")
def read_root():
    """Serves main dashboard UI HTML or root API info."""
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {
        "service": "GrowthPilot (AI Commerce Growth Agent)",
        "phase": "Phase 2: Supabase Postgres + Redis + Razorpay",
        "status": "online",
        "docs_url": "/docs",
        "api_overview": "/api/overview"
    }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
