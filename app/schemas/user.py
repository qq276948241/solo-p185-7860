from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    gender: Optional[str] = Field(None, max_length=10, description="性别")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserLogin(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    password: Optional[str] = Field(None, min_length=6, max_length=50, description="密码")


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None
