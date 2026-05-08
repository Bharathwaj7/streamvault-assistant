from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.database import create_tables
from app.db.views import create_views
from app.services.ingestion import run_full_ingestion
from app.api.routes import auth, chat, analytics, ingest, feedback

settings = get_settings()
logger   = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("startup: creating database tables")
    await create_tables()

    logger.info("startup: creating security views")
    await create_views()

    logger.info("startup: running data ingestion")
    try:
        await run_full_ingestion()
        logger.info("startup: ingestion complete")
    except Exception as e:
        logger.error(f"startup: ingestion failed: {e}")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("shutdown: StreamVault assistant stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Secure AI-powered internal analytics assistant for StreamVault Entertainment.",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    duration = round(time.time() - start, 3)
    logger.info(
        "http_request",
        extra={
            "method":      request.method,
            "path":        request.url.path,
            "status_code": response.status_code,
            "duration_s":  duration,
        },
    )
    return response


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_error", extra={"path": request.url.path, "exc": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api")
app.include_router(chat.router,      prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ingest.router,    prefix="/api")
app.include_router(feedback.router,  prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}