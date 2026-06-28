from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseWithScheduleResponse,
)

router = APIRouter(prefix="/courses", tags=["课程排课"])


@router.post("", response_model=CourseResponse, summary="创建课程(管理员)")
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    coach = db.query(Coach).filter(Coach.id == course_in.coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="教练不存在"
        )

    if course_in.start_time >= course_in.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间必须早于结束时间"
        )

    existing = db.query(Course).filter(
        Course.coach_id == course_in.coach_id,
        Course.day_of_week == course_in.day_of_week,
        Course.is_active == True,
        and_(
            Course.start_time < course_in.end_time,
            Course.end_time > course_in.start_time,
        ),
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该教练在此时段已有课程安排"
        )

    course = Course(**course_in.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)

    result = CourseResponse.model_validate(course)
    result.coach_name = coach.name
    return result


@router.get("/weekly", response_model=List[CourseWithScheduleResponse], summary="查询本周课表")
def get_weekly_schedule(
    week_offset: int = Query(0, description="周偏移量: 0=本周, 1=下周, -1=上周"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start_date = monday + timedelta(weeks=week_offset)
    end_date = start_date + timedelta(days=6)

    courses = db.query(Course).filter(
        Course.is_active == True
    ).order_by(Course.day_of_week, Course.start_time).all()

    result = []
    for course in courses:
        course_date = start_date + timedelta(days=course.day_of_week)

        booked_count = db.query(Booking).filter(
            Booking.course_id == course.id,
            Booking.class_date == course_date,
            Booking.status != BookingStatus.CANCELLED,
        ).count()

        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()

        course_resp = CourseWithScheduleResponse.model_validate(course)
        course_resp.coach_name = coach.name if coach else None
        course_resp.date = course_date.isoformat()
        course_resp.booked_count = booked_count
        course_resp.remaining_slots = max(0, course.capacity - booked_count)
        result.append(course_resp)

    return result


@router.get("", response_model=List[CourseResponse], summary="查询所有课程模板(管理员)")
def get_all_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    courses = db.query(Course).order_by(Course.day_of_week, Course.start_time).all()
    result = []
    for course in courses:
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        course_resp = CourseResponse.model_validate(course)
        course_resp.coach_name = coach.name if coach else None
        result.append(course_resp)
    return result


@router.get("/{course_id}", response_model=CourseResponse, summary="查询课程详情")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = CourseResponse.model_validate(course)
    result.coach_name = coach.name if coach else None
    return result


@router.put("/{course_id}", response_model=CourseResponse, summary="更新课程(管理员)")
def update_course(
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    if course_in.coach_id:
        coach = db.query(Coach).filter(Coach.id == course_in.coach_id).first()
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="教练不存在"
            )

    update_data = course_in.model_dump(exclude_unset=True)

    coach_id = update_data.get("coach_id", course.coach_id)
    day_of_week = update_data.get("day_of_week", course.day_of_week)
    start_time = update_data.get("start_time", course.start_time)
    end_time = update_data.get("end_time", course.end_time)

    if start_time and end_time and start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间必须早于结束时间"
        )

    if any(k in update_data for k in ["coach_id", "day_of_week", "start_time", "end_time"]):
        existing = db.query(Course).filter(
            Course.id != course_id,
            Course.coach_id == coach_id,
            Course.day_of_week == day_of_week,
            Course.is_active == True,
            and_(
                Course.start_time < end_time,
                Course.end_time > start_time,
            ),
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该教练在此时段已有课程安排"
            )

    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = CourseResponse.model_validate(course)
    result.coach_name = coach.name if coach else None
    return result
