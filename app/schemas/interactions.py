from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime


# ── Comments ──────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: str
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Comment body cannot be empty")
        if len(v) > 2000:
            raise ValueError("Comment must be under 2000 characters")
        return v


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


# ── Likes ─────────────────────────────────────────────────────

class LikeOut(BaseModel):
    liked: bool
    like_count: int


# ── Newsletter ────────────────────────────────────────────────

class NewsletterSubscribe(BaseModel):
    email: EmailStr


class NewsletterOut(BaseModel):
    message: str
    email: str


# ── AI Chat ───────────────────────────────────────────────────

class AIChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    post_id: Optional[int] = None
    messages: list[AIChatMessage]

    @field_validator("messages")
    @classmethod
    def limit_messages(cls, v):
        if not v:
            raise ValueError("Messages list cannot be empty")
        if len(v) > 20:
            raise ValueError("Maximum 20 messages per request")
        return v


class AIChatOut(BaseModel):
    reply: str
    model: str