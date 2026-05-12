from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_admin, get_optional_user
from app.models.post import Post
from app.models.interactions import PostLike
from app.schemas.post import PostCreate, PostUpdate, PostOut, PostListOut

router = APIRouter(prefix="/posts", tags=["Posts"])


# ── Helpers ───────────────────────────────────────────────────

def _post_or_404(db: Session, slug: str) -> Post:
    post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()
    if not post:
        raise HTTPException(404, "Post not found")
    return post


def _get_liked_post_ids(post_ids: list[int], user_id: int, db: Session) -> set[int]:
    """Single query to get all post IDs liked by the user — avoids N+1."""
    rows = db.query(PostLike.post_id).filter(
        PostLike.post_id.in_(post_ids),
        PostLike.user_id == user_id,
    ).all()
    return {row.post_id for row in rows}


def _is_bot(request: Request) -> bool:
    ua = request.headers.get("user-agent", "").lower()
    return any(bot in ua for bot in ["bot", "crawler", "spider", "wget", "curl"])


# ── Public ────────────────────────────────────────────────────

@router.get("/", response_model=list[PostListOut])
def list_posts(
    cat: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    q = db.query(Post).filter(Post.is_published == True)

    if cat:
        q = q.filter(Post.cat == cat)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            Post.title.ilike(term) |
            Post.excerpt.ilike(term) |
            Post.content.ilike(term)
        )

    posts = q.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()

    # Single query for all liked post IDs — no N+1
    liked_ids: set[int] = set()
    if current_user and posts:
        liked_ids = _get_liked_post_ids([p.id for p in posts], current_user.id, db)

    result = []
    for p in posts:
        data = PostListOut.model_validate(p)
        data.user_liked = p.id in liked_ids
        result.append(data)
    return result


@router.get("/{slug}", response_model=PostOut)
def get_post(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    post = _post_or_404(db, slug)

    # Increment view count — skip bots
    if not _is_bot(request):
        post.view_count = (post.view_count or 0) + 1
        db.commit()
        db.refresh(post)

    data = PostOut.model_validate(post)
    data.user_liked = False
    if current_user:
        data.user_liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id,
        ).first() is not None
    return data


# ── Admin CRUD ────────────────────────────────────────────────

@router.post("/", response_model=PostOut, status_code=201)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    if db.query(Post).filter(Post.slug == payload.slug).first():
        raise HTTPException(400, f"Slug '{payload.slug}' already exists")
    post = Post(**payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return PostOut.model_validate(post)


@router.patch("/{slug}", response_model=PostOut)
def update_post(
    slug: str,
    payload: PostUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    post = db.query(Post).filter(Post.slug == slug).first()
    if not post:
        raise HTTPException(404, "Post not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return PostOut.model_validate(post)


@router.delete("/{slug}", status_code=204)
def delete_post(
    slug: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    post = db.query(Post).filter(Post.slug == slug).first()
    if not post:
        raise HTTPException(404, "Post not found")
    db.delete(post)
    db.commit()