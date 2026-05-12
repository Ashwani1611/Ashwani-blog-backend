from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.interactions import NewsletterSubscriber
from app.schemas.interactions import NewsletterSubscribe, NewsletterOut

router = APIRouter(prefix="/newsletter", tags=["Newsletter"])


@router.post("/subscribe", response_model=NewsletterOut)
def subscribe(payload: NewsletterSubscribe, db: Session = Depends(get_db)):
    existing = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.email == str(payload.email)
    ).first()

    if existing:
        if existing.is_active:
            raise HTTPException(400, "Email already subscribed")
        # Re-activate unsubscribed email
        existing.is_active = True
        existing.unsubscribed_at = None
        db.commit()
        return NewsletterOut(message="Welcome back! Re-subscribed successfully.", email=str(payload.email))

    subscriber = NewsletterSubscriber(email=str(payload.email))
    db.add(subscriber)
    db.commit()
    return NewsletterOut(message="Subscribed successfully!", email=str(payload.email))


@router.post("/unsubscribe", response_model=NewsletterOut)
def unsubscribe(payload: NewsletterSubscribe, db: Session = Depends(get_db)):
    subscriber = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.email == str(payload.email),
        NewsletterSubscriber.is_active == True,
    ).first()

    if not subscriber:
        raise HTTPException(404, "Email not found in subscriber list")

    subscriber.is_active = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()
    return NewsletterOut(message="Unsubscribed successfully.", email=str(payload.email))


# ── Admin only ────────────────────────────────────────────────────────────────

@router.get("/subscribers", tags=["Admin"])
def list_subscribers(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    subscribers = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.is_active == True
    ).all()
    return {
        "count": len(subscribers),
        "subscribers": [{"email": s.email, "subscribed_at": s.subscribed_at} for s in subscribers],
    }