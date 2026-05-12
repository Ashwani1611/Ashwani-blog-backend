from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Comments ──────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: str
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    body: str
    ai_reply: Optional[str]
    display_name: str
    like_count: int
    is_approved: bool
    created_at: datetime
    user_liked: bool = False

    model_config = {"from_attributes": True}


# ── Likes ──────────────────────────────────────────────────────

class LikeOut(BaseModel):
    liked: bool
    like_count: int


# ── Newsletter ─────────────────────────────────────────────────

class NewsletterSubscribe(BaseModel):
    email: EmailStr


class NewsletterOut(BaseModel):
    message: str
    email: str


# ── AI Chat ────────────────────────────────────────────────────

class AIChatMessage(BaseModel):
    role: str
    content: str


class AIChatRequest(BaseModel):
    post_id: Optional[int] = None
    messages: list[AIChatMessage]


class AIChatOut(BaseModel):
    reply: str
    model: str