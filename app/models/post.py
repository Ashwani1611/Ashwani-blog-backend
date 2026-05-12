from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "posts"

    id           = Column(Integer, primary_key=True, index=True)
    slug         = Column(String(128), unique=True, index=True, nullable=False)
    title        = Column(String(255), nullable=False)
    excerpt      = Column(Text, nullable=False)
    body         = Column(Text, nullable=False)
    content      = Column(Text, nullable=False)
    cat          = Column(String(32), nullable=False)
    layout       = Column(String(16), default="half")
    tags         = Column(JSON, default=list)
    toc          = Column(JSON, default=list)
    date_str     = Column(String(32), nullable=False)
    read_time    = Column(String(32), default="5 min read")
    cover_image  = Column(String(500), nullable=True)
    is_featured  = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)
    view_count   = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # relationships
    comments = relationship("Comment", back_populates="post",
                            cascade="all, delete-orphan", lazy="select")
    likes    = relationship("PostLike", back_populates="post",
                            cascade="all, delete-orphan", lazy="select")

    @property
    def like_count(self):
        return len(self.likes)

    @property
    def comment_count(self):
        return len([c for c in self.comments if c.is_approved])