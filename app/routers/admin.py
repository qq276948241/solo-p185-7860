from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.models.check_in import CheckIn
from app.models.membership_card import MembershipCard, CardStatus
from app.schemas.admin import CourseBookingStats, CoachStats, ExpiringCardResponse
from app.schemas.review import ReviewResponse
from app.services import review_service

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/course-bookings", response_model=List[CourseBookingStats], summary="每节课报名情况")
def get_course_bookings(
    start_date: Optional[date] = Query(None, description="开始日期，默认本周一"),
    end_date: Optional[date] = Query(None, description="结束日期，默认本周日"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today = date.today()
    if not start_date:
        start_date = today - timedelta(days=today.weekday())
    if not end_date:
        end_date = start_date + timedelta(days=6)

    courses = db.query(Course).filter(Course.is_active == True).all()
    result = []

    current = start_date
    while current <= end_date:
        for course in courses:
            if current.weekday() != course.day_of_week:
                continue

            coach = db.query(Coach).filter(Coach.id == course.coach_id).first()

            bookings = db.query(Booking).filter(
                Booking.course_id == course.id,
                Booking.class_date == current,
                Booking.status != BookingStatus.CANCELLED,
            ).all()

            booking_list = []
            for b in bookings:
                user = db.query(User).filter(User.id == b.user_id).first()
                booking_list.append({
                    "booking_id": b.id,
                    "user_id": b.user_id,
                    "user_name": user.name if user else None,
                    "user_phone": user.phone if user else None,
                    "status": b.status.value,
                    "booked_at": b.created_at.isoformat(),
                })

            stats = CourseBookingStats(
                course_id=course.id,
                course_name=course.name,
                coach_name=coach.name if coach else None,
                class_date=current,
                start_time=course.start_time.strftime("%H:%M"),
                end_time=course.end_time.strftime("%H:%M"),
                capacity=course.capacity,
                booked_count=len(bookings),
                remaining_slots=max(0, course.capacity - len(bookings)),
                bookings=booking_list,
            )
            result.append(stats)

        current += timedelta(days=1)

    result.sort(key=lambda x: (x.class_date, x.start_time))
    return result


@router.get("/coach-stats", response_model=List[CoachStats], summary="教练课时统计")
def get_coach_stats(
    start_date: Optional[date] = Query(None, description="开始日期，默认本月1号"),
    end_date: Optional[date] = Query(None, description="结束日期，默认今天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        end_date = today

    coaches = db.query(Coach).filter(Coach.is_active == True).all()
    result = []

    for coach in coaches:
        course_ids = [c.id for c in coach.courses]

        total_classes = db.query(func.count(CheckIn.id.distinct())).filter(
            CheckIn.course_id.in_(course_ids),
            func.date(CheckIn.check_in_time) >= start_date,
            func.date(CheckIn.check_in_time) <= end_date,
        ).scalar() or 0

        total_attendance = db.query(func.count(CheckIn.id)).filter(
            CheckIn.course_id.in_(course_ids),
            func.date(CheckIn.check_in_time) >= start_date,
            func.date(CheckIn.check_in_time) <= end_date,
        ).scalar() or 0

        stats = CoachStats(
            coach_id=coach.id,
            coach_name=coach.name,
            total_classes=total_classes,
            total_attendance=total_attendance,
            period_start=start_date,
            period_end=end_date,
        )
        result.append(stats)

    return result


@router.get("/expiring-cards", response_model=List[ExpiringCardResponse], summary="会员卡快到期提醒")
def get_expiring_cards(
    days_threshold: int = Query(7, ge=1, le=30, description="提前多少天提醒，默认7天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today = date.today()
    threshold_date = today + timedelta(days=days_threshold)

    cards = db.query(MembershipCard).filter(
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.end_date >= today,
        MembershipCard.end_date <= threshold_date,
    ).order_by(MembershipCard.end_date.asc()).all()

    result = []
    for card in cards:
        user = db.query(User).filter(User.id == card.user_id).first()
        days_left = (card.end_date - today).days

        resp = ExpiringCardResponse(
            id=card.id,
            user_id=card.user_id,
            user_name=user.name if user else None,
            user_phone=user.phone if user else None,
            card_type=card.card_type.value,
            name=card.name,
            remaining_count=card.remaining_count,
            end_date=card.end_date,
            days_left=days_left,
        )
        result.append(resp)

    return result


@router.get("/dashboard", summary="数据概览")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    today = date.today()

    total_members = db.query(func.count(User.id)).filter(
        User.role == "member",
        User.is_active == True,
    ).scalar() or 0

    active_cards = db.query(func.count(MembershipCard.id)).filter(
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.start_date <= today,
        MembershipCard.end_date >= today,
    ).scalar() or 0

    today_weekday = today.weekday()
    today_course_ids = [c.id for c in db.query(Course).filter(
        Course.day_of_week == today_weekday,
        Course.is_active == True,
    ).all()]

    today_bookings = db.query(func.count(Booking.id)).filter(
        Booking.course_id.in_(today_course_ids),
        Booking.class_date == today,
        Booking.status != BookingStatus.CANCELLED,
    ).scalar() or 0

    today_check_ins = db.query(func.count(CheckIn.id)).filter(
        func.date(CheckIn.check_in_time) == today,
    ).scalar() or 0

    expiring_soon = db.query(func.count(MembershipCard.id)).filter(
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.end_date > today,
        MembershipCard.end_date <= today + timedelta(days=7),
    ).scalar() or 0

    return {
        "total_members": total_members,
        "active_cards": active_cards,
        "today_bookings": today_bookings,
        "today_check_ins": today_check_ins,
        "expiring_cards_7d": expiring_soon,
        "today": today.isoformat(),
    }


@router.get("/reviews", response_model=List[ReviewResponse], summary="查询所有评价(管理员)")
def get_all_reviews(
    coach_id: Optional[int] = Query(None, description="按教练筛选"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="按评分筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    return review_service.get_review_responses(db, coach_id=coach_id, rating=rating)
