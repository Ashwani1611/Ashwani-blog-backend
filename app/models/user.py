from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(64), unique=True, index=True, nullable=False)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    password   = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True)
    is_admin   = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # relationships
    comments      = relationship("Comment", back_populates="author", lazy="select", foreign_keys="Comment.author_id")
    likes         = relationship("PostLike", back_populates="user", lazy="select")
    comment_likes = relationship("CommentLike", back_populates="user", lazy="select")