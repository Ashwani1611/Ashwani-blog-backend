from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import Base, engine

# Import all models so SQLAlchemy registers them before create_all
from app.models import user, post, interactions  # noqa: F401

from app.routers import auth, posts, comments, likes, newsletter, ai

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (dev convenience — use Alembic in prod)
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

# ── CORS ─────────────────────────────────────────────────────────────────────
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
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}