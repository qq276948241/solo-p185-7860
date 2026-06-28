from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.booking import BookingStatus


class BookingBase(BaseModel):
    course_id: int = Field(..., description="课程ID")
    class_date: date = Field(..., description="上课日期")


class BookingCreate(BookingBase):
    pass


class BookingCancel(BaseModel):
    booking_id: int = Field(..., description="预约ID")


class BookingResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    course_name: Optional[str] = None
    coach_name: Optional[str] = None
    class_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: BookingStatus
    membership_card_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
