from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_optional_user
from app.models.post import Post
from app.models.interactions import PostLike
from app.schemas.interactions import LikeOut

router = APIRouter(prefix="/posts", tags=["Likes"])


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


@router.post("/{slug}/like", response_model=LikeOut)
def toggle_post_like(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()
    if not post:
        raise HTTPException(404, "Post not found")

    ip = _get_ip(request)

    if current_user:
        existing = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id,
        ).first()
    else:
        existing = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.ip_address == ip,
        ).first()

    if existing:
        db.delete(existing)
        db.commit()
        db.refresh(post)
        return LikeOut(liked=False, like_count=post.like_count)

    like = PostLike(
        post_id=post.id,
        user_id=current_user.id if current_user else None,
        ip_address=None if current_user else ip,
    )
    db.add(like)
    db.commit()
    db.refresh(post)
    return LikeOut(liked=True, like_count=post.like_count)


@router.get("/{slug}/like", response_model=LikeOut)
def get_post_like_status(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()
    if not post:
        raise HTTPException(404, "Post not found")

    ip = _get_ip(request)

    if current_user:
        liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id,
        ).first() is not None
    else:
        liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.ip_address == ip,
        ).first() is not None

    return LikeOut(liked=liked, like_count=post.like_count)