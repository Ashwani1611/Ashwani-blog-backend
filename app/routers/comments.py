from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_optional_user, get_current_admin
from app.models.post import Post
from app.models.interactions import Comment, CommentLike
from app.schemas.interactions import CommentCreate, CommentOut
from app.services.gemini import generate_comment_reply

router = APIRouter(tags=["Comments"])


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


async def _add_ai_reply(comment_id: int, post_title: str, body: str, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    Session = sessionmaker(bind=engine)
    with Session() as s:
        comment = s.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            try:
                reply = await generate_comment_reply(body, post_title)
                comment.ai_reply = reply
                s.commit()
            except Exception:
                pass


# ── Per-post endpoints ────────────────────────────────────────

@router.get("/posts/{slug}/comments", response_model=list[CommentOut])
def list_comments(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    request: Request = None,
):
    post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()
    if not post:
        raise HTTPException(404, "Post not found")

    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post.id, Comment.is_approved == True)
        .order_by(Comment.created_at.asc())
        .all()
    )

    ip = _get_ip(request) if request else None
    result = []
    for c in comments:
        data = CommentOut.model_validate(c)
        if current_user:
            data.user_liked = db.query(CommentLike).filter(
                CommentLike.comment_id == c.id,
                CommentLike.user_id == current_user.id,
            ).first() is not None
        elif ip:
            data.user_liked = db.query(CommentLike).filter(
                CommentLike.comment_id == c.id,
                CommentLike.ip_address == ip,
            ).first() is not None
        result.append(data)
    return result


@router.post("/posts/{slug}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    slug: str,
    payload: CommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()
    if not post:
        raise HTTPException(404, "Post not found")

    if not current_user and not payload.guest_name:
        raise HTTPException(422, "guest_name is required when not authenticated")

    comment = Comment(
        post_id=post.id,
        author_id=current_user.id if current_user else None,
        guest_name=payload.guest_name,
        guest_email=str(payload.guest_email) if payload.guest_email else None,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    from app.core.config import get_settings
    background_tasks.add_task(
        _add_ai_reply,
        comment.id,
        post.title,
        payload.body,
        get_settings().database_url,
    )

    return CommentOut.model_validate(comment)


# ── Comment likes ─────────────────────────────────────────────

@router.post("/comments/{comment_id}/like", response_model=dict)
def toggle_comment_like(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(404, "Comment not found")

    ip = _get_ip(request)

    if current_user:
        existing = db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == current_user.id,
        ).first()
    else:
        existing = db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id,
            CommentLike.ip_address == ip,
        ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"liked": False, "like_count": comment.like_count - 1}
    else:
        like = CommentLike(
            comment_id=comment_id,
            user_id=current_user.id if current_user else None,
            ip_address=None if current_user else ip,
        )
        db.add(like)
        db.commit()
        db.refresh(comment)
        return {"liked": True, "like_count": comment.like_count}


# ── Admin ─────────────────────────────────────────────────────

@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(404, "Comment not found")
    db.delete(comment)
    db.commit()