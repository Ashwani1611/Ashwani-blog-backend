from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_optional_user
from app.core.utils import get_client_ip
from app.models.post import Post
from app.models.interactions import PostLike
from app.schemas.interactions import LikeOut

router = APIRouter(prefix="/posts", tags=["Likes"])


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

    ip = get_client_ip(request)

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
        post.like_count = max(0, post.like_count - 1)
        db.commit()
        return LikeOut(liked=False, like_count=post.like_count)

    like = PostLike(
        post_id=post.id,
        user_id=current_user.id if current_user else None,
        ip_address=None if current_user else ip,
    )
    db.add(like)
    post.like_count += 1
    db.commit()
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

    ip = get_client_ip(request)

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