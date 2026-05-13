from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_optional_user, get_current_admin
from app.core.utils import get_client_ip
from app.models.post import Post
from app.models.interactions import Comment, CommentLike
from app.schemas.interactions import CommentCreate, CommentOut
from app.services.gemini import generate_comment_reply

router = APIRouter(tags=["Comments"])


async def _add_ai_reply(comment_id: int, post_title: str, body: str):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            reply = await generate_comment_reply(body, post_title)
            comment.ai_reply = reply
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _get_liked_comment_ids(comment_ids: list[int], user_id: int, db: Session) -> set[int]:
    """Single query for all liked comment IDs — avoids N+1."""
    rows = db.query(CommentLike.comment_id).filter(
        CommentLike.comment_id.in_(comment_ids),
        CommentLike.user_id == user_id,
    ).all()
    return {row.comment_id for row in rows}


def _get_liked_comment_ids_by_ip(comment_ids: list[int], ip: str, db: Session) -> set[int]:
    rows = db.query(CommentLike.comment_id).filter(
        CommentLike.comment_id.in_(comment_ids),
        CommentLike.ip_address == ip,
    ).all()
    return {row.comment_id for row in rows}


# ── Per-post endpoints ────────────────────────────────────────

@router.get("/posts/{slug}/comments", response_model=list[CommentOut])
def list_comments(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
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

    comment_ids = [c.id for c in comments]
    liked_ids: set[int] = set()

    if current_user and comment_ids:
        liked_ids = _get_liked_comment_ids(comment_ids, current_user.id, db)
    elif comment_ids:
        ip = get_client_ip(request)
        liked_ids = _get_liked_comment_ids_by_ip(comment_ids, ip, db)

    result = []
    for c in comments:
        data = CommentOut.model_validate(c)
        data.user_liked = c.id in liked_ids
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

    # Update post comment count
    post.comment_count += 1

    db.commit()
    db.refresh(comment)

    background_tasks.add_task(_add_ai_reply, comment.id, post.title, payload.body)

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

    ip = get_client_ip(request)

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
        comment.like_count = max(0, comment.like_count - 1)
        db.commit()
        return {"liked": False, "like_count": comment.like_count}

    like = CommentLike(
        comment_id=comment_id,
        user_id=current_user.id if current_user else None,
        ip_address=None if current_user else ip,
    )
    db.add(like)
    comment.like_count += 1
    db.commit()
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

    # Update post comment count
    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if post:
        post.comment_count = max(0, post.comment_count - 1)

    db.delete(comment)
    db.commit()