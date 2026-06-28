from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="评分: 1-5星")
    comment: Optional[str] = Field(None, max_length=1000, description="评价内容")

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("评分必须在1-5星之间")
        return v


class ReviewResponse(BaseModel):
    id: int
    booking_id: int
    user_id: int
    user_name: Optional[str] = None
    course_id: int
    course_name: Optional[str] = None
    coach_id: int
    coach_name: Optional[str] = None
    class_date: Optional[str] = None
    start_time: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewStats(BaseModel):
    coach_id: int
    coach_name: str
    total_reviews: int
    avg_rating: float
    five_star_count: int
    four_star_count: int
    three_star_count: int
    two_star_count: int
    one_star_count: int
