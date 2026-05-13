from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.post import Post
from app.schemas.interactions import AIChatRequest, AIChatOut
from app.services import gemini

router = APIRouter(prefix="/ai", tags=["AI Chat"])
settings = get_settings()


@router.post("/chat", response_model=AIChatOut)
async def blog_chat(payload: AIChatRequest, db: Session = Depends(get_db)):
    """Blog-wide AI chat — answers questions about any post."""
    if not settings.gemini_api_key:
        raise HTTPException(503, "AI service not configured — set GEMINI_API_KEY in .env")

    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    if payload.post_id:
        post = db.query(Post).filter(
            Post.id == payload.post_id,
            Post.is_published == True,
        ).first()
        if not post:
            raise HTTPException(404, "Post not found")
        reply = await gemini.post_chat(messages, post.title, post.content)
    else:
        # Load only title + excerpt — not full content
        posts = db.query(Post.id, Post.title, Post.excerpt).filter(
            Post.is_published == True
        ).all()
        reply = await gemini.blog_chat(messages, posts)

    return AIChatOut(reply=reply, model=settings.gemini_model)


@router.post("/post/{slug}/chat", response_model=AIChatOut)
async def post_chat(
    slug: str,
    payload: AIChatRequest,
    db: Session = Depends(get_db),
):
    """Convenience endpoint — chat scoped to a post by slug."""
    if not settings.gemini_api_key:
        raise HTTPException(503, "AI service not configured — set GEMINI_API_KEY in .env")

    post = db.query(Post).filter(
        Post.slug == slug,
        Post.is_published == True,
    ).first()
    if not post:
        raise HTTPException(404, "Post not found")

    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    reply = await gemini.post_chat(messages, post.title, post.content)
    return AIChatOut(reply=reply, model=settings.gemini_model)