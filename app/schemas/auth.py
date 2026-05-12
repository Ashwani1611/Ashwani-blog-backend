from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 64:
            raise ValueError("Username must be 3–64 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, _ and -")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshOut(BaseModel):
    access_token: str
    token_type: str = "bearer"