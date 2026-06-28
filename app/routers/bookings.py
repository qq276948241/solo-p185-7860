from datetime import date, datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.models.membership_card import MembershipCard, CardType, CardStatus
from app.schemas.booking import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["预约管理"])


def get_valid_card(db: Session, user_id: int, class_date: date) -> MembershipCard:
    today = date.today()
    cards = db.query(MembershipCard).filter(
        MembershipCard.user_id == user_id,
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.start_date <= class_date,
        MembershipCard.end_date >= class_date,
    ).order_by(MembershipCard.created_at.asc()).all()

    monthly_cards = [c for c in cards if c.card_type == CardType.MONTHLY]
    if monthly_cards:
        return monthly_cards[0]

    count_cards = [c for c in cards if c.card_type == CardType.COUNT and c.remaining_count > 0]
    if count_cards:
        return count_cards[0]

    return None


@router.post("", response_model=BookingResponse, summary="预约课程")
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    if booking_in.class_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能预约过去的课程"
        )

    course = db.query(Course).filter(
        Course.id == booking_in.course_id,
        Course.is_active == True,
    ).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    if booking_in.class_date.weekday() != course.day_of_week:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该日期与课程星期几不匹配"
        )

    existing = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.course_id == booking_in.course_id,
        Booking.class_date == booking_in.class_date,
    ).first()

    if existing:
        if existing.status == BookingStatus.CANCELLED:
            existing.status = BookingStatus.BOOKED
            db.commit()
            db.refresh(existing)

            coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
            result = BookingResponse.model_validate(existing)
            result.course_name = course.name
            result.coach_name = coach.name if coach else None
            result.start_time = course.start_time.strftime("%H:%M")
            result.end_time = course.end_time.strftime("%H:%M")
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已预约该课程"
            )

    booked_count = db.query(Booking).filter(
        Booking.course_id == booking_in.course_id,
        Booking.class_date == booking_in.class_date,
        Booking.status != BookingStatus.CANCELLED,
    ).count()

    if booked_count >= course.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该课程已满员"
        )

    valid_card = get_valid_card(db, current_user.id, booking_in.class_date)
    if not valid_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可用的会员卡，请先办卡或充值"
        )

    booking = Booking(
        user_id=current_user.id,
        course_id=booking_in.course_id,
        class_date=booking_in.class_date,
        status=BookingStatus.BOOKED,
        membership_card_id=valid_card.id,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = BookingResponse.model_validate(booking)
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.start_time = course.start_time.strftime("%H:%M")
    result.end_time = course.end_time.strftime("%H:%M")
    return result


@router.post("/{booking_id}/cancel", response_model=BookingResponse, summary="取消预约")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权取消他人预约"
        )

    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该预约已取消"
        )

    if booking.status == BookingStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已签到的课程不能取消"
        )

    now = datetime.now()
    class_datetime = datetime.combine(booking.class_date, booking.course.start_time)
    if now >= class_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已开始，不能取消"
        )

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)

    course = db.query(Course).filter(Course.id == booking.course_id).first()
    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = BookingResponse.model_validate(booking)
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.start_time = course.start_time.strftime("%H:%M")
    result.end_time = course.end_time.strftime("%H:%M")
    return result


@router.get("/my", response_model=List[BookingResponse], summary="查询我的预约")
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    bookings = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.class_date >= today - timedelta(days=7),
    ).order_by(Booking.class_date.desc(), Booking.id.desc()).all()

    result = []
    for booking in bookings:
        course = db.query(Course).filter(Course.id == booking.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        booking_resp = BookingResponse.model_validate(booking)
        booking_resp.course_name = course.name
        booking_resp.coach_name = coach.name if coach else None
        booking_resp.start_time = course.start_time.strftime("%H:%M")
        booking_resp.end_time = course.end_time.strftime("%H:%M")
        result.append(booking_resp)

    return result


@router.get("", response_model=List[BookingResponse], summary="查询所有预约(管理员)")
def get_all_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    bookings = db.query(Booking).order_by(
        Booking.class_date.desc(),
        Booking.id.desc(),
    ).all()

    result = []
    for booking in bookings:
        course = db.query(Course).filter(Course.id == booking.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        booking_resp = BookingResponse.model_validate(booking)
        booking_resp.course_name = course.name
        booking_resp.coach_name = coach.name if coach else None
        booking_resp.start_time = course.start_time.strftime("%H:%M")
        booking_resp.end_time = course.end_time.strftime("%H:%M")
        result.append(booking_resp)

    return result
