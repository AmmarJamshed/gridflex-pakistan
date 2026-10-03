"""GRIDFLEX Pakistan FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        f"{settings.app_subtitle}\n\n"
        "Research/prototype electricity flexibility marketplace for Pakistan. "
        "Simulated prices and illustrative grid model — not an operational market."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Allow exact origins plus common public hosts (Vercel / Netlify)
_cors_origins = [o for o in settings.cors_origin_list if "*" not in o]
for _extra in (
    "https://gridflex-pakistan.netlify.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
):
    if _extra not in _cors_origins:
        _cors_origins.append(_extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.(vercel\.app|netlify\.app|ngrok-free\.app|ngrok\.io)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "subtitle": settings.app_subtitle,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gridflex-pakistan"}