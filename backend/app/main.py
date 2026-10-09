"""FastAPI application: wiring only — middleware, error mapping, routers, startup."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from .config import settings
from .db import SessionLocal, ensure_schema
from .routers import auth, course, dev, me, quests, sessions, shop, social
from .seed import seed_if_empty
from .services.errors import GameError


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    with SessionLocal() as db:
        seed_if_empty(db)  # the app is usable immediately after first boot
    yield


app = FastAPI(title="Duolingo Clone API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(GameError)
async def game_error(_: Request, exc: GameError):
    return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message})


@app.exception_handler(StaleDataError)
async def stale(_: Request, __: StaleDataError):
    # Optimistic-lock conflict: someone else updated this learner mid-request. Safe to retry.
    return JSONResponse(status_code=409, content={"error": "conflict", "message": "Please retry"})


@app.get("/api/health")
def health():
    return {"ok": True}


for r in (auth.router, me.router, course.router, sessions.router, social.router, shop.router, quests.router):
    app.include_router(r)
if settings.enable_dev_routes:
    app.include_router(dev.router)
