from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import *  # noqa: F401,F403
from app.services.bootstrap import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("APP")
settings = get_settings()

app = FastAPI(title="Lumina Stars API", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins == ["*"] else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_mw(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.exception_handler(AppError)
async def app_error_handler(_, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def unhandled(_, exc: Exception):
    log.exception("unhandled")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL", "message": "Внутренняя ошибка"}},
    )


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    log.info("Lumina started demo_mode=%s env=%s", settings.demo_mode, settings.app_env)


@app.get("/api/health")
def health():
    return {"success": True, "data": {"ok": True, "demo_mode": settings.demo_mode, "name": settings.app_name}}


app.include_router(api_router, prefix="/api/v1")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"success": False, "error": {"code": "NOT_FOUND", "message": "Not found"}}, 404)
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"success": False, "error": {"code": "NO_FRONTEND", "message": "Frontend is not built"}}, 404)
