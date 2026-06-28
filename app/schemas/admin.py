from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CourseBookingStats(BaseModel):
    course_id: int
    course_name: str
    coach_name: str
    class_date: date
    start_time: str
    end_time: str
    capacity: int
    booked_count: int
    remaining_slots: int
    bookings: List[dict] = []


class CoachStats(BaseModel):
    coach_id: int
    coach_name: str
    total_classes: int
    total_attendance: int
    period_start: date
    period_end: date


class ExpiringCardResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    card_type: str
    name: str
    remaining_count: int
    end_date: date
    days_left: int
