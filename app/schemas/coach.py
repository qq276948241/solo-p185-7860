from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CoachBase(BaseModel):
    name: str = Field(..., max_length=50, description="教练姓名")
    phone: Optional[str] = Field(None, max_length=20, description="教练电话")
    specialty: Optional[str] = Field(None, max_length=100, description="专长")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="教练姓名")
    phone: Optional[str] = Field(None, max_length=20, description="教练电话")
    specialty: Optional[str] = Field(None, max_length=100, description="专长")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    is_active: Optional[bool] = Field(None, description="是否启用")


class CoachResponse(CoachBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
