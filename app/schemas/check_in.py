from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CheckInBase(BaseModel):
    booking_id: int = Field(..., description="预约ID")


class CheckInCreate(CheckInBase):
    pass


class CheckInResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    booking_id: int
    course_id: int
    course_name: Optional[str] = None
    coach_name: Optional[str] = None
    check_in_time: datetime
    deducted_count: int
    remaining_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
