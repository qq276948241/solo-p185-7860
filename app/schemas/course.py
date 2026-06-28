from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    name: str = Field(..., max_length=100, description="课程名称")
    description: Optional[str] = Field(None, max_length=500, description="课程描述")
    coach_id: int = Field(..., description="教练ID")
    day_of_week: int = Field(..., ge=0, le=6, description="星期几: 0=周一, 6=周日")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    capacity: int = Field(10, ge=1, description="容量")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="课程名称")
    description: Optional[str] = Field(None, max_length=500, description="课程描述")
    coach_id: Optional[int] = Field(None, description="教练ID")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="星期几: 0=周一, 6=周日")
    start_time: Optional[time] = Field(None, description="开始时间")
    end_time: Optional[time] = Field(None, description="结束时间")
    capacity: Optional[int] = Field(None, ge=1, description="容量")
    is_active: Optional[bool] = Field(None, description="是否启用")


class CourseResponse(CourseBase):
    id: int
    is_active: bool
    coach_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseWithScheduleResponse(CourseResponse):
    date: Optional[str] = None
    booked_count: int = 0
    remaining_slots: int = 0
