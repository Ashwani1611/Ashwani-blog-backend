from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import get_settings
from app.core.database import Base, engine

from app.models import user, post, interactions  # noqa: F401

from app.routers import auth, posts, comments, likes, newsletter, ai

settings = get_settings()

frontend_dir = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Backend API for Ashwani Kumar's developer blog. Powered by FastAPI + PostgreSQL + Gemini 1.5.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,       prefix="/api/v1")
app.include_router(posts.router,      prefix="/api/v1")
app.include_router(comments.router,   prefix="/api/v1")
app.include_router(likes.router,      prefix="/api/v1")
app.include_router(newsletter.router, prefix="/api/v1")
app.include_router(ai.router,         prefix="/api/v1")

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

# ── Frontend ──────────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(frontend_dir / "index.html")

@app.get("/{page:path}")
async def serve_page(page: str):
    # Guard: never intercept API or docs routes
    if page.startswith(("api/", "docs", "redoc", "health", "openapi")):
        raise HTTPException(status_code=404)

    file = frontend_dir / page
    if file.exists():
        return FileResponse(file)
    return FileResponse(frontend_dir / "index.html")