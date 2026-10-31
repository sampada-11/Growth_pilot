"""
FastAPI Server Entry Point for GrowthPilot
Initializes Database, Supabase RLS, Redis Event Worker, and mounts APIs.
"""
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.app.db.models import init_db
from backend.app.db.database import setup_supabase_rls
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.agents.orchestrator import run_full_pipeline
from backend.app.integrations.redis_client import start_redis_worker
from backend.app.api.routes import router as api_router
from backend.app.api.analytics_routes import router as analytics_router
from backend.app.api.agent_routes import router as agent_router
from backend.app.api.opportunity_routes import router as opportunity_router
from backend.app.api.campaign_routes import router as campaign_router
from backend.app.api.experiment_routes import router as experiment_router
from backend.app.api.copilot_routes import router as copilot_router
from backend.app.api.customer_routes import router as customer_router
from backend.app.api.product_routes import router as product_router

app = FastAPI(
    title="GrowthPilot - AI Commerce Growth Agent",
    description="Autonomous multi-agent system closing the loop between e-commerce analytics, Razorpay, Supabase, and Redis.",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers (Preserving /api routes + adding versioned /api/v1/* routes)
app.include_router(api_router)
app.include_router(analytics_router)
app.include_router(agent_router)
app.include_router(opportunity_router)
app.include_router(campaign_router)
app.include_router(experiment_router)
app.include_router(copilot_router)
app.include_router(customer_router)
app.include_router(product_router)

# Mount frontend directory for static assets (CSS, JS, images etc.)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup():
    """Initializes database, Supabase RLS, seeds data, starts Redis background worker, and runs initial pipeline."""
    print("Initializing GrowthPilot Backend (Phase 3: Auth Hardened + Login Page)...")
    init_db()
    setup_supabase_rls()
    seed_database(force=False)
    start_redis_worker()
    run_full_pipeline()
    print("GrowthPilot Backend startup complete. Pipeline & Redis worker ready.")


@app.get("/login")
def serve_login():
    """Serves the GrowthPilot admin login page."""
    html_path = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return RedirectResponse(url="/")


@app.get("/")
def read_root(request: Request):
    """Serves main dashboard UI. Dashboard JS validates sessionStorage auth token."""
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {
        "service": "GrowthPilot (AI Commerce Growth Agent)",
        "phase": "Phase 3: Auth Hardened + Login Page",
        "status": "online",
        "login": "/login",
        "docs_url": "/docs",
        "api_overview": "/api/overview"
    }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
