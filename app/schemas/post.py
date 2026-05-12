from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    slug: str
    title: str
    excerpt: str
    body: str
    content: str
    cat: str
    layout: str = "half"
    tags: List[str] = []
    toc: List[str] = []
    date_str: str
    read_time: str = "5 min read"
    cover_image: Optional[str] = None
    is_featured: bool = False
    is_published: bool = True

    @field_validator("cat")
    @classmethod
    def cat_valid(cls, v):
        valid = {"django", "dsa", "system-design", "ai", "devops", "python"}
        if v not in valid:
            raise ValueError(f"cat must be one of {valid}")
        return v

    @field_validator("layout")
    @classmethod
    def layout_valid(cls, v):
        valid = {"featured", "side", "half", "third"}
        if v not in valid:
            raise ValueError(f"layout must be one of {valid}")
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    body: Optional[str] = None
    content: Optional[str] = None
    cat: Optional[str] = None
    layout: Optional[str] = None
    tags: Optional[List[str]] = None
    toc: Optional[List[str]] = None
    date_str: Optional[str] = None
    read_time: Optional[str] = None
    cover_image: Optional[str] = None
    is_featured: Optional[bool] = None
    is_published: Optional[bool] = None


class PostOut(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: str
    body: str
    content: str
    cat: str
    layout: str
    tags: List[str]
    toc: List[str]
    date_str: str
    read_time: str
    cover_image: Optional[str] = None
    is_featured: bool
    is_published: bool
    like_count: int
    comment_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    user_liked: bool = False

    model_config = {"from_attributes": True}


class PostListOut(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: str
    cat: str
    layout: str
    tags: List[str]
    date_str: str
    read_time: str
    cover_image: Optional[str] = None
    is_featured: bool
    like_count: int
    comment_count: int
    view_count: int
    user_liked: bool = False

    model_config = {"from_attributes": True}