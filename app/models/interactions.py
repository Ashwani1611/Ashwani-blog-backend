from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


# ── Comments ─────────────────────────────────────────────────

class Comment(Base):
    __tablename__ = "comments"

    id          = Column(Integer, primary_key=True, index=True)
    post_id     = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id   = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    guest_name  = Column(String(64), nullable=True)
    guest_email = Column(String(255), nullable=True)
    body        = Column(Text, nullable=False)
    ai_reply    = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow)

    # relationships
    post   = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")
    likes  = relationship("CommentLike", back_populates="comment",
                          cascade="all, delete-orphan", lazy="select")

    @property
    def like_count(self):
        return len(self.likes)

    @property
    def display_name(self):
        if self.author:
            return self.author.username
        return self.guest_name or "Anonymous"


# ── Post Likes ────────────────────────────────────────────────

class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_like"),
        UniqueConstraint("post_id", "ip_address", name="uq_post_like_ip"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")


# ── Comment Likes ─────────────────────────────────────────────

class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_like"),
        UniqueConstraint("comment_id", "ip_address", name="uq_comment_like_ip"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    comment = relationship("Comment", back_populates="likes")
    user    = relationship("User", back_populates="comment_likes")


# ── Newsletter ────────────────────────────────────────────────

class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    is_active       = Column(Boolean, default=True)
    subscribed_at   = Column(DateTime(timezone=True), default=utcnow)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)