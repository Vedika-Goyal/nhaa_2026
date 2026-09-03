import sys
from pathlib import Path

# Add root repository directory to sys.path for perception & API modules
repo_root = str(Path(__file__).resolve().parent.parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes.cases import router as cases_router
from app.routes.risk_assessments import router as ra_router
from app.routes.websocket import router as ws_router
from app.routes.stats import router as stats_router
from app.routes.notifications import router as notifications_router
from app.routes.telephony import router as telephony_router
from app.routes.demo_ui import router as demo_ui_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import AsyncSessionLocal, engine, Base
    import app.models  # noqa: F401 — ensure all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


app = FastAPI(
    title="NHAA Central Case API",
    description=(
        "Single shared PostgreSQL-backed API for the NHAA (14566) Helpline AI Triage System.\n\n"
        "**Channels:** Portal, Chatbot, IVRS, Mobile App\n\n"
        "Every complaint lands in the SAME central case database and goes through the SAME AI pipeline.\n"
        "This is the foundation of the project -- do not bypass these endpoints."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.include_router(cases_router, prefix="/api")
app.include_router(ra_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(telephony_router, prefix="/api/v1")
app.include_router(demo_ui_router)
app.include_router(ws_router)

# Register Vedika's AI Perception Layer Routers
try:
    from api.routes.perception_routes import router as perception_router
    from api.routes.analytics_routes import router as perception_analytics_router
    app.include_router(perception_router)
    app.include_router(perception_analytics_router)
except Exception as p_err:
    print(f"[NHAA App WARNING] Perception routers optional registration notice: {p_err}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nhaa-case-api"}


@app.get("/upload-test")
async def upload_test():
    try:
        from api.routes.perception_routes import upload_test_page
        return await upload_test_page()
    except Exception as e:
        return {"error": f"Upload test page unavailable: {e}"}


@app.get("/")
async def root():
    return {"service": "NHAA Central Case API", "docs": "/docs", "upload_test": "/upload-test"}
